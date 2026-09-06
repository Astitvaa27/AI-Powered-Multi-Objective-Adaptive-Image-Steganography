import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    __table_args__ = (
        Index("ix_experiment_runs_experiment_id", "experiment_id"),

    UniqueConstraint(
        "experiment_id",
        "run_number",
        name="uq_experiment_runs_experiment_run_number",
    ),
    CheckConstraint(
        "run_number > 0",
        name="ck_experiment_run_number_positive",
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "experiments.id",
    name="experiment_runs_experiment_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    run_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="CREATED",
        nullable=False,
    )

    random_seed: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    configuration: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
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