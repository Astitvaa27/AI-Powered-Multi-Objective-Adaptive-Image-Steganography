import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ObjectiveScore(Base):
    __tablename__ = "objective_scores"
    __table_args__ = (
        Index("ix_objective_scores_candidate_configuration_id", "candidate_configuration_id"),

    UniqueConstraint(
        "candidate_configuration_id",
        "objective_name",
        name="uq_objective_scores_candidate_objective",
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    candidate_configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "candidate_configurations.id",
    name="objective_scores_candidate_configuration_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    objective_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    metric_values: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    ranking: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )