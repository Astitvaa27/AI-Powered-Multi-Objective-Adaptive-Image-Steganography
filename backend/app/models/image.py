import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Image(Base):
    __tablename__ = "images"

    __table_args__ = (
        Index("ix_images_owner_id", "owner_id"),

        CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_images_file_size_nonnegative",
        ),
        CheckConstraint(
            "width > 0",
            name="ck_images_width_positive",
        ),
        CheckConstraint(
            "height > 0",
            name="ck_images_height_positive",
        ),
        CheckConstraint(
            "channels > 0",
            name="ck_images_channels_positive",
        ),
        CheckConstraint(
            "bit_depth IS NULL OR bit_depth > 0",
            name="ck_images_bit_depth_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "users.id",
    name="images_owner_id_fkey",
    ondelete="SET NULL",
),
        nullable=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_extension: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    channels: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    bit_depth: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    sha256_hash: Mapped[str] = mapped_column(
        CHAR(64),
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
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

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )