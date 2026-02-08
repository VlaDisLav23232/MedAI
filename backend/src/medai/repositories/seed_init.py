"""Seeding utility — populate database with admin user and demo patients."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from medai.repositories.database import get_session_factory
from medai.repositories.seed import create_admin_user, create_seed_patients, create_seed_timeline_events
from medai.repositories.sqlalchemy import SqlAlchemyUserRepository, SqlAlchemyPatientRepository, SqlAlchemyTimelineRepository

logger = structlog.get_logger()


async def seed_initial_data() -> None:
    """Seed admin user + demo patients + timeline events (idempotent)."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            # Seed admin user
            user_repo = SqlAlchemyUserRepository(session)
            existing_admin = await user_repo.get_by_email("admin@medai.local")
            if not existing_admin:
                admin = create_admin_user()
                await user_repo.create(admin)
                logger.info("seeded_admin_user", email=admin.email)
            else:
                logger.info("admin_user_already_exists")

            # Seed demo patients
            patient_repo = SqlAlchemyPatientRepository(session)
            demo_patients = create_seed_patients()
            seeded_count = 0
            for patient in demo_patients:
                existing = await patient_repo.get(patient.id)
                if not existing:
                    await patient_repo.create(patient)
                    seeded_count += 1
            logger.info("seeded_demo_patients", count=seeded_count, total=len(demo_patients))

            # Seed timeline events
            timeline_repo = SqlAlchemyTimelineRepository(session)
            events = create_seed_timeline_events()
            event_seeded_count = 0
            for event in events:
                # Check if event already exists
                existing_events = await timeline_repo.get_for_patient(event.patient_id)
                if not any(e.id == event.id for e in existing_events):
                    await timeline_repo.add_event(event)
                    event_seeded_count += 1
            logger.info("seeded_timeline_events", count=event_seeded_count, total=len(events))

            await session.commit()
            logger.info("seed_data_complete")
        except Exception as e:
            await session.rollback()
            logger.error("seed_data_failed", error=str(e))
            raise
