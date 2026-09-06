import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
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


class CandidateConfiguration(Base):
    __tablename__ = "candidate_configurations"
    __table_args__ = (
        Index("ix_candidate_configurations_method_id", "method_id"),

    UniqueConstraint(
        "iteration_id",
        "candidate_number",
        name="uq_candidate_configurations_iteration_candidate_number",
    ),
    CheckConstraint(
        "candidate_number IS NULL OR candidate_number > 0",
        name="ck_candidate_number_positive",
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    iteration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "optimization_iterations.id",
    name="candidate_configurations_iteration_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "embedding_methods.id",
    name="candidate_configurations_method_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    candidate_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="GENERATED",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )