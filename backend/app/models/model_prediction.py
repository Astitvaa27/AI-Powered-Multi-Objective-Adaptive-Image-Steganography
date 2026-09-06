import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    __table_args__ = (
        Index("ix_model_predictions_analysis_session_id", "analysis_session_id"),
        Index("ix_model_predictions_model_version_id", "model_version_id"),

        CheckConstraint(
            "confidence IS NULL OR "
            "(confidence >= 0 AND confidence <= 1)",
            name="ck_prediction_confidence_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "analysis_sessions.id",
    name="model_predictions_analysis_session_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "model_versions.id",
    name="model_predictions_model_version_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    predicted_class: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    score: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    probabilities: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )