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


class DatasetImage(Base):
    __tablename__ = "dataset_images"

    __table_args__ = (
        Index("ix_dataset_images_dataset_id", "dataset_id"),
        Index("ix_dataset_images_image_id", "image_id"),

        UniqueConstraint(
            "dataset_id",
            "image_id",
            name="uq_dataset_image",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "datasets.id",
    name="dataset_images_dataset_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "images.id",
    name="dataset_images_image_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    split: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    label: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    sample_group: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
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