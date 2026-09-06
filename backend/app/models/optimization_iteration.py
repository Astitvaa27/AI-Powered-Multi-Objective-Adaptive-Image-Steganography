import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    DateTime,
    ForeignKey,
    Integer,
    String,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class OptimizationIteration(Base):
    __tablename__ = "optimization_iterations"
    __table_args__ = (
        Index("ix_optimization_iterations_optimization_run_id", "optimization_run_id"),

    UniqueConstraint(
        "optimization_run_id",
        "iteration_number",
        name="uq_optimization_iterations_run_iteration_number",
    ),
    CheckConstraint(
        "iteration_number > 0",
        name="ck_optimization_iteration_number_positive",
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "optimization_runs.id",
    name="optimization_iterations_optimization_run_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    iteration_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="STARTED",
        nullable=False,
    )

    selected_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "candidate_configurations.id",
    name="optimization_iterations_selected_candidate_id_fkey",
    ondelete="RESTRICT",
    deferrable=True,
    initially="DEFERRED",
),
        nullable=True,
    )

    optimizer_state: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
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