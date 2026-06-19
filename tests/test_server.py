"""Server-build tests — read tools always present, write tools gated.

Skips cleanly if the ``mcp`` runtime isn't installed (e.g. a minimal CI lane
that only checks the transport/operations layers)."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp", reason="mcp runtime not installed")

from revolut_merchant_mcp.config import Config  # noqa: E402
from revolut_merchant_mcp.server import build_server  # noqa: E402

# Every tool registered across all domains, partitioned by mutation posture.
# Keep these in sync with the per-domain ``register`` functions: the read-only
# safety assertion below is only as strong as ``_WRITE_TOOLS`` is complete.
_READ_TOOLS = {
    # customers (incl. nested payment-methods)
    "list_customers", "get_customer",
    "list_payment_methods", "get_payment_method",
    # orders
    "list_orders", "get_order",
    # subscriptions
    "list_subscriptions", "get_subscription",
    "list_subscription_cycles", "get_subscription_cycle",
    # plans
    "list_plans", "get_plan",
    # webhooks
    "list_webhooks", "get_webhook",
}
_WRITE_TOOLS = {
    # customers (incl. nested payment-methods)
    "create_customer", "update_customer", "delete_customer",
    "update_payment_method", "delete_payment_method",
    # orders
    "create_order", "update_order", "capture_order", "cancel_order",
    "pay_order", "refund_order", "increment_authorisation",
    # subscriptions
    "create_subscription", "update_subscription", "cancel_subscription",
    "change_subscription_plan", "update_subscription_renewal_date",
    # plans
    "create_plan",
    # webhooks
    "create_webhook", "update_webhook", "delete_webhook",
    "rotate_webhook_signing_secret",
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


async def test_tool_sets_are_exhaustive():
    """Every registered tool is categorized — guards against a new tool slipping
    in uncategorized (which would silently weaken the read-only safety check)."""
    names = await _tool_names(build_server(_cfg(allow_writes=True)))
    uncategorized = names - _READ_TOOLS - _WRITE_TOOLS
    assert not uncategorized, f"uncategorized tools: {sorted(uncategorized)}"
    assert not (_READ_TOOLS & _WRITE_TOOLS), "a tool is in both read and write sets"
