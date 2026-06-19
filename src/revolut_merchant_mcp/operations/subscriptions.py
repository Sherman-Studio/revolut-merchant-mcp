"""Subscriptions domain operations (incl. subscription billing cycles).

Pure, framework-free async wrappers over ``RevolutClient`` for the Merchant
Subscriptions endpoints (Merchant API ``2026-04-20``). ``register`` attaches the
MCP tools (read always, write gated). Tool functions share names with the pure
ops and call them via ``_``-prefixed private aliases to avoid the local-name
shadow inside ``register``.

Lifecycle reference: a subscription is created in ``pending`` state and (after the
customer sets up a payment method) becomes ``active``; from there it ends via
``cancel`` or naturally ``finished``. There is no pause/resume in the Merchant
API — the closest operations are :func:`update_subscription_renewal_date`
(reschedule the next payment) and :func:`cancel_subscription`.
"""

from __future__ import annotations

from ..client import RevolutClient

__all__ = [
    "list_subscriptions",
    "get_subscription",
    "list_subscription_cycles",
    "get_subscription_cycle",
    "create_subscription",
    "update_subscription",
    "cancel_subscription",
    "change_subscription_plan",
    "update_subscription_renewal_date",
]


async def list_subscriptions(
    client: RevolutClient,
    *,
    external_reference: str | None = None,
    customer_id: str | None = None,
) -> dict:
    """List subscriptions for the merchant account.

    Optionally filter by ``external_reference`` (the only filter declared in the
    ``2026-04-20`` spec). ``customer_id`` is accepted for caller convenience and
    forwarded as a query param when set. Response is a paginated
    ``{next_page_token, subscriptions[]}`` page.
    """
    params: dict = {}
    if external_reference:
        params["external_reference"] = external_reference
    if customer_id:
        params["customer_id"] = customer_id
    return await client.get("/subscriptions", params=params or None)


async def get_subscription(client: RevolutClient, *, subscription_id: str) -> dict:
    """Retrieve a single subscription by id, for its current state and details."""
    return await client.get(f"/subscriptions/{subscription_id}")


async def list_subscription_cycles(
    client: RevolutClient, *, subscription_id: str,
) -> dict:
    """List all billing cycles for a subscription.

    Response is a paginated ``{next_page_token, cycles[]}`` page.
    """
    return await client.get(f"/subscriptions/{subscription_id}/cycles")


async def get_subscription_cycle(
    client: RevolutClient, *, subscription_id: str, cycle_id: str,
) -> dict:
    """Retrieve a single billing cycle of a subscription by its id."""
    return await client.get(f"/subscriptions/{subscription_id}/cycles/{cycle_id}")


async def create_subscription(
    client: RevolutClient,
    *,
    plan_variation_id: str,
    customer_id: str,
    external_reference: str | None = None,
    setup_order_redirect_url: str | None = None,
    trial_duration: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Create a subscription against a plan variation for a customer. WRITE.

    The customer must already exist. The subscription is created in ``pending``
    state; when ``setup_order_redirect_url`` is supplied the response includes a
    ``setup_order_id`` and the customer is redirected to the Revolut Hosted
    Payment Page to set up a payment method, after which a webhook flips the
    subscription to ``active``.
    """
    body: dict = {
        "plan_variation_id": plan_variation_id,
        "customer_id": customer_id,
    }
    if external_reference is not None:
        body["external_reference"] = external_reference
    if setup_order_redirect_url is not None:
        body["setup_order_redirect_url"] = setup_order_redirect_url
    if trial_duration is not None:
        body["trial_duration"] = trial_duration
    return await client.post("/subscriptions", json=body, idempotency_key=idempotency_key)


async def update_subscription(
    client: RevolutClient, *, subscription_id: str, external_reference: str,
) -> dict:
    """Update a subscription's mutable details. WRITE.

    In the ``2026-04-20`` spec the only modifiable request-body field is
    ``external_reference``. Returns the updated subscription object.
    """
    return await client.patch(
        f"/subscriptions/{subscription_id}",
        json={"external_reference": external_reference},
    )


async def cancel_subscription(client: RevolutClient, *, subscription_id: str) -> dict:
    """Cancel a subscription. WRITE. Returns the subscription after cancel.

    Allowed in any state except ``cancelled`` or ``finished``; no further billing
    cycles are created. The cancel endpoint returns 204 No Content, so this reads
    the subscription back to surface its post-cancel state to the caller.
    """
    await client.post(f"/subscriptions/{subscription_id}/cancel", json={})
    return await client.get(f"/subscriptions/{subscription_id}")


async def change_subscription_plan(
    client: RevolutClient,
    *,
    subscription_id: str,
    plan_variation_id: str,
    scheduled: bool,
    plan_variation_phase_id: str | None = None,
    reason: str | None = None,
) -> dict:
    """Schedule a plan change (upgrade/downgrade/variation switch). WRITE.

    The change is applied at the end of the current billing cycle. ``scheduled``
    is required by the spec. The endpoint returns 204 No Content (``{}`` here).
    """
    body: dict = {
        "plan_variation_id": plan_variation_id,
        "scheduled": scheduled,
    }
    if plan_variation_phase_id is not None:
        body["plan_variation_phase_id"] = plan_variation_phase_id
    if reason is not None:
        body["reason"] = reason
    return await client.post(
        f"/subscriptions/{subscription_id}/change-plan", json=body,
    )


async def update_subscription_renewal_date(
    client: RevolutClient, *, subscription_id: str, renewal_date: str,
) -> dict:
    """Reschedule the upcoming payment/renewal date of the active cycle. WRITE.

    Command endpoint: the renewal date is derived from the active cycle's end
    date, not a direct field on the subscription resource. ``renewal_date`` is an
    ISO-8601 date/timestamp. The endpoint returns 204 No Content (``{}`` here).
    """
    return await client.post(
        f"/subscriptions/{subscription_id}/change-renewal-date",
        json={"renewal_date": renewal_date},
    )


# Private aliases so the same-named MCP tool functions in register() can call the
# pure ops without the local definitions shadowing them.
_list_subscriptions = list_subscriptions
_get_subscription = get_subscription
_list_subscription_cycles = list_subscription_cycles
_get_subscription_cycle = get_subscription_cycle
_create_subscription = create_subscription
_update_subscription = update_subscription
_cancel_subscription = cancel_subscription
_change_subscription_plan = change_subscription_plan
_update_subscription_renewal_date = update_subscription_renewal_date


def register(mcp, client, allow_writes, safe) -> None:
    """Register the subscriptions-domain MCP tools."""

    @mcp.tool()
    async def list_subscriptions(
        external_reference: str | None = None, customer_id: str | None = None,
    ) -> dict:
        """List subscriptions, optionally filtered by external_reference / customer id."""
        return await safe(
            _list_subscriptions(
                client,
                external_reference=external_reference,
                customer_id=customer_id,
            ),
        )

    @mcp.tool()
    async def get_subscription(subscription_id: str) -> dict:
        """Retrieve a single subscription by its id."""
        return await safe(_get_subscription(client, subscription_id=subscription_id))

    @mcp.tool()
    async def list_subscription_cycles(subscription_id: str) -> dict:
        """List all billing cycles for a subscription."""
        return await safe(
            _list_subscription_cycles(client, subscription_id=subscription_id),
        )

    @mcp.tool()
    async def get_subscription_cycle(subscription_id: str, cycle_id: str) -> dict:
        """Retrieve a single billing cycle of a subscription by its id."""
        return await safe(
            _get_subscription_cycle(
                client, subscription_id=subscription_id, cycle_id=cycle_id,
            ),
        )

    if allow_writes:

        @mcp.tool()
        async def create_subscription(
            plan_variation_id: str,
            customer_id: str,
            external_reference: str | None = None,
            setup_order_redirect_url: str | None = None,
            trial_duration: str | None = None,
        ) -> dict:
            """Create a subscription against a plan variation for a customer. WRITE."""
            return await safe(
                _create_subscription(
                    client,
                    plan_variation_id=plan_variation_id,
                    customer_id=customer_id,
                    external_reference=external_reference,
                    setup_order_redirect_url=setup_order_redirect_url,
                    trial_duration=trial_duration,
                ),
            )

        @mcp.tool()
        async def update_subscription(
            subscription_id: str, external_reference: str,
        ) -> dict:
            """Update a subscription's external_reference. WRITE."""
            return await safe(
                _update_subscription(
                    client,
                    subscription_id=subscription_id,
                    external_reference=external_reference,
                ),
            )

        @mcp.tool()
        async def cancel_subscription(subscription_id: str) -> dict:
            """Cancel a subscription and return its post-cancel state. WRITE."""
            return await safe(_cancel_subscription(client, subscription_id=subscription_id))

        @mcp.tool()
        async def change_subscription_plan(
            subscription_id: str,
            plan_variation_id: str,
            scheduled: bool,
            plan_variation_phase_id: str | None = None,
            reason: str | None = None,
        ) -> dict:
            """Schedule a plan change at the end of the current cycle. WRITE."""
            return await safe(
                _change_subscription_plan(
                    client,
                    subscription_id=subscription_id,
                    plan_variation_id=plan_variation_id,
                    scheduled=scheduled,
                    plan_variation_phase_id=plan_variation_phase_id,
                    reason=reason,
                ),
            )

        @mcp.tool()
        async def update_subscription_renewal_date(
            subscription_id: str, renewal_date: str,
        ) -> dict:
            """Reschedule the upcoming renewal date of the active cycle. WRITE."""
            return await safe(
                _update_subscription_renewal_date(
                    client,
                    subscription_id=subscription_id,
                    renewal_date=renewal_date,
                ),
            )
