"""Integration tests for the FastAPI endpoints.

Boots the full app with mock tools and tests HTTP request/response.
"""

from __future__ import annotations

import os

# Ensure test environment
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"
os.environ["DEBUG"] = "true"

import pytest
from httpx import AsyncClient, ASGITransport

from medai.main import create_app


@pytest.fixture
def app():
    """Create a fresh app for each test."""
    return create_app()


@pytest.fixture
async def client(app):
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════════════════════════
#  Health Check
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "tools_registered" in data
        assert len(data["tools_registered"]) == 5  # all mock tools
        assert "image_analysis" in data["tools_registered"]
        assert "text_reasoning" in data["tools_registered"]


# ═══════════════════════════════════════════════════════════════
#  Case Analysis
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestCaseAnalysisEndpoint:
    @pytest.mark.asyncio
    async def test_analyze_minimal_case(self, client):
        """Test minimal case analysis (text only)."""
        payload = {
            "patient_id": "PT-API-001",
            "doctor_query": "Assess for pneumonia",
            "clinical_context": "3-week cough, fever",
        }
        response = await client.post("/api/v1/cases/analyze", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == "PT-API-001"
        assert "report_id" in data
        assert data["report_id"].startswith("RPT-")
        assert "diagnosis" in data
        assert "confidence" in data
        assert 0 <= data["confidence"] <= 1
        assert "findings" in data
        assert "plan" in data
        assert "reasoning_trace" in data
        assert data["approval_status"] == "pending"

    @pytest.mark.asyncio
    async def test_analyze_case_with_image(self, client):
        """Test case with image URL triggers image analysis."""
        payload = {
            "patient_id": "PT-API-002",
            "doctor_query": "Rule out pneumonia",
            "clinical_context": "Cough with fever",
            "image_urls": ["s3://bucket/cxr.dcm"],
        }
        response = await client.post("/api/v1/cases/analyze", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert len(data["findings"]) > 0
        # Should have heatmap from image analysis
        assert len(data["heatmap_urls"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_case_response_contract(self, client):
        """Validate the full response JSON contract."""
        payload = {
            "patient_id": "PT-API-003",
            "encounter_id": "ENC-003",
            "doctor_query": "Full assessment",
            "clinical_context": "Multi-modal",
            "image_urls": ["cxr.dcm"],
            "audio_urls": ["breath.wav"],
        }
        response = await client.post("/api/v1/cases/analyze", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Validate all required response fields
        required = [
            "report_id", "encounter_id", "patient_id",
            "diagnosis", "confidence", "evidence_summary",
            "timeline_impact", "plan", "findings",
            "reasoning_trace", "judge_verdict",
            "approval_status", "created_at",
            "heatmap_urls", "specialist_summaries",
        ]
        for field in required:
            assert field in data, f"Missing response field: {field}"

    @pytest.mark.asyncio
    async def test_analyze_case_validation_error(self, client):
        """Test that invalid request returns 422."""
        payload = {"not_valid": True}  # Missing required fields
        response = await client.post("/api/v1/cases/analyze", json=payload)
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
#  Report Approval
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestApprovalEndpoint:
    @pytest.mark.asyncio
    async def test_approve_report(self, client):
        # First create a report via the analyze endpoint
        analyze_payload = {
            "patient_id": "PT-APPROVE-1",
            "doctor_query": "Check for approval",
            "image_urls": ["http://example.com/img.png"],
        }
        analyze_resp = await client.post("/api/v1/cases/analyze", json=analyze_payload)
        assert analyze_resp.status_code == 200
        report_id = analyze_resp.json()["report_id"]

        # Now approve it
        payload = {
            "report_id": report_id,
            "status": "approved",
            "doctor_notes": "Looks correct",
        }
        response = await client.post("/api/v1/cases/approve", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["report_id"] == report_id
        assert data["status"] == "approved"

    @pytest.mark.asyncio
    async def test_reject_report(self, client):
        # First create a report
        analyze_payload = {
            "patient_id": "PT-REJECT-1",
            "doctor_query": "Check for rejection",
            "image_urls": ["http://example.com/img.png"],
        }
        analyze_resp = await client.post("/api/v1/cases/analyze", json=analyze_payload)
        assert analyze_resp.status_code == 200
        report_id = analyze_resp.json()["report_id"]

        # Now reject it
        payload = {
            "report_id": report_id,
            "status": "rejected",
            "doctor_notes": "Incorrect diagnosis",
        }
        response = await client.post("/api/v1/cases/approve", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_approve_nonexistent_report(self, client):
        """Approving a non-existent report returns 404."""
        payload = {
            "report_id": "RPT-NONEXISTENT",
            "status": "approved",
        }
        response = await client.post("/api/v1/cases/approve", json=payload)
        assert response.status_code == 404
