import hashlib
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from PIL import Image as PILImage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.embedding_method import EmbeddingMethod
from backend.app.models.image import Image
from backend.app.models.payload import Payload
from backend.app.models.steganography_session import SteganographySession
from backend.app.services.dct_service import embed_dct, extract_dct
from backend.app.services.dwt_service import embed_dwt, extract_dwt
from backend.app.services.lsb_service import (
    calculate_capacity,
    embed_lsb,
    extract_lsb,
)
from backend.app.services.metrics_service import calculate_metrics

router = APIRouter(
    prefix="/steganography",
    tags=["Steganography"],
)

STORAGE_ROOT = Path("storage")
SUPPORTED_METHODS = ("LSB", "DCT", "DWT")


class EmbedRequest(BaseModel):
    cover_image_id: UUID
    method: str = Field("LSB", description="LSB, DCT or DWT")
    payload_text: str = Field(..., min_length=1)
    channel_mode: str = Field("RGB", description="R, G, B or RGB (LSB only)")
    lsb_bits: int = Field(1, ge=1, le=3, description="LSB only")


class ExtractRequest(BaseModel):
    image_id: UUID
    method: str = Field("LSB")
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
    normalised = (method or "").upper().strip()

    if normalised not in SUPPORTED_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported embedding method. Supported methods: "
                + ", ".join(SUPPORTED_METHODS)
            ),
        )

    return normalised


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

    supports_parameters = {
        "LSB": {"channel_mode": True, "lsb_bits": True},
        "DCT": {"channel_mode": False, "lsb_bits": False},
        "DWT": {"channel_mode": False, "lsb_bits": False},
    }

    return [
        {
            "code": code,
            "name": getattr(registered.get(code), "name", code),
            "id": getattr(registered.get(code), "id", None),
            "registered": code in registered,
            "supports": supports_parameters[code],
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
    Embed a payload into a registered cover image using the existing
    LSB / DCT / DWT services, then measure MSE, PSNR and SSIM and verify
    that the payload can be extracted from the produced stego image.
    """

    user_id = UUID(current_user_id)
    method = _normalise_method(request.method)

    cover = _get_owned_image(request.cover_image_id, user_id, db)

    payload_bytes = request.payload_text.encode("utf-8")

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

    output_dir = STORAGE_ROOT / "stego"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{session.id}.png"

    started = perf_counter()

    try:
        if method == "LSB":
            embed_result = embed_lsb(
                input_path=cover.storage_path,
                output_path=str(output_path),
                payload=payload_bytes,
                channel_mode=request.channel_mode,
                lsb_bits=request.lsb_bits,
            )

            extracted = extract_lsb(
                image_path=str(output_path),
                channel_mode=request.channel_mode,
                lsb_bits=request.lsb_bits,
            )

        elif method == "DCT":
            embed_result = embed_dct(
                input_path=cover.storage_path,
                output_path=str(output_path),
                payload=payload_bytes,
            )

            extracted = extract_dct(image_path=str(output_path))

        else:
            embed_result = embed_dwt(
                input_path=cover.storage_path,
                output_path=str(output_path),
                payload=payload_bytes,
            )

            extracted = extract_dwt(image_path=str(output_path))

        metrics = calculate_metrics(cover.storage_path, str(output_path))

        processing_time_ms = int((perf_counter() - started) * 1000)

        extraction_matches = extracted == payload_bytes

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
            metadata_json={
                "image_type": "STEGO",
                "source": "STEGANOGRAPHY_EMBED",
                "source_image_id": str(cover.id),
                "embedding_method": method,
                "channel_mode": request.channel_mode.upper(),
                "lsb_bits": request.lsb_bits,
                "steganography_session_id": str(session.id),
            },
            status="ACTIVE",
        )

        db.add(stego_image)
        db.flush()

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
        session.status = "FAILED"
        session.error_message = str(exc)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        session.status = "FAILED"
        session.error_message = str(exc)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding failed: {exc}",
        )


@router.post("/extract")
def extract_payload(
    request: ExtractRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Attempt to recover a payload from a registered stego image."""

    user_id = UUID(current_user_id)
    method = _normalise_method(request.method)

    image = _get_owned_image(request.image_id, user_id, db)

    started = perf_counter()

    try:
        if method == "LSB":
            extracted = extract_lsb(
                image_path=image.storage_path,
                channel_mode=request.channel_mode,
                lsb_bits=request.lsb_bits,
            )
        elif method == "DCT":
            extracted = extract_dct(image_path=image.storage_path)
        else:
            extracted = extract_dwt(image_path=image.storage_path)

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
        "payload_size_bytes": len(extracted),
        "payload_text": decoded,
        "is_probably_text": "\ufffd" not in decoded,
        "processing_time_ms": int((perf_counter() - started) * 1000),
    }


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

    cover_ids = {session.cover_image_id for session in sessions}

    covers = {
        image.id: image
        for image in db.query(Image).filter(Image.id.in_(cover_ids)).all()
    } if cover_ids else {}

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
                    covers.get(session.cover_image_id),
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
            }
            for session in sessions
        ],
    }
