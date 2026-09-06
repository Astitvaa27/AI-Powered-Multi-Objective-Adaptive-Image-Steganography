from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.payload import Payload
from backend.app.schemas.payload import PayloadCreate, PayloadResponse


router = APIRouter(
    prefix="/payloads",
    tags=["Payloads"],
)


@router.post(
    "",
    response_model=PayloadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payload(
    payload_data: PayloadCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    payload = Payload(
        payload_type=payload_data.payload_type,
        original_size_bytes=payload_data.original_size_bytes,
        encoded_size_bytes=payload_data.encoded_size_bytes,
        payload_hash=payload_data.payload_hash,
        encryption_enabled=payload_data.encryption_enabled,
        encryption_algorithm=payload_data.encryption_algorithm,
        encryption_metadata=payload_data.encryption_metadata,
        storage_path=payload_data.storage_path,
    )

    db.add(payload)
    db.commit()
    db.refresh(payload)

    return payload


@router.get(
    "/{payload_id}",
    response_model=PayloadResponse,
)
def get_payload(
    payload_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
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

    return payload