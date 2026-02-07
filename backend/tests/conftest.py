"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest

# Set test environment variables BEFORE importing app code
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-not-real")
os.environ.setdefault("DEBUG", "true")


@pytest.fixture
def anyio_backend():
    return "asyncio"
