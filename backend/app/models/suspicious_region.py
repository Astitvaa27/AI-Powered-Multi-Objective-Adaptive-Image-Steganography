import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class SuspiciousRegion(Base):
    __tablename__ = "suspicious_regions"

    __table_args__ = (
        Index("ix_suspicious_regions_analysis_session_id", "analysis_session_id"),

        CheckConstraint(
            "x >= 0",
            name="ck_suspicious_region_x_nonnegative",
        ),
        CheckConstraint(
            "y >= 0",
            name="ck_suspicious_region_y_nonnegative",
        ),
        CheckConstraint(
            "width > 0",
            name="ck_suspicious_region_width_positive",
        ),
        CheckConstraint(
            "height > 0",
            name="ck_suspicious_region_height_positive",
        ),
        CheckConstraint(
            "suspicion_score IS NULL OR "
            "(suspicion_score >= 0 AND suspicion_score <= 1)",
            name="ck_suspicious_region_score_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
    "analysis_sessions.id",
    name="suspicious_regions_analysis_session_id_fkey",
    ondelete="RESTRICT",
),
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

    suspicion_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    region_type: Mapped[str | None] = mapped_column(
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