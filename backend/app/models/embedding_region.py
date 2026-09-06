import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class EmbeddingRegion(Base):
    __tablename__ = "embedding_regions"

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "region_index",
            name="uq_embedding_region_session_index",
        ),
        CheckConstraint(
            "region_index >= 0",
            name="ck_embedding_region_index_nonnegative",
        ),
        CheckConstraint(
            "x >= 0",
            name="ck_embedding_region_x_nonnegative",
        ),
        CheckConstraint(
            "y >= 0",
            name="ck_embedding_region_y_nonnegative",
        ),
        CheckConstraint(
            "width > 0",
            name="ck_embedding_region_width_positive",
        ),
        CheckConstraint(
            "height > 0",
            name="ck_embedding_region_height_positive",
        ),
        CheckConstraint(
            "allocation_ratio IS NULL OR "
            "(allocation_ratio >= 0 AND allocation_ratio <= 1)",
            name="ck_embedding_region_allocation_range",
        ),
        CheckConstraint(
            "embedding_score IS NULL OR "
            "(embedding_score >= 0 AND embedding_score <= 1)",
            name="ck_embedding_region_score_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "steganography_sessions.id",
    name="embedding_regions_session_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    region_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    x: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    y: Mapped[int] = mapped_column(
        Integer,
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

    allocation_ratio: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    embedding_score: Mapped[float | None] = mapped_column(
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