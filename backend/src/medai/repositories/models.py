"""SQLAlchemy table models — the relational schema.

Maps domain entities to PostgreSQL tables.
All IDs are application-generated strings (e.g. PT-ABCDEF12),
NOT auto-increment integers — matches the Pydantic entity pattern.

JSON columns store nested Pydantic structures (findings, reasoning_trace, etc.)
to avoid over-normalization. This is appropriate for a prototype; normalize
if query patterns demand it later.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all models."""
    pass


class UserRow(Base):
    """users table — authenticated system users."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="doctor")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )


class PatientRow(Base):
    """patients table — core patient records."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[str] = mapped_column(String(10), nullable=False)  # ISO date string
    gender: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    medical_record_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class TimelineEventRow(Base):
    """timeline_events table — patient timeline entries."""

    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )

    __table_args__ = (
        Index("ix_timeline_events_patient_id", "patient_id"),
    )


class FinalReportRow(Base):
    """final_reports table — AI-generated medical reports."""

    __tablename__ = "final_reports"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    encounter_id: Mapped[str] = mapped_column(String(20), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_method: Mapped[str] = mapped_column(
        String(30), nullable=False, default="model_self_reported"
    )
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    timeline_impact: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[list | None] = mapped_column(JSON, nullable=True)
    findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reasoning_trace: Mapped[list | None] = mapped_column(JSON, nullable=True)
    specialist_outputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    judge_verdict: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pipeline_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_final_reports_patient_id", "patient_id"),
    )
