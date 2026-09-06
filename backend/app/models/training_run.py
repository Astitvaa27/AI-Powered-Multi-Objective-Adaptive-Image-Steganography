import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class TrainingRun(Base):
    __tablename__ = "training_runs"
    __table_args__ = (
        Index("ix_training_runs_dataset_id", "dataset_id"),
        Index("ix_training_runs_model_version_id", "model_version_id"),

    CheckConstraint(
        "processing_time_ms IS NULL OR processing_time_ms >= 0",
        name="ck_training_processing_time_nonnegative",
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "datasets.id",
    name="training_runs_dataset_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "model_versions.id",
    name="training_runs_model_version_id_fkey",
    ondelete="RESTRICT",
),
        nullable=True,
    )

    training_framework: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="CREATED",
        nullable=False,
    )

    hyperparameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    metrics: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    artifact_path: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    artifact_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    processing_time_ms: Mapped[int | None] = mapped_column(
        BigInteger,
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