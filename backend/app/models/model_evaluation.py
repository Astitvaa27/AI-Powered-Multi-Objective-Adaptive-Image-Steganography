import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"
    __table_args__ = (
        Index("ix_model_evaluations_model_version_id", "model_version_id"),
        Index("ix_model_evaluations_dataset_id", "dataset_id"),

    UniqueConstraint(
        "model_version_id",
        "dataset_id",
        "evaluation_type",
        name="uq_model_evaluations_model_dataset_type",
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "model_versions.id",
    name="model_evaluations_model_version_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "datasets.id",
    name="model_evaluations_dataset_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    evaluation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    metrics: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    confusion_matrix: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    evaluation_config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )