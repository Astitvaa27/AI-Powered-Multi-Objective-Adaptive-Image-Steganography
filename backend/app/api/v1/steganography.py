import hashlib
import json
import shutil
import tempfile
import threading
import weakref
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from PIL import Image as PILImage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.embedding_method import EmbeddingMethod
from backend.app.models.image import Image
from backend.app.models.optimization_iteration import OptimizationIteration
from backend.app.models.optimization_run import OptimizationRun
from backend.app.models.payload import Payload
from backend.app.models.steganography_session import SteganographySession
from backend.app.services.adaptive_embedding_service import (
    OBJECTIVE_FUNCTION,
    AdaptiveSelectionError,
    build_candidate_grid,
    build_comparison_payload,
    evaluate_adaptive_candidates,
    persist_adaptive_run,
    resolve_weights,
)
from backend.app.services.auto_extract import (
    AutoExtractInputError,
    Limits,
    RecordedConfig,
    collect_result,
    load_image_input,
    run_auto_extraction,
)
from backend.app.services.embedding_service import (
    METHOD_PARAMETERS,
    SUPPORTED_METHODS,
    embed_with_method,
    extract_with_method,
    normalise_method_code,
)
from backend.app.services.lsb_service import calculate_capacity
from backend.app.services.metrics_service import calculate_metrics

router = APIRouter(
    prefix="/steganography",
    tags=["Steganography"],
)

settings = get_settings()

STORAGE_ROOT = Path("storage")


class EmbedRequest(BaseModel):
    cover_image_id: UUID
    method: str = Field("LSB", description="LSB, DCT or DWT")
    payload_text: str = Field(..., min_length=1)
    channel_mode: str = Field("RGB", description="R, G, B or RGB (LSB only)")
    lsb_bits: int = Field(1, ge=1, le=3, description="LSB only")


class AdaptiveEmbedRequest(BaseModel):
    cover_image_id: UUID
    payload_text: str = Field(..., min_length=1)
    weights: dict[str, float] | None = Field(
        None,
        description=(
            "Optional per-request objective weights, e.g. "
            '{"security": 0.5, "quality": 0.3}. Omitted objectives keep '
            "their configured weight; all weights are renormalised."
        ),
    )
    run_steganalysis: bool = Field(
        True,
        description="Persist a full steganalysis report for the selected image.",
    )


class ExtractRequest(BaseModel):
    image_id: UUID
    method: str = Field(
        "LSB",
        description=(
            "LSB, DCT, DWT, or AUTO to use the method recorded when the "
            "stego image was created"
        ),
    )
    channel_mode: str = Field("RGB")
    lsb_bits: int = Field(1, ge=1, le=3)


def _get_owned_image(image_id: UUID, user_id: UUID, db: Session) -> Image:
    image = (
        db.query(Image)
        .filter(Image.id == image_id, Image.owner_id == user_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for the current user.",
        )

    if not Path(image.storage_path).is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file is missing from storage.",
        )

    return image


def _normalise_method(method: str) -> str:
    try:
        return normalise_method_code(method)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


def _recorded_embedding(image: Image) -> dict | None:
    """
    Embedding parameters stored on a stego image when it was created
    (manual or adaptive). Returns None for images without a record.
    """

    metadata = image.metadata_json or {}
    method = str(metadata.get("embedding_method") or "").upper()

    if method not in SUPPORTED_METHODS:
        return None

    channel_mode = str(metadata.get("channel_mode") or "RGB").upper()

    try:
        lsb_bits = int(metadata.get("lsb_bits") or 1)
    except (TypeError, ValueError):
        lsb_bits = 1

    if channel_mode not in {"R", "G", "B", "RGB"}:
        channel_mode = "RGB"

    if lsb_bits not in {1, 2, 3}:
        lsb_bits = 1

    return {
        "method": method,
        "channel_mode": channel_mode,
        "lsb_bits": lsb_bits,
        "embedding_mode": metadata.get("embedding_mode", "MANUAL"),
    }


def _store_payload(db: Session, payload_bytes: bytes) -> Payload:
    payload_dir = STORAGE_ROOT / "payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)

    payload_path = payload_dir / f"{uuid4()}.txt"
    payload_path.write_bytes(payload_bytes)

    payload = Payload(
        payload_type="TEXT",
        original_size_bytes=len(payload_bytes),
        encoded_size_bytes=len(payload_bytes),
        payload_hash=hashlib.sha256(payload_bytes).hexdigest(),
        storage_path=str(payload_path).replace("\\", "/"),
        encryption_enabled=False,
        encryption_metadata={},
    )

    db.add(payload)
    db.commit()
    db.refresh(payload)

    return payload


def _start_session(
    db: Session,
    user_id: UUID,
    cover: Image,
    payload: Payload,
) -> SteganographySession:
    session = SteganographySession(
        user_id=user_id,
        cover_image_id=cover.id,
        payload_id=payload.id,
        status="PROCESSING",
        started_at=datetime.now(timezone.utc),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def _register_stego_image(
    db: Session,
    user_id: UUID,
    output_path: Path,
    metadata: dict,
) -> Image:
    stego_bytes = output_path.read_bytes()

    with PILImage.open(output_path) as stego_opened:
        stego_width, stego_height = stego_opened.size
        stego_channels = len(stego_opened.getbands())

    stego_image = Image(
        owner_id=user_id,
        original_filename=output_path.name,
        storage_path=str(output_path).replace("\\", "/"),
        mime_type="image/png",
        file_extension=".png",
        file_size_bytes=len(stego_bytes),
        width=stego_width,
        height=stego_height,
        channels=stego_channels,
        bit_depth=8,
        sha256_hash=hashlib.sha256(stego_bytes).hexdigest(),
        metadata_json=metadata,
        status="ACTIVE",
    )

    db.add(stego_image)
    db.flush()

    return stego_image


def _fail_session(db: Session, session: SteganographySession, message: str):
    db.rollback()
    session.status = "FAILED"
    session.error_message = message
    session.completed_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/methods")
def list_embedding_methods(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Return the embedding methods that are both registered as active in
    the database and backed by an implemented service.
    """

    methods = (
        db.query(EmbeddingMethod)
        .filter(
            EmbeddingMethod.code.in_(SUPPORTED_METHODS),
            EmbeddingMethod.is_active.is_(True),
        )
        .all()
    )

    registered = {method.code: method for method in methods}

    return [
        {
            "code": code,
            "name": getattr(registered.get(code), "name", code),
            "id": getattr(registered.get(code), "id", None),
            "registered": code in registered,
            "supports": METHOD_PARAMETERS[code],
        }
        for code in SUPPORTED_METHODS
    ]


@router.get("/capacity")
def get_capacity(
    image_id: UUID,
    channel_mode: str = Query("RGB"),
    lsb_bits: int = Query(1, ge=1, le=3),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Report LSB payload capacity for a registered cover image."""

    image = _get_owned_image(image_id, UUID(current_user_id), db)

    try:
        with PILImage.open(image.storage_path) as opened:
            capacity_bytes = calculate_capacity(
                opened.convert("RGB"),
                channel_mode,
                lsb_bits,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "image_id": image.id,
        "channel_mode": channel_mode.upper(),
        "lsb_bits": lsb_bits,
        "capacity_bytes": capacity_bytes,
        "width": image.width,
        "height": image.height,
    }


@router.post("/embed", status_code=status.HTTP_201_CREATED)
def embed_payload(
    request: EmbedRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Manual mode: embed a payload into a registered cover image with one
    explicitly chosen method (LSB / DCT / DWT), then measure MSE, PSNR and
    SSIM and verify that the payload can be extracted from the produced
    stego image. Kept for baselines, comparison and debugging; the
    adaptive endpoint below is the primary workflow.
    """

    user_id = UUID(current_user_id)
    method = _normalise_method(request.method)

    cover = _get_owned_image(request.cover_image_id, user_id, db)

    payload_bytes = request.payload_text.encode("utf-8")

    payload = _store_payload(db, payload_bytes)
    session = _start_session(db, user_id, cover, payload)

    output_dir = STORAGE_ROOT / "stego"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{session.id}.png"

    started = perf_counter()

    try:
        embed_result = embed_with_method(
            method,
            input_path=cover.storage_path,
            output_path=str(output_path),
            payload=payload_bytes,
            channel_mode=request.channel_mode,
            lsb_bits=request.lsb_bits,
        )

        extracted = extract_with_method(
            method,
            image_path=str(output_path),
            channel_mode=request.channel_mode,
            lsb_bits=request.lsb_bits,
        )

        metrics = calculate_metrics(cover.storage_path, str(output_path))

        processing_time_ms = int((perf_counter() - started) * 1000)

        extraction_matches = extracted == payload_bytes

        stego_image = _register_stego_image(
            db,
            user_id,
            output_path,
            {
                "image_type": "STEGO",
                "source": "STEGANOGRAPHY_EMBED",
                "embedding_mode": "MANUAL",
                "source_image_id": str(cover.id),
                "embedding_method": method,
                "channel_mode": request.channel_mode.upper(),
                "lsb_bits": request.lsb_bits,
                "steganography_session_id": str(session.id),
            },
        )

        session.stego_image_id = stego_image.id
        session.status = "COMPLETED"
        session.payload_capacity_bytes = embed_result["capacity_bytes"]
        session.psnr = None if metrics["psnr"] == float("inf") else metrics["psnr"]
        session.ssim = metrics["ssim"]
        session.extraction_accuracy = 1.0 if extraction_matches else 0.0
        session.processing_time_ms = processing_time_ms
        session.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(session)
        db.refresh(stego_image)

        return {
            "mode": "MANUAL",
            "session_id": session.id,
            "status": session.status,
            "method": method,
            "channel_mode": request.channel_mode.upper() if method == "LSB" else None,
            "lsb_bits": request.lsb_bits if method == "LSB" else None,
            "cover_image_id": cover.id,
            "stego_image_id": stego_image.id,
            "payload_id": payload.id,
            "payload_size_bytes": len(payload_bytes),
            "capacity_bytes": embed_result["capacity_bytes"],
            "capacity_used_ratio": (
                len(payload_bytes) / embed_result["capacity_bytes"]
                if embed_result["capacity_bytes"]
                else None
            ),
            "mse": metrics["mse"],
            "psnr": metrics["psnr"] if metrics["psnr"] != float("inf") else None,
            "ssim": metrics["ssim"],
            "processing_time_ms": processing_time_ms,
            "extraction_verified": extraction_matches,
            "extraction_accuracy": 1.0 if extraction_matches else 0.0,
            "extracted_preview": (
                extracted.decode("utf-8", errors="replace")[:500]
                if extraction_matches
                else None
            ),
            "output_path": str(output_path).replace("\\", "/"),
        }

    except ValueError as exc:
        _fail_session(db, session, str(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        _fail_session(db, session, str(exc))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding failed: {exc}",
        )


@router.post("/adaptive/embed", status_code=status.HTTP_201_CREATED)
def adaptive_embed_payload(
    request: AdaptiveEmbedRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Adaptive mode (closed loop): try every enabled embedding candidate,
    verify and measure each one, score them on quality, distortion,
    capacity headroom, steganalysis detectability and robustness, keep the
    best one and run a persisted steganalysis report on it.
    """

    user_id = UUID(current_user_id)

    cover = _get_owned_image(request.cover_image_id, user_id, db)

    try:
        weights = resolve_weights(settings, request.weights)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    try:
        with PILImage.open(cover.storage_path) as opened:
            opened.verify()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported or corrupted cover image: {exc}",
        )

    # Methods explicitly deactivated in embedding_methods are left out;
    # methods simply missing from the table are still implemented and used.
    disabled_methods = {
        method.code
        for method in db.query(EmbeddingMethod)
        .filter(
            EmbeddingMethod.code.in_(SUPPORTED_METHODS),
            EmbeddingMethod.is_active.is_(False),
        )
        .all()
    }

    grid = build_candidate_grid(settings, disabled_methods)

    payload_bytes = request.payload_text.encode("utf-8")

    payload = _store_payload(db, payload_bytes)
    session = _start_session(db, user_id, cover, payload)

    output_dir = STORAGE_ROOT / "stego"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{session.id}.png"

    started = perf_counter()

    try:
        with tempfile.TemporaryDirectory(prefix="adaptive_") as work_dir:
            evaluation = evaluate_adaptive_candidates(
                cover_path=cover.storage_path,
                payload=payload_bytes,
                work_dir=Path(work_dir),
                settings=settings,
                weights=weights,
                grid=grid,
            )

            shutil.copyfile(evaluation.selected_output_path, output_path)

        selected = evaluation.selected

        # Final check on the file that is actually kept.
        extracted = extract_with_method(
            selected["method"],
            image_path=str(output_path),
            channel_mode=selected["parameters"].get("channel_mode", "RGB"),
            lsb_bits=selected["parameters"].get("lsb_bits", 1),
        )
        extraction_matches = extracted == payload_bytes

        stego_image = _register_stego_image(
            db,
            user_id,
            output_path,
            {
                "image_type": "STEGO",
                "source": "STEGANOGRAPHY_EMBED",
                "embedding_mode": "ADAPTIVE",
                "source_image_id": str(cover.id),
                "embedding_method": selected["method"],
                "channel_mode": selected["parameters"].get("channel_mode", "RGB"),
                "lsb_bits": selected["parameters"].get("lsb_bits", 1),
                "steganography_session_id": str(session.id),
                "adaptive_candidate_key": selected["key"],
                "adaptive_score": selected["score"],
            },
        )

        run, iteration = persist_adaptive_run(
            db,
            user_id=user_id,
            cover_image_id=cover.id,
            payload_id=payload.id,
            evaluation=evaluation,
            selected_stego_image_id=stego_image.id,
        )

        # JSONB columns need a new dict to register the change.
        stego_image.metadata_json = {
            **stego_image.metadata_json,
            "optimization_run_id": str(run.id),
        }

        optimizer_state = {
            **build_comparison_payload(evaluation),
            "steganography_session_id": str(session.id),
            "stego_image_id": str(stego_image.id),
        }
        iteration.optimizer_state = optimizer_state

        session.stego_image_id = stego_image.id
        session.status = "COMPLETED"
        session.payload_capacity_bytes = selected["capacity_bytes"]
        session.psnr = selected["psnr"]
        session.ssim = selected["ssim"]
        session.extraction_accuracy = 1.0 if extraction_matches else 0.0
        session.processing_time_ms = int((perf_counter() - started) * 1000)
        session.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(session)
        db.refresh(stego_image)

    except AdaptiveSelectionError as exc:
        _fail_session(db, session, str(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except ValueError as exc:
        _fail_session(db, session, str(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        _fail_session(db, session, str(exc))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Adaptive embedding failed: {exc}",
        )

    # Closed-loop step: persisted steganalysis of the image that was kept.
    steganalysis = {
        "requested": request.run_steganalysis,
        "available": evaluation.steganalysis_available,
        "analysis_session_id": None,
        "predicted_class": selected["steganalysis_class"],
        "stego_probability": selected["stego_probability"],
        "confidence": None,
        "cover_stego_probability": evaluation.cover_stego_probability,
        "error": evaluation.steganalysis_error,
    }

    if request.run_steganalysis and evaluation.steganalysis_available:
        # Imported here: it is a helper of the steganalysis router.
        from backend.app.api.v1.steganalysis import _execute_analysis

        try:
            analysis = _execute_analysis(db, stego_image, user_id)

            steganalysis.update(
                {
                    "analysis_session_id": analysis["analysis_session_id"],
                    "predicted_class": analysis["predicted_class"],
                    "stego_probability": analysis["probabilities"].get(
                        "STEGO",
                        selected["stego_probability"],
                    ),
                    "confidence": analysis["confidence"],
                }
            )
        except HTTPException as exc:
            steganalysis["error"] = str(exc.detail)

        iteration.optimizer_state = {
            **optimizer_state,
            "steganalysis": _json_safe(steganalysis),
        }
        db.commit()

    return {
        "mode": "ADAPTIVE",
        "session_id": session.id,
        "status": session.status,
        "method": selected["method"],
        "selected_method": selected["method"],
        "selected_candidate_key": selected["key"],
        "selected_label": selected["label"],
        "selected_score": selected["score"],
        "channel_mode": (
            selected["parameters"]["channel_mode"]
            if selected["method"] == "LSB"
            else None
        ),
        "lsb_bits": (
            selected["parameters"]["lsb_bits"]
            if selected["method"] == "LSB"
            else None
        ),
        "cover_image_id": cover.id,
        "stego_image_id": stego_image.id,
        "payload_id": payload.id,
        "payload_size_bytes": len(payload_bytes),
        "capacity_bytes": selected["capacity_bytes"],
        "capacity_used_ratio": selected["capacity_used_ratio"],
        "mse": selected["mse"],
        "psnr": selected["psnr"],
        "ssim": selected["ssim"],
        "change_rate": selected["change_rate"],
        "processing_time_ms": session.processing_time_ms,
        "extraction_verified": extraction_matches,
        "extraction_accuracy": 1.0 if extraction_matches else 0.0,
        "extracted_preview": (
            extracted.decode("utf-8", errors="replace")[:500]
            if extraction_matches
            else None
        ),
        "output_path": str(output_path).replace("\\", "/"),
        "optimization_run_id": run.id,
        "algorithm": evaluation.configuration["algorithm"],
        "weights": evaluation.weights,
        "objectives_evaluated": evaluation.objectives_evaluated,
        "candidates": evaluation.candidates,
        "explanation": evaluation.explanation,
        "limitations": evaluation.limitations,
        "steganalysis": steganalysis,
    }


def _json_safe(value: dict) -> dict:
    return {
        key: str(item) if isinstance(item, UUID) else item
        for key, item in value.items()
    }


@router.get("/adaptive/runs/{run_id}")
def get_adaptive_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Return the stored candidate comparison for a past adaptive run."""

    run = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
            OptimizationRun.objective_function == OBJECTIVE_FUNCTION,
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adaptive run not found.",
        )

    iteration = (
        db.query(OptimizationIteration)
        .filter(OptimizationIteration.optimization_run_id == run.id)
        .order_by(OptimizationIteration.iteration_number)
        .first()
    )

    return {
        "optimization_run_id": run.id,
        "status": run.status,
        "cover_image_id": run.image_id,
        "payload_id": run.payload_id,
        "algorithm": run.optimization_algorithm,
        "objective_function": run.objective_function,
        "best_score": run.best_score,
        "processing_time_ms": run.processing_time_ms,
        "configuration": run.configuration,
        "created_at": run.created_at,
        **(iteration.optimizer_state if iteration else {}),
    }


@router.post("/extract")
def extract_payload(
    request: ExtractRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Attempt to recover a payload from a registered stego image.

    With method=AUTO the method and parameters recorded on the image when
    it was embedded (manually or adaptively) are used, so the user does not
    need to remember which algorithm the adaptive optimiser picked.
    """

    user_id = UUID(current_user_id)

    image = _get_owned_image(request.image_id, user_id, db)

    if (request.method or "").upper().strip() == "AUTO":
        recorded = _recorded_embedding(image)

        if not recorded:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No embedding method is recorded for this image, so it "
                    "cannot be detected automatically. Choose LSB, DCT or "
                    "DWT manually."
                ),
            )

        method = recorded["method"]
        channel_mode = recorded["channel_mode"]
        lsb_bits = recorded["lsb_bits"]
        method_source = "RECORDED"
    else:
        method = _normalise_method(request.method)
        channel_mode = request.channel_mode
        lsb_bits = request.lsb_bits
        method_source = "REQUEST"

    started = perf_counter()

    try:
        extracted = extract_with_method(
            method,
            image_path=image.storage_path,
            channel_mode=channel_mode,
            lsb_bits=lsb_bits,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {exc}",
        )

    decoded = extracted.decode("utf-8", errors="replace")

    return {
        "image_id": image.id,
        "method": method,
        "method_source": method_source,
        "channel_mode": channel_mode.upper() if method == "LSB" else None,
        "lsb_bits": lsb_bits if method == "LSB" else None,
        "payload_size_bytes": len(extracted),
        "payload_text": decoded,
        "is_probably_text": "�" not in decoded,
        "processing_time_ms": int((perf_counter() - started) * 1000),
    }


# Bounded per process: automatic extraction is CPU- and memory-heavy.
_AUTO_EXTRACT_SLOTS = threading.BoundedSemaphore(
    max(1, settings.AUTO_EXTRACT_MAX_CONCURRENT)
)


def _find_stegolab_record(
    db: Session,
    user_id: UUID,
    image: Image | None,
    sha256: str,
) -> RecordedConfig | None:
    """
    Embedding settings StegoLab stored for this image, if any: either on
    the selected image itself or on one of the user's stego images with
    byte-identical content. The stored message hash is attached so the
    pipeline can verify the extraction; the record alone proves nothing.
    """

    record_image = None
    source = None

    if image is not None and _recorded_embedding(image):
        record_image, source = image, "IMAGE_RECORD"
    else:
        matches = (
            db.query(Image)
            .filter(
                Image.owner_id == user_id,
                Image.sha256_hash == sha256,
                Image.status == "ACTIVE",
            )
            .order_by(Image.created_at.desc())
            .limit(20)
            .all()
        )
        for match in matches:
            if _recorded_embedding(match):
                record_image, source = match, "HASH_MATCH"
                break

    if record_image is None:
        return None

    recorded = _recorded_embedding(record_image)
    assert recorded is not None

    payload_hash = None
    session_id = (record_image.metadata_json or {}).get("steganography_session_id")

    try:
        session_uuid = UUID(str(session_id)) if session_id else None
    except ValueError:
        session_uuid = None

    if session_uuid:
        session = (
            db.query(SteganographySession)
            .filter(
                SteganographySession.id == session_uuid,
                SteganographySession.user_id == user_id,
            )
            .first()
        )
        if session and session.payload_id:
            payload = db.get(Payload, session.payload_id)
            payload_hash = payload.payload_hash if payload else None

    return RecordedConfig(
        method=recorded["method"],
        channel_mode=recorded["channel_mode"],
        lsb_bits=recorded["lsb_bits"],
        embedding_mode=str(recorded["embedding_mode"]),
        source=source,
        payload_sha256=payload_hash,
    )


@router.post("/extract/auto")
async def auto_extract_payload(
    file: UploadFile | None = File(
        None,
        description="Image to analyse (PNG, BMP, TIFF, PGM/PPM, WebP or JPEG).",
    ),
    image_id: UUID | None = Form(
        None,
        description="Alternatively, an image already registered to the current user.",
    ),
    run_steganalysis: bool = Form(
        True,
        description="Also run the steganalysis classifier as a supporting signal.",
    ),
    stream: bool = Query(
        False,
        description=(
            "Return newline-delimited JSON progress events, ending with a "
            "'result' event, instead of a single JSON document."
        ),
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Detect and extract a hidden message without knowing how it was hidden.

    Checks StegoLab's own records first, then file-structure formats
    (appended data, EXIF), then a bounded search over the supported pixel
    methods, and validates every candidate before reporting it. The
    result distinguishes verified, plausible and unverified candidates
    and lists every method and configuration that was tried.
    """

    user_id = UUID(current_user_id)

    if (file is None) == (image_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either an image file or an image_id (not both).",
        )

    limits = Limits.from_settings(settings)
    too_large = HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail=(
            f"The file is larger than the {limits.max_file_bytes // (1024 * 1024)} MB "
            "limit for automatic extraction."
        ),
    )

    image_record: Image | None = None
    stored_path: str | None = None

    if file is not None:
        data = await file.read(limits.max_file_bytes + 1)
        await file.close()
    else:
        image_record = _get_owned_image(image_id, user_id, db)
        stored = Path(image_record.storage_path)
        if stored.stat().st_size > limits.max_file_bytes:
            raise too_large
        data = stored.read_bytes()
        stored_path = str(stored)

    if len(data) > limits.max_file_bytes:
        raise too_large

    if not _AUTO_EXTRACT_SLOTS.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many automatic extractions are running. Try again in a moment.",
        )

    released = False
    # Set once the streaming generator owns the slot and will release it.
    handed_to_stream = False

    def release() -> None:
        nonlocal released
        if not released:
            released = True
            _AUTO_EXTRACT_SLOTS.release()

    try:
        started = perf_counter()
        try:
            image = await run_in_threadpool(load_image_input, data, limits)
        except AutoExtractInputError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)
        validate_ms = int((perf_counter() - started) * 1000)

        record = _find_stegolab_record(db, user_id, image_record, image.sha256)

        events = run_auto_extraction(
            image,
            limits=limits,
            record=record,
            image_path=stored_path,
            run_steganalysis=(
                run_steganalysis and settings.AUTO_EXTRACT_STEGANALYSIS_ENABLED
            ),
            validate_ms=validate_ms,
        )
        response_extra = {"image_id": image_record.id if image_record else None}

        if not stream:
            try:
                result = await run_in_threadpool(collect_result, events)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Automatic extraction failed unexpectedly.",
                )
            return {**response_extra, **result}

        def event_stream():
            try:
                for event in events:
                    if event.get("type") == "result":
                        event = {
                            "type": "result",
                            "result": {**response_extra, **event["result"]},
                        }
                    yield json.dumps(event, default=str) + "\n"
            except Exception:
                yield json.dumps(
                    {"type": "error", "detail": "Automatic extraction failed unexpectedly."}
                ) + "\n"
            finally:
                events.close()
                release()

        body = event_stream()
        # An unstarted generator never runs its finally block, so also
        # release the slot when the generator is discarded.
        weakref.finalize(body, release)

        response = StreamingResponse(
            body,
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )
        handed_to_stream = True
        return response

    finally:
        if not handed_to_stream:
            release()


@router.get("/sessions")
def list_steganography_sessions(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    user_id = UUID(current_user_id)

    query = (
        db.query(SteganographySession)
        .filter(SteganographySession.user_id == user_id)
    )

    total = query.count()

    sessions = (
        query
        .order_by(SteganographySession.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    image_ids = {session.cover_image_id for session in sessions} | {
        session.stego_image_id
        for session in sessions
        if session.stego_image_id
    }

    images = {
        image.id: image
        for image in db.query(Image).filter(Image.id.in_(image_ids)).all()
    } if image_ids else {}

    def stego_metadata(session: SteganographySession) -> dict:
        stego = images.get(session.stego_image_id)
        return (stego.metadata_json or {}) if stego else {}

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": session.id,
                "status": session.status,
                "cover_image_id": session.cover_image_id,
                "cover_image_filename": getattr(
                    images.get(session.cover_image_id),
                    "original_filename",
                    None,
                ),
                "stego_image_id": session.stego_image_id,
                "payload_id": session.payload_id,
                "payload_capacity_bytes": session.payload_capacity_bytes,
                "psnr": session.psnr,
                "ssim": session.ssim,
                "extraction_accuracy": session.extraction_accuracy,
                "processing_time_ms": session.processing_time_ms,
                "error_message": session.error_message,
                "created_at": session.created_at,
                "method": stego_metadata(session).get("embedding_method"),
                "embedding_mode": stego_metadata(session).get("embedding_mode"),
                "optimization_run_id": stego_metadata(session).get(
                    "optimization_run_id"
                ),
            }
            for session in sessions
        ],
    }
