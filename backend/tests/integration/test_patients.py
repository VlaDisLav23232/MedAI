"""Integration tests for patient, timeline, and report endpoints.

Uses FastAPI TestClient (ASGI in-process) — no real server needed.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy")
os.environ.setdefault("DEBUG", "true")

from medai.main import create_app  # noqa: E402


@pytest.fixture
def app():
    """Create a fresh app per test class to isolate in-memory state."""
    # Clear lru_cache singletons so each test class gets fresh repos
    from medai.api import dependencies
    from medai.config import get_settings

    for fn in [
        get_settings,
        dependencies.get_tool_registry,
        dependencies.get_anthropic_client,
        dependencies.get_patient_repository,
        dependencies.get_timeline_repository,
        dependencies.get_report_repository,
    ]:
        fn.cache_clear()

    return create_app()


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
        """DEBUG mode should seed 3 demo patients."""
        resp = await client.get("/api/v1/patients")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert len(data["patients"]) == 3

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
