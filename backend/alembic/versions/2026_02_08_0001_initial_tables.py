"""Initial tables: users, patients, timeline_events, final_reports

Revision ID: 0001
Revises: None
Create Date: 2026-02-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ──────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="doctor"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # ── Patients ───────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date_of_birth", sa.String(10), nullable=False),
        sa.Column("gender", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("medical_record_number", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── Timeline Events ───────────────────────────────────
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("patient_id", sa.String(20), nullable=False),
        sa.Column("date", sa.DateTime, nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("source_id", sa.String(50), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
    )
    op.create_index("ix_timeline_events_patient_id", "timeline_events", ["patient_id"])

    # ── Final Reports ─────────────────────────────────────
    op.create_table(
        "final_reports",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("encounter_id", sa.String(20), nullable=False),
        sa.Column("patient_id", sa.String(20), nullable=False),
        sa.Column("diagnosis", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("confidence_method", sa.String(30), nullable=False, server_default="model_self_reported"),
        sa.Column("evidence_summary", sa.Text, nullable=False),
        sa.Column("timeline_impact", sa.Text, nullable=False),
        sa.Column("plan", sa.JSON, nullable=True),
        sa.Column("findings", sa.JSON, nullable=True),
        sa.Column("reasoning_trace", sa.JSON, nullable=True),
        sa.Column("specialist_outputs", sa.JSON, nullable=True),
        sa.Column("judge_verdict", sa.JSON, nullable=True),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("doctor_notes", sa.Text, nullable=True),
        sa.Column("pipeline_metrics", sa.JSON, nullable=True),
    )
    op.create_index("ix_final_reports_patient_id", "final_reports", ["patient_id"])


def downgrade() -> None:
    op.drop_table("final_reports")
    op.drop_table("timeline_events")
    op.drop_table("patients")
    op.drop_table("users")
