"""Webhooks domain operations.

Pure, framework-free async wrappers over ``RevolutClient`` for the Merchant
Webhooks endpoints (``/webhooks``) plus the signing-secret rotation endpoint.

Each Webhook-v2 object is ``{ id, url, events[], signing_secret }``. A merchant
may register at most 10 webhook URLs; the 11th ``create_webhook`` returns 422.

``register`` attaches the MCP tools for this domain; read tools are always
registered, write tools only when ``allow_writes`` is true. Each MCP tool shares
its name with the matching pure op, so the tool body calls the pure function via
a private ``_``-prefixed alias to avoid the local-name shadow inside ``register``.
"""

from __future__ import annotations

from ..client import RevolutClient

__all__ = [
    "list_webhooks",
    "get_webhook",
    "create_webhook",
    "update_webhook",
    "delete_webhook",
    "rotate_webhook_signing_secret",
]


async def list_webhooks(client: RevolutClient) -> dict:
    """List the webhooks currently registered for the merchant."""
    return await client.get("/webhooks")


async def get_webhook(client: RevolutClient, *, webhook_id: str) -> dict:
    """Retrieve a single webhook by id, including its signing secret."""
    return await client.get(f"/webhooks/{webhook_id}")


async def create_webhook(
    client: RevolutClient,
    *,
    url: str,
    events: list[str] | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Register a new webhook URL and subscribe it to a set of event types.

    The response includes the generated ``signing_secret`` used to verify
    payload signatures. Max 10 webhooks per merchant (the 11th returns 422).
    WRITE.
    """
    body: dict = {"url": url}
    if events is not None:
        body["events"] = events
    return await client.post("/webhooks", json=body, idempotency_key=idempotency_key)


async def update_webhook(
    client: RevolutClient,
    *,
    webhook_id: str,
    url: str | None = None,
    events: list[str] | None = None,
) -> dict:
    """Update the URL and/or subscribed event list of an existing webhook.

    Both fields are optional. WRITE.
    """
    body: dict = {}
    if url is not None:
        body["url"] = url
    if events is not None:
        body["events"] = events
    return await client.patch(f"/webhooks/{webhook_id}", json=body)


async def delete_webhook(client: RevolutClient, *, webhook_id: str) -> dict:
    """Delete a webhook so events are no longer delivered to its URL.

    Returns ``{}`` on the 204 No Content response. WRITE.
    """
    return await client.delete(f"/webhooks/{webhook_id}")


async def rotate_webhook_signing_secret(
    client: RevolutClient,
    *,
    webhook_id: str,
    expiration_period: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Rotate the signing secret for a webhook, returning the new secret.

    ``expiration_period`` is an optional ISO 8601 duration string (e.g.
    ``"PT5H30M"``, max 7 days) for which the OLD secret stays valid; if omitted
    the old secret is invalidated immediately. WRITE.
    """
    body: dict = {}
    if expiration_period is not None:
        body["expiration_period"] = expiration_period
    return await client.post(
        f"/webhooks/{webhook_id}/rotate-signing-secret",
        json=body,
        idempotency_key=idempotency_key,
    )


# Private aliases so the same-named MCP tool functions in register() can call the
# pure ops without the local definitions shadowing them.
_list_webhooks = list_webhooks
_get_webhook = get_webhook
_create_webhook = create_webhook
_update_webhook = update_webhook
_delete_webhook = delete_webhook
_rotate_webhook_signing_secret = rotate_webhook_signing_secret


def register(mcp, client, allow_writes, safe) -> None:
    """Register the webhooks-domain MCP tools."""

    @mcp.tool()
    async def list_webhooks() -> dict:
        """List the webhooks currently registered for the merchant."""
        return await safe(_list_webhooks(client))

    @mcp.tool()
    async def get_webhook(webhook_id: str) -> dict:
        """Retrieve a single Merchant webhook by its id (incl. signing secret)."""
        return await safe(_get_webhook(client, webhook_id=webhook_id))

    if allow_writes:

        @mcp.tool()
        async def create_webhook(
            url: str,
            events: list[str] | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            """Register a new webhook URL. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _create_webhook(
                    client, url=url, events=events, idempotency_key=idempotency_key,
                ),
            )

        @mcp.tool()
        async def update_webhook(
            webhook_id: str,
            url: str | None = None,
            events: list[str] | None = None,
        ) -> dict:
            """Update a webhook's URL and/or events. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _update_webhook(client, webhook_id=webhook_id, url=url, events=events),
            )

        @mcp.tool()
        async def delete_webhook(webhook_id: str) -> dict:
            """Delete a webhook. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(_delete_webhook(client, webhook_id=webhook_id))

        @mcp.tool()
        async def rotate_webhook_signing_secret(
            webhook_id: str,
            expiration_period: str | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            """Rotate a webhook's signing secret. WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _rotate_webhook_signing_secret(
                    client,
                    webhook_id=webhook_id,
                    expiration_period=expiration_period,
                    idempotency_key=idempotency_key,
                ),
            )
