import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class SteganographySession(Base):
    __tablename__ = "steganography_sessions"

    __table_args__ = (
        Index("ix_steganography_sessions_cover_image_id", "cover_image_id"),
        Index("ix_steganography_sessions_user_id", "user_id"),

        CheckConstraint(
            "payload_capacity_bytes IS NULL OR payload_capacity_bytes >= 0",
            name="ck_stego_payload_capacity_nonnegative",
        ),
        CheckConstraint(
            "psnr IS NULL OR psnr >= 0",
            name="ck_stego_psnr_nonnegative",
        ),
        CheckConstraint(
            "ssim IS NULL OR (ssim >= 0 AND ssim <= 1)",
            name="ck_stego_ssim_range",
        ),
        CheckConstraint(
            "extraction_accuracy IS NULL OR "
            "(extraction_accuracy >= 0 AND extraction_accuracy <= 1)",
            name="ck_stego_extraction_accuracy_range",
        ),
        CheckConstraint(
            "processing_time_ms IS NULL OR processing_time_ms >= 0",
            name="ck_stego_processing_time_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "users.id",
    name="steganography_sessions_user_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    cover_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "images.id",
    name="steganography_sessions_cover_image_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    stego_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "images.id",
    name="steganography_sessions_stego_image_id_fkey",
    ondelete="RESTRICT",
),
        nullable=True,
    )

    payload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "payloads.id",
    name="steganography_sessions_payload_id_fkey",
    ondelete="RESTRICT",
),
        nullable=True,
    )

    configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "embedding_configurations.id",
    name="steganography_sessions_configuration_id_fkey",
    ondelete="RESTRICT",
),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="CREATED",
        nullable=False,
    )

    payload_capacity_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    psnr: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    ssim: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    extraction_accuracy: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    processing_time_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )