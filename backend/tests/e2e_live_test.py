#!/usr/bin/env python3
"""End-to-end live pipeline test.

Runs against the REAL backend (real Claude + real Modal endpoints).
NOT part of the pytest suite — run manually:

    cd backend
    python tests/e2e_live_test.py

Requires:
  - backend/.env with real keys + Modal URLs + DEBUG=false
  - Modal endpoints deployed and reachable
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure backend/src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def header(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 70}")
    print(f"  {text}")
    print(f"{'═' * 70}{RESET}\n")


def section(text: str) -> None:
    print(f"\n{BOLD}{BLUE}── {text} {'─' * (60 - len(text))}{RESET}")


def success(text: str) -> None:
    print(f"  {GREEN}✓{RESET} {text}")


def warn(text: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {text}")


def fail(text: str) -> None:
    print(f"  {RED}✗{RESET} {text}")


def info(text: str) -> None:
    print(f"  {CYAN}ℹ{RESET} {text}")


def pretty_json(data: dict, indent: int = 4) -> str:
    return json.dumps(data, indent=indent, default=str)


async def main():
    """Run the full E2E pipeline."""
    # ── Setup ──────────────────────────────────────────────
    header("MedAI — End-to-End Live Pipeline Test")
    info(f"Started at {datetime.now().isoformat()}")

    # Import after path setup
    from httpx import AsyncClient, ASGITransport
    from medai.main import create_app
    from medai.config import get_settings

    settings = get_settings()
    info(f"DEBUG mode: {settings.debug}")
    info(f"Orchestrator model: {settings.orchestrator_model}")
    info(f"MedGemma 4B endpoint: {settings.medgemma_4b_endpoint}")
    info(f"MedGemma 27B endpoint: {settings.medgemma_27b_endpoint}")
    info(f"HeAR endpoint: {settings.hear_endpoint}")

    if settings.debug:
        warn("DEBUG=true — using MOCK tools. Set DEBUG=false for real inference.")

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test", timeout=600) as client:

        # ═══════════════════════════════════════════════════
        #  TEST 1: Health Check
        # ═══════════════════════════════════════════════════
        section("Test 1: Health Check")
        t0 = time.time()
        resp = await client.get("/api/v1/health")
        success(f"GET /health → {resp.status_code} ({time.time()-t0:.1f}s)")
        print(f"    {resp.json()}")

        # ═══════════════════════════════════════════════════
        #  TEST 2: List Patients
        # ═══════════════════════════════════════════════════
        section("Test 2: List Seed Patients")
        resp = await client.get("/api/v1/patients")
        if resp.status_code != 200:
            fail(f"GET /patients → {resp.status_code}: {resp.text[:200]}")
            return
        patients = resp.json()
        success(f"GET /patients → {resp.status_code}, {patients['count']} patients")
        for p in patients.get("patients", []):
            info(f"  {p['id'][:8]}… — {p['name']} (DOB: {p['date_of_birth']})")

        first_patient_id = patients["patients"][0]["id"] if patients["patients"] else None

        # ═══════════════════════════════════════════════════
        #  TEST 3: Create a New Patient
        # ═══════════════════════════════════════════════════
        section("Test 3: Create New Patient")
        new_patient = {
            "name": "E2E Test Patient",
            "date_of_birth": "1960-03-15",
            "gender": "male",
            "medical_record_number": "MRN-E2E-001",
        }
        resp = await client.post("/api/v1/patients", json=new_patient)
        if resp.status_code not in (200, 201):
            fail(f"POST /patients → {resp.status_code}: {resp.text[:200]}")
            return
        created = resp.json()
        test_patient_id = created["id"]
        success(f"POST /patients → {resp.status_code}, ID={test_patient_id[:12]}…")

        # ═══════════════════════════════════════════════════
        #  TEST 4: Full Case Analysis — Image + Text (THE BIG ONE)
        # ═══════════════════════════════════════════════════
        section("Test 4: FULL CASE ANALYSIS 🧠")
        info("This calls: Claude orchestrator → picks tools → Modal inference → Judge → Report")
        info("First request may trigger Modal cold starts (2-5 min per model)…")

        case_request = {
            "patient_id": test_patient_id,
            "encounter_id": "ENC-E2E-001",
            "doctor_query": (
                "62-year-old male presents with 3-week progressive dyspnea, "
                "productive cough with yellowish sputum, and low-grade fever (37.8°C). "
                "40-pack-year smoking history. Physical exam: decreased breath sounds "
                "right lower lobe with dullness to percussion. "
                "Please analyze the chest X-ray, reason about the clinical picture, "
                "and provide a diagnosis with treatment plan."
            ),
            "clinical_context": (
                "Vitals: BP 135/85, HR 92, RR 22, SpO2 93% on room air. "
                "Weight loss of 4kg over past month."
            ),
            "image_urls": [
                "https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/1-s2.0-S0929664620300449-gr2_lrg-a.jpg"
            ],
            "patient_history_text": (
                "PMH: COPD (GOLD stage II), Hypertension, Type 2 DM. "
                "Medications: Tiotropium inhaler, Amlodipine 5mg, Metformin 1000mg BID. "
                "Allergies: Penicillin (rash). "
                "Prior hospitalisation: Pneumonia (2024), COPD exacerbation (2023). "
                "Social: Current smoker, 40-pack-year. Former construction worker (asbestos exposure)."
            ),
            "lab_results": [
                {"test": "WBC", "value": 14.2, "unit": "×10⁹/L", "reference": "4.5-11.0", "flag": "H"},
                {"test": "CRP", "value": 85, "unit": "mg/L", "reference": "<5", "flag": "H"},
                {"test": "Procalcitonin", "value": 0.8, "unit": "ng/mL", "reference": "<0.1", "flag": "H"},
                {"test": "Hemoglobin", "value": 12.1, "unit": "g/dL", "reference": "13.5-17.5", "flag": "L"},
                {"test": "Creatinine", "value": 1.1, "unit": "mg/dL", "reference": "0.7-1.3"},
                {"test": "HbA1c", "value": 7.2, "unit": "%", "reference": "<6.5", "flag": "H"},
            ],
        }

        print()
        t0 = time.time()
        resp = await client.post("/api/v1/cases/analyze", json=case_request)
        elapsed = time.time() - t0

        if resp.status_code != 200:
            fail(f"POST /cases/analyze → {resp.status_code}")
            print(f"    Error: {resp.text[:500]}")
            return
        
        report = resp.json()
        report_id = report["report_id"]
        success(f"POST /cases/analyze → {resp.status_code} ({elapsed:.1f}s)")
        success(f"Report ID: {report_id}")

        # ── Display Results ────────────────────────────────
        section("📋 DIAGNOSIS")
        print(f"    {BOLD}{report['diagnosis'][:200]}{RESET}")
        print(f"    Confidence: {report['confidence']}")

        section("📊 FINDINGS")
        for i, f in enumerate(report.get("findings", []), 1):
            severity = f.get("severity", "unknown")
            color = RED if severity in ("severe", "critical") else YELLOW if severity == "moderate" else GREEN
            print(f"    {i}. [{color}{severity.upper()}{RESET}] {f.get('finding', 'N/A')}")
            if f.get("explanation"):
                print(f"       {f['explanation'][:120]}")

        section("🧠 REASONING TRACE")
        for step in report.get("reasoning_trace", [])[:5]:
            if isinstance(step, dict):
                step_num = step.get("step", "?")
                thought = step.get("thought", str(step))[:150]
                print(f"    Step {step_num}: {thought}")

        section("📝 TREATMENT PLAN")
        for i, item in enumerate(report.get("plan", [])[:8], 1):
            print(f"    {i}. {item[:120]}")

        section("⚖️  JUDGE VERDICT")
        verdict = report.get("judge_verdict")
        if verdict:
            print(f"    Verdict: {verdict.get('verdict', 'N/A')}")
            print(f"    Confidence: {verdict.get('confidence', 'N/A')}")
            if verdict.get("reasoning"):
                print(f"    Reasoning: {verdict['reasoning'][:200]}")

        section("🔬 SPECIALIST SUMMARIES")
        for tool_name, summary in report.get("specialist_summaries", {}).items():
            print(f"    [{tool_name}]")
            # Truncate long summaries for display
            lines = summary[:300].split("\n")
            for line in lines[:4]:
                print(f"      {line}")

        section("🕐 TIMELINE IMPACT")
        print(f"    {report.get('timeline_impact', 'N/A')[:200]}")

        section("📎 EVIDENCE SUMMARY")
        print(f"    {report.get('evidence_summary', 'N/A')[:300]}")

        # ═══════════════════════════════════════════════════
        #  TEST 5: Retrieve Report by ID
        # ═══════════════════════════════════════════════════
        section("Test 5: Retrieve Report")
        resp = await client.get(f"/api/v1/cases/reports/{report_id}")
        success(f"GET /reports/{report_id[:12]}… → {resp.status_code}")

        # ═══════════════════════════════════════════════════
        #  TEST 6: Approve Report (Doctor Sign-off)
        # ═══════════════════════════════════════════════════
        section("Test 6: Doctor Approves Report")
        approval = {
            "report_id": report_id,
            "status": "approved",
            "doctor_notes": "Agree with CAP diagnosis. Will initiate empiric antibiotics per protocol.",
        }
        resp = await client.post("/api/v1/cases/approve", json=approval)
        if resp.status_code == 200:
            success(f"POST /cases/approve → {resp.status_code}")
            print(f"    {resp.json()}")
        else:
            warn(f"POST /cases/approve → {resp.status_code}: {resp.text[:200]}")

        # ═══════════════════════════════════════════════════
        #  TEST 7: Patient Reports List
        # ═══════════════════════════════════════════════════
        section("Test 7: Patient Reports")
        resp = await client.get(f"/api/v1/patients/{test_patient_id}/reports")
        if resp.status_code == 200:
            reports_data = resp.json()
            success(f"GET /patients/{test_patient_id[:12]}…/reports → {reports_data.get('count', 0)} reports")
        else:
            warn(f"→ {resp.status_code}: {resp.text[:200]}")

        # ═══════════════════════════════════════════════════
        #  TEST 8: Patient Timeline
        # ═══════════════════════════════════════════════════
        section("Test 8: Patient Timeline")
        if first_patient_id:
            resp = await client.get(f"/api/v1/patients/{first_patient_id}/timeline")
            if resp.status_code == 200:
                tl = resp.json()
                success(f"GET /patients/…/timeline → {tl.get('count', 0)} events")
                for ev in tl.get("events", [])[:3]:
                    info(f"  [{ev['event_type']}] {ev.get('summary', '')[:80]}")

        # ═══════════════════════════════════════════════════
        #  SUMMARY
        # ═══════════════════════════════════════════════════
        header("🏁 E2E TEST COMPLETE")
        success(f"Full pipeline executed in {elapsed:.1f}s")
        success(f"Claude orchestrator → Tool dispatch → Modal inference → Judge → Report")
        info(f"Report {report_id}")
        info(f"Diagnosis: {report['diagnosis'][:100]}")
        info(f"Confidence: {report['confidence']}")
        info(f"Findings: {len(report.get('findings', []))}")
        info(f"Plan items: {len(report.get('plan', []))}")

        # Dump full report to file for inspection
        report_path = Path(__file__).parent / "e2e_report_output.json"
        report_path.write_text(pretty_json(report))
        info(f"Full report saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
