import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    framework: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    architecture: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    artifact_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    artifact_hash: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    configuration: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
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