import uuid
from datetime import datetime

from sqlalchemy import Index, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    __table_args__ = (
        Index("ix_experiments_user_id", "user_id"),
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
    name="experiments_user_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    experiment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    hypothesis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    configuration: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="DRAFT",
        nullable=False,
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