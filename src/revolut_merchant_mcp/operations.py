"""Revolut Merchant API operations.

Each function is a thin, typed wrapper over ``RevolutClient`` for one Merchant
API endpoint. They are deliberately framework-free (no MCP imports) so they can
be unit-tested with ``respx`` and reused outside the MCP server. ``server.py``
registers a subset of these as MCP tools.

Endpoint paths mirror the live Merchant API (the client base URL already includes
``/api``); versioning is carried by the ``Revolut-Api-Version`` header, not the
path.
"""

from __future__ import annotations

from .client import RevolutClient

# ── Customers ───────────────────────────────────────────────────────


async def list_customers(client: RevolutClient, *, email: str | None = None) -> dict:
    """List customers, optionally filtered by exact email."""
    params = {"email": email} if email else None
    return await client.get("/customers", params=params)


async def get_customer(client: RevolutClient, *, customer_id: str) -> dict:
    """Retrieve a single customer by id."""
    return await client.get(f"/customers/{customer_id}")


async def create_customer(
    client: RevolutClient, *, email: str, full_name: str | None = None,
) -> dict:
    """Create a customer. WRITE."""
    body: dict = {"email": email}
    if full_name:
        body["full_name"] = full_name
    return await client.post("/customers", json=body)


# ── Orders ──────────────────────────────────────────────────────────


async def list_orders(client: RevolutClient, *, limit: int | None = None) -> dict:
    """List recent orders."""
    params = {"limit": limit} if limit else None
    return await client.get("/orders", params=params)


async def get_order(client: RevolutClient, *, order_id: str) -> dict:
    """Retrieve a single order by id."""
    return await client.get(f"/orders/{order_id}")


async def create_order(
    client: RevolutClient,
    *,
    amount: int,
    currency: str,
    customer_id: str | None = None,
    description: str | None = None,
) -> dict:
    """Create an order. ``amount`` is in the minor unit (e.g. cents/pence). WRITE."""
    body: dict = {"amount": amount, "currency": currency.upper()}
    if customer_id:
        body["customer_id"] = customer_id
    if description:
        body["description"] = description
    return await client.post("/orders", json=body)


# ── Subscriptions ───────────────────────────────────────────────────


async def list_subscriptions(
    client: RevolutClient, *, customer_id: str | None = None,
) -> dict:
    """List subscriptions, optionally filtered by customer."""
    params = {"customer_id": customer_id} if customer_id else None
    return await client.get("/subscriptions", params=params)


async def get_subscription(client: RevolutClient, *, subscription_id: str) -> dict:
    """Retrieve a single subscription by id."""
    return await client.get(f"/subscriptions/{subscription_id}")


async def create_subscription(
    client: RevolutClient, *, plan_variation_id: str, customer_id: str,
) -> dict:
    """Create a subscription against a plan variation for a customer. WRITE.

    Returns the subscription in ``state: "pending"`` with a ``setup_order_token``;
    the customer completes that setup order in the checkout widget and a webhook
    then flips the subscription to ``active``.
    """
    return await client.post(
        "/subscriptions",
        json={"plan_variation_id": plan_variation_id, "customer_id": customer_id},
    )


async def cancel_subscription(client: RevolutClient, *, subscription_id: str) -> dict:
    """Cancel a subscription. WRITE. Returns the subscription after cancel."""
    await client.post(f"/subscriptions/{subscription_id}/cancel", json={})
    return await client.get(f"/subscriptions/{subscription_id}")


# ── Plans ───────────────────────────────────────────────────────────


async def list_plans(client: RevolutClient) -> dict:
    """List merchant subscription plans."""
    return await client.get("/plans")


async def get_plan(client: RevolutClient, *, plan_id: str) -> dict:
    """Retrieve a single plan (including its variations) by id."""
    return await client.get(f"/plans/{plan_id}")
