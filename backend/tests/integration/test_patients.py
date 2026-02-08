"""Integration tests for patient, timeline, and report endpoints.

Uses FastAPI TestClient (ASGI in-process) with an in-memory SQLite DB.
Each test class gets a fresh database with tables + seed data.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy")
os.environ.setdefault("DEBUG", "true")

import json  # noqa: E402
from datetime import date, datetime  # noqa: E402

from medai.api.auth import get_current_user  # noqa: E402
from medai.domain.entities import User, UserRole  # noqa: E402
from medai.main import create_app  # noqa: E402
from medai.repositories.database import get_db_session  # noqa: E402
from medai.repositories.models import Base, TimelineEventRow  # noqa: E402
from medai.repositories.seed import (  # noqa: E402
    create_seed_patients,
    create_seed_timeline_events,
)
from medai.repositories.sqlalchemy import (  # noqa: E402
    SqlAlchemyPatientRepository,
    SqlAlchemyTimelineRepository,
)

# ── Dummy user returned by the auth override ───────────────
_TEST_USER = User(
    id="USR-TEST0001",
    email="test@medai.com",
    hashed_password="not-used",
    name="Test Doctor",
    role=UserRole.DOCTOR,
)


@pytest_asyncio.fixture
async def _db_session_factory():
    """Create a fresh in-memory SQLite engine + tables + seed data."""

    def _json_serializer(obj):
        """JSON serializer that handles datetime objects (needed for SQLite)."""
        def default(o):
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
        return json.dumps(obj, default=default)

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        json_serializer=_json_serializer,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed demo data
    async with factory() as session:
        patient_repo = SqlAlchemyPatientRepository(session)
        timeline_repo = SqlAlchemyTimelineRepository(session)

        for patient in create_seed_patients():
            await patient_repo.create(patient)

        for event in create_seed_timeline_events():
            await timeline_repo.add_event(event)

        await session.commit()

    yield factory

    await engine.dispose()


@pytest.fixture
def app(_db_session_factory):
    """Create a fresh app with test DB and auth overrides."""
    from medai.api import dependencies
    from medai.config import get_settings

    for fn in [
        get_settings,
        dependencies.get_tool_registry,
        dependencies.get_anthropic_client,
    ]:
        if hasattr(fn, "cache_clear"):
            fn.cache_clear()

    application = create_app()

    # Override DB session to use test in-memory SQLite
    async def _override_db_session():
        async with _db_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[get_db_session] = _override_db_session

    # Bypass JWT auth
    async def _override_current_user() -> User:
        return _TEST_USER

    application.dependency_overrides[get_current_user] = _override_current_user

    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ═══════════════════════════════════════════════════════════════
#  Patient Endpoints
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPatientList:
    @pytest.mark.asyncio
    async def test_list_patients_returns_seed_data(self, client):
        """DEBUG mode should seed 4 demo patients."""
        resp = await client.get("/api/v1/patients")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 4
        assert len(data["patients"]) == 4

    @pytest.mark.asyncio
    async def test_list_patients_structure(self, client):
        resp = await client.get("/api/v1/patients")
        data = resp.json()
        p = data["patients"][0]
        assert "id" in p
        assert "name" in p
        assert "date_of_birth" in p
        assert "gender" in p
        assert "created_at" in p


@pytest.mark.integration
class TestPatientGet:
    @pytest.mark.asyncio
    async def test_get_existing_patient(self, client):
        resp = await client.get("/api/v1/patients/PT-DEMO0001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "PT-DEMO0001"
        assert data["name"] == "Maria Ivanova"
        assert data["gender"] == "female"

    @pytest.mark.asyncio
    async def test_get_nonexistent_patient(self, client):
        resp = await client.get("/api/v1/patients/PT-DOES-NOT-EXIST")
        assert resp.status_code == 404


@pytest.mark.integration
class TestPatientCreate:
    @pytest.mark.asyncio
    async def test_create_patient(self, client):
        payload = {
            "name": "New Patient",
            "date_of_birth": "2000-05-20",
            "gender": "male",
            "medical_record_number": "MRN-NEW-001",
        }
        resp = await client.post("/api/v1/patients", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Patient"
        assert data["date_of_birth"] == "2000-05-20"
        assert data["gender"] == "male"
        assert data["id"].startswith("PT-")

    @pytest.mark.asyncio
    async def test_create_patient_minimal(self, client):
        payload = {
            "name": "Minimal Patient",
            "date_of_birth": "1999-12-31",
        }
        resp = await client.post("/api/v1/patients", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["gender"] == "unknown"

    @pytest.mark.asyncio
    async def test_create_and_retrieve(self, client):
        payload = {
            "name": "Roundtrip Test",
            "date_of_birth": "1988-03-10",
            "gender": "female",
        }
        create_resp = await client.post("/api/v1/patients", json=payload)
        patient_id = create_resp.json()["id"]

        get_resp = await client.get(f"/api/v1/patients/{patient_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Roundtrip Test"

    @pytest.mark.asyncio
    async def test_create_shows_in_list(self, client):
        # Initial count = 3 (seed)
        resp0 = await client.get("/api/v1/patients")
        initial_count = resp0.json()["count"]

        await client.post("/api/v1/patients", json={
            "name": "Extra", "date_of_birth": "2001-01-01",
        })

        resp1 = await client.get("/api/v1/patients")
        assert resp1.json()["count"] == initial_count + 1

    @pytest.mark.asyncio
    async def test_create_patient_validation_error(self, client):
        resp = await client.post("/api/v1/patients", json={"bad": "data"})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════
#  Timeline Endpoints
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPatientTimeline:
    @pytest.mark.asyncio
    async def test_timeline_for_demo_patient(self, client):
        """Maria Ivanova has 9 seed timeline events (rich multi-visit history)."""
        resp = await client.get("/api/v1/patients/PT-DEMO0001/timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["patient_id"] == "PT-DEMO0001"
        assert data["count"] == 9
        assert len(data["events"]) == 9

    @pytest.mark.asyncio
    async def test_timeline_sorted_newest_first(self, client):
        resp = await client.get("/api/v1/patients/PT-DEMO0001/timeline")
        data = resp.json()
        dates = [e["date"] for e in data["events"]]
        # Verify descending order
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_timeline_event_structure(self, client):
        resp = await client.get("/api/v1/patients/PT-DEMO0001/timeline")
        event = resp.json()["events"][0]
        assert "id" in event
        assert "date" in event
        assert "event_type" in event
        assert "summary" in event

    @pytest.mark.asyncio
    async def test_timeline_for_nonexistent_patient(self, client):
        resp = await client.get("/api/v1/patients/PT-FAKE/timeline")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_different_patients_have_different_timelines(self, client):
        r1 = await client.get("/api/v1/patients/PT-DEMO0001/timeline")
        r2 = await client.get("/api/v1/patients/PT-DEMO0002/timeline")
        r3 = await client.get("/api/v1/patients/PT-DEMO0003/timeline")

        assert r1.json()["count"] == 9
        assert r2.json()["count"] == 7
        assert r3.json()["count"] == 7


# ═══════════════════════════════════════════════════════════════
#  Patient Reports Endpoint
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPatientReports:
    @pytest.mark.asyncio
    async def test_reports_empty_initially(self, client):
        resp = await client.get("/api/v1/patients/PT-DEMO0001/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["patient_id"] == "PT-DEMO0001"
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_reports_appear_after_analysis(self, client):
        # Run an analysis for a demo patient
        analyze_payload = {
            "patient_id": "PT-DEMO0001",
            "doctor_query": "Evaluate chest X-ray findings",
            "image_urls": ["http://example.com/chest.png"],
        }
        analyze_resp = await client.post("/api/v1/cases/analyze", json=analyze_payload)
        assert analyze_resp.status_code == 200

        # Now check reports
        reports_resp = await client.get("/api/v1/patients/PT-DEMO0001/reports")
        data = reports_resp.json()
        assert data["count"] == 1
        assert data["reports"][0]["report_id"] == analyze_resp.json()["report_id"]
        assert data["reports"][0]["approval_status"] == "pending"

    @pytest.mark.asyncio
    async def test_reports_for_nonexistent_patient(self, client):
        resp = await client.get("/api/v1/patients/PT-FAKE/reports")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  Report Retrieval & Approval (full flow)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestReportLifecycle:
    @pytest.mark.asyncio
    async def test_full_report_lifecycle(self, client):
        """analyze → retrieve → approve → verify status."""
        # 1) Analyze
        resp1 = await client.post("/api/v1/cases/analyze", json={
            "patient_id": "PT-DEMO0002",
            "doctor_query": "Evaluate HbA1c trend",
            "clinical_context": "Diabetes follow-up",
        })
        assert resp1.status_code == 200
        report_id = resp1.json()["report_id"]

        # 2) Retrieve by ID
        resp2 = await client.get(f"/api/v1/cases/reports/{report_id}")
        assert resp2.status_code == 200
        assert resp2.json()["report_id"] == report_id
        assert resp2.json()["approval_status"] == "pending"

        # 3) Approve
        resp3 = await client.post("/api/v1/cases/approve", json={
            "report_id": report_id,
            "status": "approved",
            "doctor_notes": "Confirmed, continue current plan",
        })
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "approved"

        # 4) Retrieve again — status should be updated
        resp4 = await client.get(f"/api/v1/cases/reports/{report_id}")
        assert resp4.status_code == 200
        assert resp4.json()["approval_status"] == "approved"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_report(self, client):
        resp = await client.get("/api/v1/cases/reports/RPT-NONEXISTENT")
        assert resp.status_code == 404
