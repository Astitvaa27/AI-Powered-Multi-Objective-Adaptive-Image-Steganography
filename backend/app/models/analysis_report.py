import uuid
from datetime import datetime

from sqlalchemy import Index, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    __table_args__ = (
        Index("ix_analysis_reports_analysis_session_id", "analysis_session_id"),
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
    name="analysis_reports_analysis_session_id_fkey",
    ondelete="RESTRICT",
),
        nullable=False,
    )

    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    report_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    report_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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