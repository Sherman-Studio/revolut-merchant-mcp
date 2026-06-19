"""Orders domain operations.

Pure, framework-free async wrappers over ``RevolutClient`` for the Merchant
Orders endpoints (Merchant API ``2024-05-01``). The Order lifecycle is
``pending -> authorised -> processing -> completed`` plus ``cancelled`` and
refund-type orders; ``capture_mode`` is ``automatic|manual`` and
``authorisation_type`` is ``final|pre_authorisation``.

All monetary amounts (``amount``) are in the **minor unit** of the currency
(e.g. cents/pence): ``799`` == GBP 7.99.

``register`` attaches the MCP tools (read always, write gated). Tool functions
share names with the pure ops and call them via ``_``-prefixed private aliases
to avoid the local-name shadow inside ``register``.
"""

from __future__ import annotations

from ..client import RevolutClient

__all__ = [
    "list_orders",
    "get_order",
    "create_order",
    "update_order",
    "increment_authorisation",
    "capture_order",
    "cancel_order",
    "refund_order",
    "pay_order",
]


async def list_orders(
    client: RevolutClient,
    *,
    limit: int | None = None,
    from_: str | None = None,
    to: str | None = None,
    customer_id: str | None = None,
    merchant_order_data_reference: str | None = None,
    state: str | None = None,
    location_id: str | None = None,
) -> dict:
    """List orders (wrapped ``{"orders": [...]}``), newest first.

    Optional filters: ``limit``, ``from_``/``to`` (ISO timestamps; ``from_``
    maps to the ``from`` query param), ``customer_id``, ``state``,
    ``location_id`` and ``merchant_order_data_reference``.
    """
    params: dict = {}
    if limit is not None:
        params["limit"] = limit
    if from_:
        params["from"] = from_
    if to:
        params["to"] = to
    if customer_id:
        params["customer_id"] = customer_id
    if merchant_order_data_reference:
        params["merchant_order_data_reference"] = merchant_order_data_reference
    if state:
        params["state"] = state
    if location_id:
        params["location_id"] = location_id
    return await client.get("/orders", params=params or None)


async def get_order(client: RevolutClient, *, order_id: str) -> dict:
    """Retrieve the full details of a single order by id."""
    return await client.get(f"/orders/{order_id}")


async def create_order(
    client: RevolutClient,
    *,
    amount: int,
    currency: str,
    settlement_currency: str | None = None,
    description: str | None = None,
    customer: dict | None = None,
    customer_id: str | None = None,
    enforce_challenge: str | None = None,
    line_items: list | None = None,
    shipping: dict | None = None,
    capture_mode: str | None = None,
    authorisation_type: str | None = None,
    cancel_authorised_after: str | None = None,
    expire_pending_after: str | None = None,
    location_id: str | None = None,
    metadata: dict | None = None,
    industry_data: dict | None = None,
    merchant_order_data: dict | None = None,
    upcoming_payment_data: dict | None = None,
    redirect_url: str | None = None,
    statement_descriptor_suffix: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Create an Order; returns the Order with a ``token``/``checkout_url`` used
    to accept payment via the Revolut checkout widget or hosted page.

    ``amount`` is in the minor unit (cents/pence); ``currency`` is upper-cased.
    ``customer_id`` is a convenience that maps into the ``customer`` object.
    WRITE.
    """
    body: dict = {"amount": amount, "currency": currency.upper()}
    if settlement_currency:
        body["settlement_currency"] = settlement_currency.upper()
    if description:
        body["description"] = description
    if customer is not None:
        body["customer"] = customer
    if customer_id:
        body.setdefault("customer", {})["id"] = customer_id
    if enforce_challenge:
        body["enforce_challenge"] = enforce_challenge
    if line_items is not None:
        body["line_items"] = line_items
    if shipping is not None:
        body["shipping"] = shipping
    if capture_mode:
        body["capture_mode"] = capture_mode
    if authorisation_type:
        body["authorisation_type"] = authorisation_type
    if cancel_authorised_after:
        body["cancel_authorised_after"] = cancel_authorised_after
    if expire_pending_after:
        body["expire_pending_after"] = expire_pending_after
    if location_id:
        body["location_id"] = location_id
    if metadata is not None:
        body["metadata"] = metadata
    if industry_data is not None:
        body["industry_data"] = industry_data
    if merchant_order_data is not None:
        body["merchant_order_data"] = merchant_order_data
    if upcoming_payment_data is not None:
        body["upcoming_payment_data"] = upcoming_payment_data
    if redirect_url:
        body["redirect_url"] = redirect_url
    if statement_descriptor_suffix:
        body["statement_descriptor_suffix"] = statement_descriptor_suffix
    return await client.post("/orders", json=body, idempotency_key=idempotency_key)


async def update_order(
    client: RevolutClient,
    *,
    order_id: str,
    amount: int | None = None,
    currency: str | None = None,
    settlement_currency: str | None = None,
    description: str | None = None,
    customer: dict | None = None,
    enforce_challenge: str | None = None,
    line_items: list | None = None,
    shipping: dict | None = None,
    capture_mode: str | None = None,
    cancel_authorised_after: str | None = None,
    expire_pending_after: str | None = None,
    metadata: dict | None = None,
    industry_data: dict | None = None,
    merchant_order_data: dict | None = None,
    upcoming_payment_data: dict | None = None,
    redirect_url: str | None = None,
    statement_descriptor_suffix: str | None = None,
) -> dict:
    """Update an order. Which fields are modifiable depends on order state
    (``pending`` = all listed; ``authorised``/``completed`` = a restricted
    subset; ``processing`` = none). ``amount`` is in the minor unit. WRITE.
    """
    body: dict = {}
    if amount is not None:
        body["amount"] = amount
    if currency:
        body["currency"] = currency.upper()
    if settlement_currency:
        body["settlement_currency"] = settlement_currency.upper()
    if description is not None:
        body["description"] = description
    if customer is not None:
        body["customer"] = customer
    if enforce_challenge:
        body["enforce_challenge"] = enforce_challenge
    if line_items is not None:
        body["line_items"] = line_items
    if shipping is not None:
        body["shipping"] = shipping
    if capture_mode:
        body["capture_mode"] = capture_mode
    if cancel_authorised_after:
        body["cancel_authorised_after"] = cancel_authorised_after
    if expire_pending_after:
        body["expire_pending_after"] = expire_pending_after
    if metadata is not None:
        body["metadata"] = metadata
    if industry_data is not None:
        body["industry_data"] = industry_data
    if merchant_order_data is not None:
        body["merchant_order_data"] = merchant_order_data
    if upcoming_payment_data is not None:
        body["upcoming_payment_data"] = upcoming_payment_data
    if redirect_url:
        body["redirect_url"] = redirect_url
    if statement_descriptor_suffix:
        body["statement_descriptor_suffix"] = statement_descriptor_suffix
    return await client.patch(f"/orders/{order_id}", json=body)


async def increment_authorisation(
    client: RevolutClient,
    *,
    order_id: str,
    amount: int,
    reference: str | None = None,
    line_items: list | None = None,
) -> dict:
    """Increase the authorised amount on a pre-authorised order
    (``authorisation_type=pre_authorisation``, ``capture_mode=manual``, order in
    ``authorised`` state). Card only; max 10 increments; total <= 5x the initial
    amount. ``amount`` is the increment in the minor unit. WRITE.
    """
    body: dict = {"amount": amount}
    if reference:
        body["reference"] = reference
    if line_items is not None:
        body["line_items"] = line_items
    return await client.post(
        f"/orders/{order_id}/increment-authorisation", json=body,
    )


async def capture_order(
    client: RevolutClient,
    *,
    order_id: str,
    amount: int | None = None,
    line_items: list | None = None,
) -> dict:
    """Capture funds on an uncaptured (authorised) order, moving it to
    ``processing``. Supports partial capture (the uncaptured portion is voided)
    via ``amount`` (minor unit) and an optional ``line_items`` override.
    Idempotent: re-sending the same amount behaves like a retrieve; a different
    amount errors. WRITE.
    """
    body: dict = {}
    if amount is not None:
        body["amount"] = amount
    if line_items is not None:
        body["line_items"] = line_items
    return await client.post(f"/orders/{order_id}/capture", json=body or None)


async def cancel_order(client: RevolutClient, *, order_id: str) -> dict:
    """Cancel an uncaptured order. Only orders in ``pending`` or ``authorised``
    state can be cancelled. WRITE.
    """
    return await client.post(f"/orders/{order_id}/cancel")


async def refund_order(
    client: RevolutClient,
    *,
    order_id: str,
    amount: int,
    currency: str,
    description: str | None = None,
    merchant_order_data: dict | None = None,
    metadata: dict | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Issue a full or partial refund for a completed order; creates a NEW order
    with ``type=refund`` linked via ``related_order_id``. Multiple partial
    refunds are allowed up to the original amount. ``amount`` (minor unit) and
    ``currency`` are required; ``currency`` is upper-cased. WRITE.
    """
    body: dict = {"amount": amount, "currency": currency.upper()}
    if description:
        body["description"] = description
    if merchant_order_data is not None:
        body["merchant_order_data"] = merchant_order_data
    if metadata is not None:
        body["metadata"] = metadata
    return await client.post(
        f"/orders/{order_id}/refund", json=body, idempotency_key=idempotency_key,
    )


async def pay_order(
    client: RevolutClient,
    *,
    order_id: str,
    saved_payment_method: dict,
) -> dict:
    """Initiate a payment for the full order amount using a customer's saved
    payment method (merchant- or customer-initiated). Replaces the deprecated
    ``/orders/{order_id}/confirm`` endpoint. Returns a Payment object.
    ``saved_payment_method`` (with ``type``, ``id``, ``initiator``,
    ``environment``) is required. WRITE.
    """
    body = {"saved_payment_method": saved_payment_method}
    return await client.post(f"/orders/{order_id}/payments", json=body)


_list_orders = list_orders
_get_order = get_order
_create_order = create_order
_update_order = update_order
_increment_authorisation = increment_authorisation
_capture_order = capture_order
_cancel_order = cancel_order
_refund_order = refund_order
_pay_order = pay_order


def register(mcp, client, allow_writes, safe) -> None:
    """Register the orders-domain MCP tools."""

    @mcp.tool()
    async def list_orders(
        limit: int | None = None,
        from_: str | None = None,
        to: str | None = None,
        customer_id: str | None = None,
        merchant_order_data_reference: str | None = None,
        state: str | None = None,
        location_id: str | None = None,
    ) -> dict:
        """List Merchant orders (newest first), with optional filters."""
        return await safe(
            _list_orders(
                client,
                limit=limit,
                from_=from_,
                to=to,
                customer_id=customer_id,
                merchant_order_data_reference=merchant_order_data_reference,
                state=state,
                location_id=location_id,
            ),
        )

    @mcp.tool()
    async def get_order(order_id: str) -> dict:
        """Retrieve the full details of a single Merchant order by its id."""
        return await safe(_get_order(client, order_id=order_id))

    if allow_writes:

        @mcp.tool()
        async def create_order(
            amount: int,
            currency: str,
            settlement_currency: str | None = None,
            description: str | None = None,
            customer: dict | None = None,
            customer_id: str | None = None,
            enforce_challenge: str | None = None,
            line_items: list | None = None,
            shipping: dict | None = None,
            capture_mode: str | None = None,
            authorisation_type: str | None = None,
            cancel_authorised_after: str | None = None,
            expire_pending_after: str | None = None,
            location_id: str | None = None,
            metadata: dict | None = None,
            industry_data: dict | None = None,
            merchant_order_data: dict | None = None,
            upcoming_payment_data: dict | None = None,
            redirect_url: str | None = None,
            statement_descriptor_suffix: str | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            """Create an order; returns a token/checkout_url. ``amount`` is in
            the minor unit (cents/pence). WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _create_order(
                    client,
                    amount=amount,
                    currency=currency,
                    settlement_currency=settlement_currency,
                    description=description,
                    customer=customer,
                    customer_id=customer_id,
                    enforce_challenge=enforce_challenge,
                    line_items=line_items,
                    shipping=shipping,
                    capture_mode=capture_mode,
                    authorisation_type=authorisation_type,
                    cancel_authorised_after=cancel_authorised_after,
                    expire_pending_after=expire_pending_after,
                    location_id=location_id,
                    metadata=metadata,
                    industry_data=industry_data,
                    merchant_order_data=merchant_order_data,
                    upcoming_payment_data=upcoming_payment_data,
                    redirect_url=redirect_url,
                    statement_descriptor_suffix=statement_descriptor_suffix,
                    idempotency_key=idempotency_key,
                ),
            )

        @mcp.tool()
        async def update_order(
            order_id: str,
            amount: int | None = None,
            currency: str | None = None,
            settlement_currency: str | None = None,
            description: str | None = None,
            customer: dict | None = None,
            enforce_challenge: str | None = None,
            line_items: list | None = None,
            shipping: dict | None = None,
            capture_mode: str | None = None,
            cancel_authorised_after: str | None = None,
            expire_pending_after: str | None = None,
            metadata: dict | None = None,
            industry_data: dict | None = None,
            merchant_order_data: dict | None = None,
            upcoming_payment_data: dict | None = None,
            redirect_url: str | None = None,
            statement_descriptor_suffix: str | None = None,
        ) -> dict:
            """Update an order's details (modifiable fields depend on state).
            ``amount`` is in the minor unit. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _update_order(
                    client,
                    order_id=order_id,
                    amount=amount,
                    currency=currency,
                    settlement_currency=settlement_currency,
                    description=description,
                    customer=customer,
                    enforce_challenge=enforce_challenge,
                    line_items=line_items,
                    shipping=shipping,
                    capture_mode=capture_mode,
                    cancel_authorised_after=cancel_authorised_after,
                    expire_pending_after=expire_pending_after,
                    metadata=metadata,
                    industry_data=industry_data,
                    merchant_order_data=merchant_order_data,
                    upcoming_payment_data=upcoming_payment_data,
                    redirect_url=redirect_url,
                    statement_descriptor_suffix=statement_descriptor_suffix,
                ),
            )

        @mcp.tool()
        async def increment_authorisation(
            order_id: str,
            amount: int,
            reference: str | None = None,
            line_items: list | None = None,
        ) -> dict:
            """Increase the authorised amount on a pre-authorised order. ``amount``
            is the increment in the minor unit. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _increment_authorisation(
                    client,
                    order_id=order_id,
                    amount=amount,
                    reference=reference,
                    line_items=line_items,
                ),
            )

        @mcp.tool()
        async def capture_order(
            order_id: str,
            amount: int | None = None,
            line_items: list | None = None,
        ) -> dict:
            """Capture funds on an authorised order (supports partial capture).
            ``amount`` is in the minor unit. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _capture_order(
                    client, order_id=order_id, amount=amount, line_items=line_items,
                ),
            )

        @mcp.tool()
        async def cancel_order(order_id: str) -> dict:
            """Cancel an uncaptured order (pending or authorised only).
            WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(_cancel_order(client, order_id=order_id))

        @mcp.tool()
        async def refund_order(
            order_id: str,
            amount: int,
            currency: str,
            description: str | None = None,
            merchant_order_data: dict | None = None,
            metadata: dict | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            """Refund a completed order (full or partial); creates a new
            type=refund order. ``amount`` is in the minor unit. WRITE — requires
            REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _refund_order(
                    client,
                    order_id=order_id,
                    amount=amount,
                    currency=currency,
                    description=description,
                    merchant_order_data=merchant_order_data,
                    metadata=metadata,
                    idempotency_key=idempotency_key,
                ),
            )

        @mcp.tool()
        async def pay_order(order_id: str, saved_payment_method: dict) -> dict:
            """Pay for an order using a customer's saved payment method (replaces
            the deprecated confirm endpoint). WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _pay_order(
                    client, order_id=order_id, saved_payment_method=saved_payment_method,
                ),
            )
