import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    __table_args__ = (
        Index("ix_optimization_runs_user_id", "user_id"),
        Index("ix_optimization_runs_image_id", "image_id"),
        Index("ix_optimization_runs_payload_id", "payload_id"),

    CheckConstraint(
        "max_iterations IS NULL OR max_iterations > 0",
        name="ck_optimization_max_iterations_positive",
    ),
    CheckConstraint(
        "processing_time_ms IS NULL OR processing_time_ms >= 0",
        name="ck_optimization_processing_time_nonnegative",
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
    name="optimization_runs_user_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "images.id",
    name="optimization_runs_image_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    payload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "payloads.id",
    name="optimization_runs_payload_id_fkey",
    ondelete="RESTRICT",
),
        nullable=True,
    )

    selected_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "candidate_configurations.id",
    name="optimization_runs_selected_candidate_id_fkey",
    ondelete="RESTRICT",
    deferrable=True,
    initially="DEFERRED",
),
        nullable=True,
    )

    optimization_algorithm: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    objective_function: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    max_iterations: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="CREATED",
        nullable=False,
    )

    best_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    processing_time_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    configuration: Mapped[dict] = mapped_column(
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )