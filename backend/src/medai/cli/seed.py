"""Seed management command — populates the database with demo data.

Usage:
    python -m medai.cli.seed

Idempotent: skips records that already exist (matched by primary key).
Creates a default admin user + 3 demo patients + 23 timeline events.
"""

from __future__ import annotations

import asyncio
import os
import sys

from medai.api.auth import hash_password
from medai.domain.entities import User, UserRole
from medai.repositories.database import get_engine, get_session_factory, dispose_db
from medai.repositories.models import Base, PatientRow, TimelineEventRow, UserRow
from medai.repositories.seed import create_seed_patients, create_seed_timeline_events
from medai.repositories.sqlalchemy import (
    SqlAlchemyPatientRepository,
    SqlAlchemyTimelineRepository,
    SqlAlchemyUserRepository,
)


async def seed_database() -> None:
    """Seed the database with demo data."""
    engine = get_engine()

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory()

    async with factory() as session:
        user_repo = SqlAlchemyUserRepository(session)
        patient_repo = SqlAlchemyPatientRepository(session)
        timeline_repo = SqlAlchemyTimelineRepository(session)

        # ── Seed admin user ────────────────────────────────
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@medai.com")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "admin123")

        existing_admin = await user_repo.get_by_email(admin_email)
        if existing_admin is None:
            admin = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                name="System Admin",
                role=UserRole.ADMIN,
            )
            await user_repo.create(admin)
            print(f"  ✓ Created admin user: {admin_email}")
        else:
            print(f"  · Admin user already exists: {admin_email}")

        # ── Seed demo doctor ───────────────────────────────
        doctor_email = "doctor@medai.com"
        existing_doctor = await user_repo.get_by_email(doctor_email)
        if existing_doctor is None:
            doctor = User(
                email=doctor_email,
                hashed_password=hash_password("doctor123"),
                name="Dr. Demo Physician",
                role=UserRole.DOCTOR,
            )
            await user_repo.create(doctor)
            print(f"  ✓ Created demo doctor: {doctor_email}")
        else:
            print(f"  · Demo doctor already exists: {doctor_email}")

        # ── Seed patients ──────────────────────────────────
        patients = create_seed_patients()
        patients_created = 0
        for patient in patients:
            existing = await patient_repo.get(patient.id)
            if existing is None:
                await patient_repo.create(patient)
                patients_created += 1
        print(f"  ✓ Patients: {patients_created} created, {len(patients) - patients_created} already existed")

        # ── Seed timeline events ───────────────────────────
        events = create_seed_timeline_events()
        events_created = 0
        for event in events:
            # Check if event already exists by querying for its ID
            from sqlalchemy import select
            result = await session.execute(
                select(TimelineEventRow).where(TimelineEventRow.id == event.id)
            )
            if result.scalar_one_or_none() is None:
                await timeline_repo.add_event(event)
                events_created += 1
        print(f"  ✓ Timeline events: {events_created} created, {len(events) - events_created} already existed")

        await session.commit()

    await dispose_db()
    print("\n  Seed complete!")


def main() -> None:
    """Entrypoint for the seed command."""
    print("\n🌱 Seeding MedAI database...\n")
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
