import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class EmbeddingConfiguration(Base):
    __tablename__ = "embedding_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "embedding_methods.id",
    name="embedding_configurations_method_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    configuration_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    region_strategy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    payload_allocation_strategy: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )