import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Payload(Base):
    __tablename__ = "payloads"

    __table_args__ = (
        CheckConstraint(
            "original_size_bytes >= 0",
            name="ck_payload_original_size_nonnegative",
        ),
        CheckConstraint(
            "encoded_size_bytes IS NULL OR encoded_size_bytes >= 0",
            name="ck_payload_encoded_size_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    payload_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    original_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    encoded_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    payload_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    storage_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    encryption_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    encryption_algorithm: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    encryption_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )