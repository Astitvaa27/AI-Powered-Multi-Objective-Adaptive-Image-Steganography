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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    __table_args__ = (
        Index("ix_analysis_sessions_image_id", "image_id"),
        Index("ix_analysis_sessions_user_id", "user_id"),

        CheckConstraint(
            "processing_time_ms IS NULL OR processing_time_ms >= 0",
            name="ck_analysis_processing_time_nonnegative",
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
    name="analysis_sessions_user_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "images.id",
    name="analysis_sessions_image_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="CREATED",
        nullable=False,
    )

    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    processing_time_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
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