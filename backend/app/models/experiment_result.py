import uuid
from datetime import datetime

from sqlalchemy import Index, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    __table_args__ = (
        Index("ix_experiment_results_experiment_run_id", "experiment_run_id"),
        Index("ix_experiment_results_image_id", "image_id"),
        Index("ix_experiment_results_method_id", "method_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    experiment_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "experiment_runs.id",
    name="experiment_results_experiment_run_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "images.id",
    name="experiment_results_image_id_fkey",
    ondelete="RESTRICT",
),
        nullable=True,
    )

    method_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "embedding_methods.id",
    name="experiment_results_method_id_fkey",
    ondelete="RESTRICT",
),
        nullable=True,
    )

    result_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    metrics: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    observations: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    result_path: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )