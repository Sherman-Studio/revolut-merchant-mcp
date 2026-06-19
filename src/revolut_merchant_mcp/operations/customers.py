"""Customers domain operations (incl. nested payment-methods).

Pure, framework-free async wrappers over ``RevolutClient`` for the Merchant
Customers endpoints. Payment methods live under ``/customers/{id}/payment-methods``
and are folded into this module since they share the customer-id path root.

``register`` attaches the MCP tools for this domain; read tools are always
registered, write tools only when ``allow_writes`` is true. Each MCP tool shares
its name with the matching pure op, so the tool body calls the pure function via
a private ``_``-prefixed alias to avoid the local-name shadow inside ``register``.
"""

from __future__ import annotations

from ..client import RevolutClient

__all__ = [
    "list_customers",
    "get_customer",
    "create_customer",
    "update_customer",
    "delete_customer",
    "list_payment_methods",
    "get_payment_method",
    "update_payment_method",
    "delete_payment_method",
]


async def list_customers(
    client: RevolutClient,
    *,
    email: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict:
    """List customers (paginated), optionally filtered by exact email.

    Use this to search for an existing customer before creating a duplicate.
    ``limit`` is the page size; ``offset`` is the zero-based page index.
    """
    params: dict = {}
    if email:
        params["email"] = email
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    return await client.get("/customers", params=params or None)


async def get_customer(client: RevolutClient, *, customer_id: str) -> dict:
    """Retrieve a single customer by id, including saved payment methods."""
    return await client.get(f"/customers/{customer_id}")


async def create_customer(
    client: RevolutClient,
    *,
    email: str,
    full_name: str | None = None,
    phone: str | None = None,
    date_of_birth: str | None = None,
) -> dict:
    """Create a customer. ``email`` is required; ``phone`` is E.164;
    ``date_of_birth`` is ISO-8601 (YYYY-MM-DD). Check ``list_customers`` first to
    avoid duplicates. WRITE."""
    body: dict = {"email": email}
    if full_name:
        body["full_name"] = full_name
    if phone:
        body["phone"] = phone
    if date_of_birth:
        body["date_of_birth"] = date_of_birth
    return await client.post("/customers", json=body)


async def update_customer(
    client: RevolutClient,
    *,
    customer_id: str,
    full_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    date_of_birth: str | None = None,
) -> dict:
    """Update a customer's attributes. Only provided fields are sent.
    ``phone`` is E.164; ``date_of_birth`` is ISO-8601 (YYYY-MM-DD). WRITE."""
    body: dict = {}
    if full_name is not None:
        body["full_name"] = full_name
    if email is not None:
        body["email"] = email
    if phone is not None:
        body["phone"] = phone
    if date_of_birth is not None:
        body["date_of_birth"] = date_of_birth
    return await client.patch(f"/customers/{customer_id}", json=body)


async def delete_customer(client: RevolutClient, *, customer_id: str) -> dict:
    """Delete a customer profile. Returns ``{}`` on success (no content). WRITE."""
    return await client.delete(f"/customers/{customer_id}")


async def list_payment_methods(
    client: RevolutClient,
    *,
    customer_id: str,
    only_merchant: bool | None = None,
) -> dict:
    """List a customer's saved payment methods.

    Set ``only_merchant=True`` to return only methods saved for
    merchant-initiated transactions (``saved_for == "MERCHANT"``).
    """
    params = {"only_merchant": only_merchant} if only_merchant is not None else None
    return await client.get(
        f"/customers/{customer_id}/payment-methods", params=params,
    )


async def get_payment_method(
    client: RevolutClient, *, customer_id: str, payment_method_id: str,
) -> dict:
    """Retrieve a single saved payment method for a customer."""
    return await client.get(
        f"/customers/{customer_id}/payment-methods/{payment_method_id}",
    )


async def update_payment_method(
    client: RevolutClient,
    *,
    customer_id: str,
    payment_method_id: str,
    saved_for: str,
) -> dict:
    """Update a saved payment method. ``saved_for`` is one of ``CUSTOMER`` or
    ``MERCHANT``; switching ``MERCHANT`` -> ``CUSTOMER`` permanently disables the
    method for merchant-initiated transactions. WRITE."""
    return await client.patch(
        f"/customers/{customer_id}/payment-methods/{payment_method_id}",
        json={"saved_for": saved_for},
    )


async def delete_payment_method(
    client: RevolutClient, *, customer_id: str, payment_method_id: str,
) -> dict:
    """Delete a saved payment method. Returns ``{}`` on success (no content). WRITE."""
    return await client.delete(
        f"/customers/{customer_id}/payment-methods/{payment_method_id}",
    )


# Private aliases so the same-named MCP tool functions in register() can call the
# pure ops without the local definitions shadowing them.
_list_customers = list_customers
_get_customer = get_customer
_create_customer = create_customer
_update_customer = update_customer
_delete_customer = delete_customer
_list_payment_methods = list_payment_methods
_get_payment_method = get_payment_method
_update_payment_method = update_payment_method
_delete_payment_method = delete_payment_method


def register(mcp, client, allow_writes, safe) -> None:
    """Register the customers-domain MCP tools."""

    @mcp.tool()
    async def list_customers(
        email: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict:
        """List Merchant customers (paginated), optionally filtered by exact email."""
        return await safe(
            _list_customers(client, email=email, limit=limit, offset=offset),
        )

    @mcp.tool()
    async def get_customer(customer_id: str) -> dict:
        """Retrieve a single Merchant customer by its id, with saved payment methods."""
        return await safe(_get_customer(client, customer_id=customer_id))

    @mcp.tool()
    async def list_payment_methods(
        customer_id: str, only_merchant: bool | None = None,
    ) -> dict:
        """List a Merchant customer's saved payment methods."""
        return await safe(
            _list_payment_methods(
                client, customer_id=customer_id, only_merchant=only_merchant,
            ),
        )

    @mcp.tool()
    async def get_payment_method(customer_id: str, payment_method_id: str) -> dict:
        """Retrieve a single saved payment method for a Merchant customer."""
        return await safe(
            _get_payment_method(
                client, customer_id=customer_id, payment_method_id=payment_method_id,
            ),
        )

    if allow_writes:

        @mcp.tool()
        async def create_customer(
            email: str,
            full_name: str | None = None,
            phone: str | None = None,
            date_of_birth: str | None = None,
        ) -> dict:
            """Create a Merchant customer. ``email`` required; ``phone`` E.164;
            ``date_of_birth`` YYYY-MM-DD. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _create_customer(
                    client,
                    email=email,
                    full_name=full_name,
                    phone=phone,
                    date_of_birth=date_of_birth,
                ),
            )

        @mcp.tool()
        async def update_customer(
            customer_id: str,
            full_name: str | None = None,
            email: str | None = None,
            phone: str | None = None,
            date_of_birth: str | None = None,
        ) -> dict:
            """Update a Merchant customer's attributes (only provided fields). WRITE."""
            return await safe(
                _update_customer(
                    client,
                    customer_id=customer_id,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    date_of_birth=date_of_birth,
                ),
            )

        @mcp.tool()
        async def delete_customer(customer_id: str) -> dict:
            """Delete a Merchant customer profile. WRITE."""
            return await safe(_delete_customer(client, customer_id=customer_id))

        @mcp.tool()
        async def update_payment_method(
            customer_id: str, payment_method_id: str, saved_for: str,
        ) -> dict:
            """Update a saved payment method's ``saved_for`` (CUSTOMER/MERCHANT). WRITE."""
            return await safe(
                _update_payment_method(
                    client,
                    customer_id=customer_id,
                    payment_method_id=payment_method_id,
                    saved_for=saved_for,
                ),
            )

        @mcp.tool()
        async def delete_payment_method(
            customer_id: str, payment_method_id: str,
        ) -> dict:
            """Delete a Merchant customer's saved payment method. WRITE."""
            return await safe(
                _delete_payment_method(
                    client,
                    customer_id=customer_id,
                    payment_method_id=payment_method_id,
                ),
            )
