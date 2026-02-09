"""Regression test for datetime JSON serialization bug.

Reproduces the exact error:
    sqlalchemy.exc.StatementError: (builtins.TypeError)
    Object of type datetime is not JSON serializable
"""

import json
import pytest
from datetime import datetime, date
from enum import Enum

from medai.repositories.sqlalchemy import _json_safe


class _TestEnum(str, Enum):
    A = "a"


class TestJsonSafe:

    def test_primitives_pass_through(self):
        assert _json_safe(None) is None
        assert _json_safe("hello") == "hello"
        assert _json_safe(42) == 42
        assert _json_safe(3.14) == 3.14
        assert _json_safe(True) is True

    def test_datetime_converted(self):
        dt = datetime(2026, 2, 8, 23, 47, 57)
        result = _json_safe(dt)
        assert isinstance(result, str)
        assert result == "2026-02-08T23:47:57"
        json.dumps(result)  # must not raise

    def test_date_converted(self):
        d = date(2026, 2, 8)
        result = _json_safe(d)
        assert isinstance(result, str)
        assert result == "2026-02-08"

    def test_enum_converted(self):
        result = _json_safe(_TestEnum.A)
        assert result == "a"

    def test_nested_dict_with_datetimes(self):
        data = {
            "specialist_outputs": {
                "history_search": {
                    "relevant_records": [
                        {"date": datetime(2026, 1, 15, 10, 30), "summary": "test"},
                        {"date": datetime(2026, 2, 1, 14, 0), "summary": "other"},
                    ],
                    "timeline_context": "context",
                },
            },
        }
        result = _json_safe(data)
        # Must be valid JSON — this is the exact scenario that caused the crash
        serialized = json.dumps(result)
        parsed = json.loads(serialized)
        assert parsed["specialist_outputs"]["history_search"]["relevant_records"][0]["date"] == "2026-01-15T10:30:00"

    def test_list_with_mixed_types(self):
        data = [datetime(2026, 1, 1), "text", 42, {"nested": date(2025, 12, 31)}]
        result = _json_safe(data)
        serialized = json.dumps(result)
        parsed = json.loads(serialized)
        assert parsed[0] == "2026-01-01T00:00:00"
        assert parsed[3]["nested"] == "2025-12-31"

    def test_empty_structures(self):
        assert _json_safe({}) == {}
        assert _json_safe([]) == []

    def test_reproduces_original_crash_scenario(self):
        """Exact reproduction of the crash from the error log.

        The crash happened when specialist_outputs contained
        HistoryRecord objects with datetime fields, serialised via
        model_dump() (without mode='json'), then stored in a JSON column.
        """
        # Simulate what model_dump() without mode="json" returns
        specialist_outputs = {
            "history_search": {
                "tool": "history_search",
                "patient_id": "PT-E6FEC97C",
                "relevant_records": [
                    {
                        "date": datetime(2026, 2, 8, 23, 47, 57, 317039),
                        "record_type": "ai_report",
                        "summary": "AI Analysis: Vladislav presents with right knee pain",
                        "similarity_score": 0.3,
                        "clinical_relevance": "Prior analysis",
                    }
                ],
                "timeline_context": "...",
            },
        }

        result = _json_safe(specialist_outputs)
        # This exact call was failing before the fix
        json.dumps(result)
