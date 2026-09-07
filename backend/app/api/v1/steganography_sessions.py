from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.image import Image
from backend.app.models.payload import Payload
from backend.app.models.steganography_session import SteganographySession
from backend.app.services.lsb_service import embed_lsb
from backend.app.services.metrics_service import calculate_metrics


router = APIRouter(
    prefix="/steganography-sessions",
    tags=["Steganography Sessions"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_steganography_session(
    cover_image_id: UUID,
    payload_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    user_id = UUID(current_user_id)

    # Verify cover image belongs to the current user
    image = (
        db.query(Image)
        .filter(
            Image.id == cover_image_id,
            Image.owner_id == user_id,
        )
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover image not found",
        )

    # Verify payload exists
    payload = (
        db.query(Payload)
        .filter(Payload.id == payload_id)
        .first()
    )

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payload not found",
        )

    # Create session
    session = SteganographySession(
        user_id=user_id,
        cover_image_id=cover_image_id,
        payload_id=payload_id,
        status="PROCESSING",
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        input_path = Path(image.storage_path)

        output_path = (
            Path("storage")
            / "stego"
            / f"{session.id}.png"
        )

        # For Phase 3 testing, use payload bytes directly.
        payload_bytes = (
            b"Phase 3 test payload"
        )

        result = embed_lsb(
            str(input_path),
            str(output_path),
            payload_bytes,
        )

        # embed_lsb() reports embedding data only; distortion metrics
        # come from the metrics service.
        metrics = calculate_metrics(
            str(input_path),
            str(output_path),
        )

        result.update(metrics)

        session.stego_image_id = None
        session.status = "COMPLETED"
        session.payload_capacity_bytes = result["capacity_bytes"]
        session.psnr = (
            None if result["psnr"] == float("inf") else result["psnr"]
        )
        session.ssim = result["ssim"]

        db.commit()
        db.refresh(session)

        return {
            "session_id": session.id,
            "status": session.status,
            "output_path": result["output_path"],
            "payload_size_bytes": result["payload_size_bytes"],
            "capacity_bytes": result["capacity_bytes"],
            "mse": result["mse"],
            "psnr": (
                None if result["psnr"] == float("inf") else result["psnr"]
            ),
            "ssim": result["ssim"],
        }

    except Exception as exc:
        session.status = "FAILED"
        session.error_message = str(exc)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Steganography failed: {exc}",
        )