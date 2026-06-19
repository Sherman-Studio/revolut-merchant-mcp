"""FastMCP server exposing the Revolut Merchant API as MCP tools.

Read tools are always registered. Write tools (create/cancel) are only
registered when ``REVOLUT_MCP_ALLOW_WRITES=true`` — so the default posture is
read-only, which is the safe default for letting an autonomous model poke a
payments API.

Run it::

    REVOLUT_MERCHANT_SECRET_KEY=sk_sandbox_... revolut-merchant-mcp

or point your MCP client (Claude Desktop, Cursor) at ``revolut-merchant-mcp``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import operations as ops
from .client import RevolutAPIError, RevolutClient
from .config import Config


def build_server(config: Config) -> FastMCP:
    """Construct a FastMCP server bound to a Revolut client built from ``config``.

    Factored out from ``main()`` so tests can build a server against a fake/mock
    client without going through the environment.
    """
    mcp = FastMCP("revolut-merchant")
    client = RevolutClient(
        secret_key=config.secret_key,
        api_version=config.api_version,
        sandbox=config.sandbox,
    )

    async def _safe(coro) -> dict[str, Any]:
        """Run an operation, mapping Revolut errors to a structured tool result
        the model can reason about instead of an opaque exception."""
        try:
            return await coro
        except RevolutAPIError as e:
            return {
                "error": str(e),
                "status_code": e.status_code,
                "code": e.code,
            }

    # ── Read tools (always available) ───────────────────────────────

    @mcp.tool()
    async def list_customers(email: str | None = None) -> dict:
        """List Merchant customers, optionally filtered by exact email address."""
        return await _safe(ops.list_customers(client, email=email))

    @mcp.tool()
    async def get_customer(customer_id: str) -> dict:
        """Retrieve a single Merchant customer by its id."""
        return await _safe(ops.get_customer(client, customer_id=customer_id))

    @mcp.tool()
    async def list_orders(limit: int | None = None) -> dict:
        """List recent Merchant orders."""
        return await _safe(ops.list_orders(client, limit=limit))

    @mcp.tool()
    async def get_order(order_id: str) -> dict:
        """Retrieve a single Merchant order by its id."""
        return await _safe(ops.get_order(client, order_id=order_id))

    @mcp.tool()
    async def list_subscriptions(customer_id: str | None = None) -> dict:
        """List subscriptions, optionally filtered by customer id."""
        return await _safe(ops.list_subscriptions(client, customer_id=customer_id))

    @mcp.tool()
    async def get_subscription(subscription_id: str) -> dict:
        """Retrieve a single subscription by its id."""
        return await _safe(ops.get_subscription(client, subscription_id=subscription_id))

    @mcp.tool()
    async def list_plans() -> dict:
        """List Merchant subscription plans."""
        return await _safe(ops.list_plans(client))

    @mcp.tool()
    async def get_plan(plan_id: str) -> dict:
        """Retrieve a single plan, including its variations, by id."""
        return await _safe(ops.get_plan(client, plan_id=plan_id))

    # ── Write tools (gated) ─────────────────────────────────────────

    if config.allow_writes:

        @mcp.tool()
        async def create_customer(email: str, full_name: str | None = None) -> dict:
            """Create a Merchant customer. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await _safe(ops.create_customer(client, email=email, full_name=full_name))

        @mcp.tool()
        async def create_order(
            amount: int,
            currency: str,
            customer_id: str | None = None,
            description: str | None = None,
        ) -> dict:
            """Create an order. ``amount`` is in the minor unit (cents/pence). WRITE."""
            return await _safe(
                ops.create_order(
                    client,
                    amount=amount,
                    currency=currency,
                    customer_id=customer_id,
                    description=description,
                ),
            )

        @mcp.tool()
        async def create_subscription(plan_variation_id: str, customer_id: str) -> dict:
            """Create a subscription against a plan variation for a customer. WRITE."""
            return await _safe(
                ops.create_subscription(
                    client, plan_variation_id=plan_variation_id, customer_id=customer_id,
                ),
            )

        @mcp.tool()
        async def cancel_subscription(subscription_id: str) -> dict:
            """Cancel a subscription and return its post-cancel state. WRITE."""
            return await _safe(ops.cancel_subscription(client, subscription_id=subscription_id))

    return mcp


def main() -> None:
    """Console-script entry point: build from env and serve over stdio."""
    config = Config.from_env()
    server = build_server(config)
    server.run()


if __name__ == "__main__":
    main()
