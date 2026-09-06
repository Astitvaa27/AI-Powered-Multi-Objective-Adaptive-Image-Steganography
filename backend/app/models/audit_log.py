import uuid
from datetime import datetime

from sqlalchemy import Index, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "users.id",
    name="audit_logs_user_id_fkey",
    ondelete="SET NULL",
),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    old_values: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    new_values: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )