import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import CHAR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ExtractionRecord(Base):
    __tablename__ = "extraction_records"

    __table_args__ = (
        Index("ix_extraction_records_session_id", "session_id"),

        CheckConstraint(
            "extracted_size_bytes IS NULL OR extracted_size_bytes >= 0",
            name="ck_extraction_size_nonnegative",
        ),
        CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)",
            name="ck_extraction_accuracy_range",
        ),
        CheckConstraint(
            "processing_time_ms IS NULL OR processing_time_ms >= 0",
            name="ck_extraction_processing_time_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "steganography_sessions.id",
    name="extraction_records_session_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="STARTED",
        nullable=False,
    )

    extracted_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    extracted_payload_hash: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    accuracy: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    integrity_verified: Mapped[bool | None] = mapped_column(
        Boolean,
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