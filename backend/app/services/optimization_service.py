import hashlib
from pathlib import Path
from time import perf_counter
from uuid import UUID

from PIL import Image as PILImage
from sqlalchemy.orm import Session

from backend.app.models.candidate_configuration import CandidateConfiguration
from backend.app.models.embedding_method import EmbeddingMethod
from backend.app.models.image import Image
from backend.app.models.objective_score import ObjectiveScore
from backend.app.models.optimization_iteration import OptimizationIteration
from backend.app.models.optimization_run import OptimizationRun
from backend.app.models.payload import Payload
from backend.app.services.lsb_service import embed_lsb, extract_lsb
from backend.app.services.dct_service import embed_dct, extract_dct
from backend.app.services.dwt_service import embed_dwt, extract_dwt
from backend.app.services.metrics_service import calculate_metrics


STORAGE_ROOT = Path("storage")


def process_lsb_candidate(
    db: Session,
    run: OptimizationRun,
    iteration: OptimizationIteration,
    candidate: CandidateConfiguration,
) -> ObjectiveScore:
    """
    Automatically process one LSB candidate.

    Flow:
        image + payload
            ↓
        LSB embedding
            ↓
        stego image
            ↓
        MSE / PSNR / SSIM
            ↓
        ObjectiveScore
    """

    method = (
        db.query(EmbeddingMethod)
        .filter(EmbeddingMethod.id == candidate.method_id)
        .first()
    )

    if not method:
        raise ValueError("Embedding method not found")

    if method.code not in {"LSB", "DCT", "DWT"}:
        raise ValueError(
            f"Automatic processing for {method.code} is not implemented yet"
        )

    image = (
        db.query(Image)
        .filter(Image.id == run.image_id)
        .first()
    )

    if not image:
        raise ValueError("Source image not found")

    if not run.payload_id:
        raise ValueError("Optimization run has no payload")

    payload = (
        db.query(Payload)
        .filter(Payload.id == run.payload_id)
        .first()
    )

    if not payload:
        raise ValueError("Payload not found")

    if not payload.storage_path:
        raise ValueError("Payload storage path is missing")

    input_path = Path(image.storage_path)
    payload_path = Path(payload.storage_path)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Source image not found: {input_path}"
        )

    if not payload_path.exists():
        raise FileNotFoundError(
            f"Payload file not found: {payload_path}"
        )

    payload_bytes = payload_path.read_bytes()

    output_dir = STORAGE_ROOT / "stego"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = (
        output_dir
        / f"{run.id}_{iteration.id}_{candidate.id}.png"
    )

    start_time = perf_counter()

    channel_mode = candidate.parameters.get(
        "channel_mode",
        "RGB",
    )

    lsb_bits = int(
        candidate.parameters.get(
            "lsb_bits",
            1,
        )
    )

    if method.code == "LSB":
        embed_result = embed_lsb(
            input_path=str(input_path),
            output_path=str(output_path),
            payload=payload_bytes,
            channel_mode=channel_mode,
            lsb_bits=lsb_bits,
        )

    elif method.code == "DCT":
        embed_result = embed_dct(
            input_path=str(input_path),
            output_path=str(output_path),
            payload=payload_bytes,
        )

    elif method.code == "DWT":
        embed_result = embed_dwt(
            input_path=str(input_path),
            output_path=str(output_path),
            payload=payload_bytes,
        )

    # Verify that the embedded payload can be extracted correctly.
    if method.code == "LSB":
        extracted_payload = extract_lsb(
            image_path=str(output_path),
            channel_mode=channel_mode,
            lsb_bits=lsb_bits,
        )

    elif method.code == "DCT":
        extracted_payload = extract_dct(
            image_path=str(output_path),
        )

    elif method.code == "DWT":
        extracted_payload = extract_dwt(
            image_path=str(output_path),
        )

    extraction_accuracy = (
        1.0
        if extracted_payload == payload_bytes
        else 0.0
    )

    metrics = calculate_metrics(
        str(input_path),
        str(output_path),
    )

    stego_file_size = output_path.stat().st_size
    stego_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()

    with PILImage.open(output_path) as stego_image:
        stego_width, stego_height = stego_image.size
        stego_channels = len(stego_image.getbands())

    stego_image_record = Image(
        owner_id=run.user_id,
        original_filename=output_path.name,
        storage_path=str(output_path),
        mime_type="image/png",
        file_extension=".png",
        file_size_bytes=stego_file_size,
        width=stego_width,
        height=stego_height,
        channels=stego_channels,
        bit_depth=8,
        sha256_hash=stego_hash,
        metadata_json={
            "image_type": "STEGO",
            "source_image_id": str(image.id),
            "optimization_run_id": str(run.id),
            "iteration_id": str(iteration.id),
            "candidate_id": str(candidate.id),
            "embedding_method": method.code,
            "channel_mode": channel_mode,
            "lsb_bits": lsb_bits,
        },
        status="ACTIVE",
    )

    db.add(stego_image_record)
    db.flush()

    processing_time_ms = int(
        (perf_counter() - start_time) * 1000
    )

    candidate.status = "COMPLETED"

    metric_values = {
        "mse": metrics["mse"],
        "psnr": metrics["psnr"],
        "ssim": metrics["ssim"],
        "extraction_accuracy": extraction_accuracy,
        "payload_size_bytes": len(payload_bytes),
        "capacity_bytes": embed_result["capacity_bytes"],
        "processing_time_ms": processing_time_ms,
        "stego_image_path": str(output_path),
        "lsb_bits": lsb_bits if method.code == "LSB" else None,
        "channel_mode": channel_mode if method.code == "LSB" else None,
    }

    objective_name = run.objective_function

    if objective_name == "MAXIMIZE_PSNR":
        score = metrics["psnr"]

    elif objective_name == "MAXIMIZE_SSIM":
        score = metrics["ssim"]

    elif objective_name == "MINIMIZE_MSE":
        score = -metrics["mse"]

    else:
        raise ValueError(
            f"Unsupported objective function: {objective_name}"
        )

    score_record = (
        db.query(ObjectiveScore)
        .filter(
            ObjectiveScore.candidate_configuration_id == candidate.id,
            ObjectiveScore.objective_name == objective_name,
        )
        .first()
    )

    if score_record:
        score_record.score = score
        score_record.metric_values = metric_values
        score_record.ranking = None
    else:
        score_record = ObjectiveScore(
            candidate_configuration_id=candidate.id,
            objective_name=objective_name,
            score=score,
            metric_values=metric_values,
            ranking=None,
        )

        db.add(score_record)

    db.commit()
    db.refresh(score_record)

    return score_record