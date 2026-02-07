"""Seed data — realistic demo patients and timeline events.

Loaded on startup in DEBUG mode so the API has data to serve
without needing a database or manual setup.
"""

from __future__ import annotations

from datetime import date, datetime

from medai.domain.entities import (
    Gender,
    Patient,
    TimelineEvent,
    TimelineEventType,
)


def create_seed_patients() -> list[Patient]:
    """Create a small set of realistic demo patients."""
    return [
        Patient(
            id="PT-DEMO0001",
            name="Maria Ivanova",
            date_of_birth=date(1985, 3, 15),
            gender=Gender.FEMALE,
            medical_record_number="MRN-2024-001",
        ),
        Patient(
            id="PT-DEMO0002",
            name="Oleksandr Petrenko",
            date_of_birth=date(1972, 11, 22),
            gender=Gender.MALE,
            medical_record_number="MRN-2024-002",
        ),
        Patient(
            id="PT-DEMO0003",
            name="Natalia Kovalenko",
            date_of_birth=date(1995, 7, 8),
            gender=Gender.FEMALE,
            medical_record_number="MRN-2024-003",
        ),
    ]


def create_seed_timeline_events() -> list[TimelineEvent]:
    """Create demo timeline entries linked to seed patients."""
    return [
        # ── Maria Ivanova (PT-DEMO0001) ──
        TimelineEvent(
            id="TL-SEED0001",
            patient_id="PT-DEMO0001",
            date=datetime(2024, 6, 1, 9, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary="Initial consultation – persistent cough, chest discomfort for 3 weeks.",
            source_type="encounter",
            metadata={"chief_complaint": "persistent cough"},
        ),
        TimelineEvent(
            id="TL-SEED0002",
            patient_id="PT-DEMO0001",
            date=datetime(2024, 6, 2, 14, 30),
            event_type=TimelineEventType.IMAGING,
            summary="Chest X-ray – mild bilateral infiltrates noted.",
            source_type="imaging",
            metadata={"modality": "xray", "body_region": "chest"},
        ),
        TimelineEvent(
            id="TL-SEED0003",
            patient_id="PT-DEMO0001",
            date=datetime(2024, 6, 3, 10, 0),
            event_type=TimelineEventType.LAB,
            summary="CBC + CRP – elevated CRP (25 mg/L), mild leukocytosis.",
            source_type="lab",
            metadata={"crp": 25.0, "wbc": 12.4},
        ),

        # ── Oleksandr Petrenko (PT-DEMO0002) ──
        TimelineEvent(
            id="TL-SEED0004",
            patient_id="PT-DEMO0002",
            date=datetime(2024, 5, 10, 8, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary="Routine checkup – history of Type 2 DM, well controlled.",
            source_type="encounter",
            metadata={"chief_complaint": "routine follow-up"},
        ),
        TimelineEvent(
            id="TL-SEED0005",
            patient_id="PT-DEMO0002",
            date=datetime(2024, 5, 10, 8, 30),
            event_type=TimelineEventType.LAB,
            summary="HbA1c 6.8%, fasting glucose 128 mg/dL.",
            source_type="lab",
            metadata={"hba1c": 6.8, "fasting_glucose": 128},
        ),
        TimelineEvent(
            id="TL-SEED0006",
            patient_id="PT-DEMO0002",
            date=datetime(2024, 6, 15, 11, 0),
            event_type=TimelineEventType.IMAGING,
            summary="Fundus imaging – no diabetic retinopathy detected.",
            source_type="imaging",
            metadata={"modality": "fundus"},
        ),

        # ── Natalia Kovalenko (PT-DEMO0003) ──
        TimelineEvent(
            id="TL-SEED0007",
            patient_id="PT-DEMO0003",
            date=datetime(2024, 7, 1, 16, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary="Urgent visit – skin lesion on left forearm, growing for 2 months.",
            source_type="encounter",
            metadata={"chief_complaint": "skin lesion"},
        ),
        TimelineEvent(
            id="TL-SEED0008",
            patient_id="PT-DEMO0003",
            date=datetime(2024, 7, 2, 9, 0),
            event_type=TimelineEventType.IMAGING,
            summary="Dermoscopic image captured – asymmetric pigmented lesion 8mm.",
            source_type="imaging",
            metadata={"modality": "dermatology", "lesion_size_mm": 8},
        ),
    ]
