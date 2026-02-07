"""Integration test — tests the live FastAPI app using TestClient.

No real server needed. Uses httpx TestClient which runs the ASGI app in-process.
This is the recommended way to test FastAPI apps per their documentation.
"""

import json
import sys
from datetime import datetime

# Use FastAPI's TestClient (httpx based, runs in-process)
from fastapi.testclient import TestClient


def main() -> int:
    """Run integration tests against the live app."""
    # Set env vars before importing app
    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy")
    os.environ.setdefault("DEBUG", "true")

    # Clear lru_cache to pick up env vars
    from medai.config import get_settings
    get_settings.cache_clear()

    from medai.main import create_app
    from medai.api.dependencies import get_tool_registry, get_anthropic_client, get_orchestrator

    # Clear all caches
    get_tool_registry.cache_clear()
    get_anthropic_client.cache_clear()

    app = create_app()
    client = TestClient(app)

    passed = 0
    failed = 0
    total = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name} — {detail}")

    # ═══════════════════════════════════════════════════════
    #  1. Health Check
    # ═══════════════════════════════════════════════════════
    print("\n🏥 1. Health Check")
    resp = client.get("/api/v1/health")
    check("Status 200", resp.status_code == 200, f"got {resp.status_code}")

    data = resp.json()
    check("status = ok", data.get("status") == "ok", f"got {data.get('status')}")
    check("version present", "version" in data, "missing version field")
    check("tools_registered is list", isinstance(data.get("tools_registered"), list))
    check(
        "4 tools registered",
        len(data.get("tools_registered", [])) == 4,
        f"got {len(data.get('tools_registered', []))} tools",
    )
    check("debug = true", data.get("debug") is True, f"got {data.get('debug')}")

    expected_tools = {"image_analysis", "text_reasoning", "audio_analysis", "history_search"}
    actual_tools = set(data.get("tools_registered", []))
    check("correct tool names", actual_tools == expected_tools, f"got {actual_tools}")

    print(f"\n  Response:\n{json.dumps(data, indent=2)}")

    # ═══════════════════════════════════════════════════════
    #  2. Case Analysis — Full Case (image + text + audio)
    # ═══════════════════════════════════════════════════════
    print("\n🔬 2. Case Analysis — Full Case")
    case_request = {
        "patient_id": "PT-TEST001",
        "doctor_query": "Assess for any pathology, compare with previous imaging",
        "clinical_context": "Persistent cough x 3 weeks, fever 38.5°C, right-sided chest pain",
        "image_urls": ["s3://bucket/cxr-20260207.dcm"],
        "audio_urls": ["s3://bucket/breathing-20260207.wav"],
        "patient_history_text": "45yo male, no prior respiratory disease, non-smoker",
        "lab_results": [
            {"test": "WBC", "value": 14.2, "unit": "k/uL", "reference": "4.5-11.0"},
            {"test": "CRP", "value": 45, "unit": "mg/L", "reference": "<5"},
        ],
    }

    resp = client.post("/api/v1/cases/analyze", json=case_request)
    check("Status 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text[:200]}")

    report = resp.json()

    # Validate top-level fields
    check("report_id present", "report_id" in report)
    check("report_id starts with RPT-", report.get("report_id", "").startswith("RPT-"))
    check("patient_id matches", report.get("patient_id") == "PT-TEST001")
    check("diagnosis present", bool(report.get("diagnosis")))
    check("confidence is float", isinstance(report.get("confidence"), (int, float)))
    check("confidence in [0,1]", 0 <= report.get("confidence", -1) <= 1)
    check("plan is list", isinstance(report.get("plan"), list))
    check("plan has items", len(report.get("plan", [])) > 0)
    check("findings is list", isinstance(report.get("findings"), list))
    check("findings has items", len(report.get("findings", [])) > 0)
    check("reasoning_trace is list", isinstance(report.get("reasoning_trace"), list))
    check("evidence_summary present", bool(report.get("evidence_summary")))
    check("timeline_impact present", bool(report.get("timeline_impact")))
    check("approval_status = pending", report.get("approval_status") == "pending")
    check("created_at present", bool(report.get("created_at")))

    # Validate judge verdict
    verdict = report.get("judge_verdict")
    check("judge_verdict present", verdict is not None)
    if verdict:
        check("verdict is consensus", verdict.get("verdict") == "consensus")
        check("verdict confidence in [0,1]", 0 <= verdict.get("confidence", -1) <= 1)
        check("verdict reasoning present", bool(verdict.get("reasoning")))

    # Validate findings structure
    if report.get("findings"):
        f = report["findings"][0]
        check("finding has 'finding' field", "finding" in f)
        check("finding has confidence", "confidence" in f)
        check("finding has explanation", "explanation" in f)
        check("finding has severity", "severity" in f)

    print(f"\n  Diagnosis: {report.get('diagnosis')}")
    print(f"  Confidence: {report.get('confidence')}")
    print(f"  Findings: {len(report.get('findings', []))}")
    print(f"  Plan items: {len(report.get('plan', []))}")
    print(f"  Judge: {verdict.get('verdict') if verdict else 'N/A'}")

    # ═══════════════════════════════════════════════════════
    #  3. Case Analysis — Text Only (no images/audio)
    # ═══════════════════════════════════════════════════════
    print("\n📝 3. Case Analysis — Text Only")
    text_request = {
        "patient_id": "PT-TEST002",
        "doctor_query": "Review patient history and assess cardiovascular risk",
        "clinical_context": "Annual check-up, family history of heart disease",
        "patient_history_text": "62yo female, HTN controlled with lisinopril 10mg, BMI 28",
    }

    resp = client.post("/api/v1/cases/analyze", json=text_request)
    check("Status 200", resp.status_code == 200, f"got {resp.status_code}")
    text_report = resp.json()
    check("No image findings in text-only case or findings present",
          isinstance(text_report.get("findings"), list))
    check("Patient ID correct", text_report.get("patient_id") == "PT-TEST002")

    # ═══════════════════════════════════════════════════════
    #  4. Report Approval
    # ═══════════════════════════════════════════════════════
    print("\n✅ 4. Report Approval")
    approval_request = {
        "report_id": report.get("report_id", "RPT-TEST"),
        "status": "approved",
        "doctor_notes": "Concur with AI assessment. Starting antibiotics.",
    }

    resp = client.post("/api/v1/cases/approve", json=approval_request)
    check("Status 200", resp.status_code == 200, f"got {resp.status_code}")
    approval = resp.json()
    check("report_id matches", approval.get("report_id") == approval_request["report_id"])
    check("status = approved", approval.get("status") == "approved")
    check("updated_at present", bool(approval.get("updated_at")))

    # ═══════════════════════════════════════════════════════
    #  5. OpenAPI Schema
    # ═══════════════════════════════════════════════════════
    print("\n📖 5. OpenAPI Schema")
    resp = client.get("/openapi.json")
    check("Status 200", resp.status_code == 200)
    schema = resp.json()
    check("title present", "MedAI" in schema.get("info", {}).get("title", ""))
    check("paths present", len(schema.get("paths", {})) >= 3)
    paths = list(schema.get("paths", {}).keys())
    check("/api/v1/health in paths", "/api/v1/health" in paths, f"paths: {paths}")
    check("/api/v1/cases/analyze in paths", "/api/v1/cases/analyze" in paths)
    check("/api/v1/cases/approve in paths", "/api/v1/cases/approve" in paths)

    # ═══════════════════════════════════════════════════════
    #  6. Error Handling
    # ═══════════════════════════════════════════════════════
    print("\n🚨 6. Error Handling")
    # Missing required fields
    resp = client.post("/api/v1/cases/analyze", json={})
    check("422 on missing fields", resp.status_code == 422, f"got {resp.status_code}")

    # Invalid approval status
    resp = client.post("/api/v1/cases/approve", json={
        "report_id": "RPT-TEST",
        "status": "invalid_status",
    })
    check("422 on invalid enum", resp.status_code == 422, f"got {resp.status_code}")

    # ═══════════════════════════════════════════════════════
    #  Summary
    # ═══════════════════════════════════════════════════════
    print(f"\n{'═' * 50}")
    print(f"  INTEGRATION TESTS: {passed}/{total} passed, {failed} failed")
    print(f"{'═' * 50}")

    if failed > 0:
        print("\n⚠️  Some tests failed! Review the output above.")
        return 1
    else:
        print("\n🎉 All integration tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
