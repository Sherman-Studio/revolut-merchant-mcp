"""Server-build tests — read tools always present, write tools gated.

Skips cleanly if the ``mcp`` runtime isn't installed (e.g. a minimal CI lane
that only checks the transport/operations layers)."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp", reason="mcp runtime not installed")

from revolut_merchant_mcp.config import Config  # noqa: E402
from revolut_merchant_mcp.server import build_server  # noqa: E402

_READ_TOOLS = {
    "list_customers", "get_customer", "list_orders", "get_order",
    "list_subscriptions", "get_subscription", "list_plans", "get_plan",
}
_WRITE_TOOLS = {
    "create_customer", "create_order", "create_subscription", "cancel_subscription",
}


def _cfg(allow_writes: bool) -> Config:
    return Config(
        secret_key="sk_sandbox_x",
        api_version="2024-09-01",
        sandbox=True,
        allow_writes=allow_writes,
    )


async def _tool_names(server) -> set[str]:
    return {t.name for t in await server.list_tools()}


async def test_read_only_by_default():
    names = await _tool_names(build_server(_cfg(allow_writes=False)))
    assert _READ_TOOLS <= names
    assert not (_WRITE_TOOLS & names), "write tools must be absent when writes disabled"


async def test_writes_registered_when_enabled():
    names = await _tool_names(build_server(_cfg(allow_writes=True)))
    assert _READ_TOOLS <= names
    assert _WRITE_TOOLS <= names
