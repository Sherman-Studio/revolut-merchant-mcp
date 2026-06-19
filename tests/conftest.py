"""Shared test fixtures.

Tests exercise the transport client and the operations layer with ``respx``
mocking the Revolut sandbox host — no live keys, no network.
"""

from __future__ import annotations

import pytest

from revolut_merchant_mcp.client import SANDBOX_BASE, RevolutClient


@pytest.fixture
def base_url() -> str:
    return SANDBOX_BASE


@pytest.fixture
async def client() -> RevolutClient:
    # backoff_base=0 makes retry sleeps instant.
    c = RevolutClient(
        secret_key="sk_sandbox_test",
        api_version="2024-09-01",
        sandbox=True,
        backoff_base=0,
    )
    yield c
    await c.aclose()
