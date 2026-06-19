"""Webhooks operations tests: each op hits the right path/verb, sends the right
body, and returns the parsed response. respx mocks the sandbox host."""

from __future__ import annotations

import json as _json

import httpx
import pytest
import respx

from revolut_merchant_mcp import operations as ops
from revolut_merchant_mcp.client import RevolutAPIError

_WEBHOOK = {
    "id": "wh_1",
    "url": "https://example.com/hook",
    "events": ["ORDER_COMPLETED"],
    "signing_secret": "wsk_abc",
}


@respx.mock
async def test_list_webhooks(client, base_url):
    route = respx.get(f"{base_url}/webhooks").mock(
        return_value=httpx.Response(200, json={"webhooks": [_WEBHOOK]}),
    )
    out = await ops.list_webhooks(client)
    assert out == {"webhooks": [_WEBHOOK]}
    assert route.calls.last.request.method == "GET"


@respx.mock
async def test_get_webhook(client, base_url):
    route = respx.get(f"{base_url}/webhooks/wh_1").mock(
        return_value=httpx.Response(200, json=_WEBHOOK),
    )
    out = await ops.get_webhook(client, webhook_id="wh_1")
    assert out["id"] == "wh_1"
    assert out["signing_secret"] == "wsk_abc"
    assert route.calls.last.request.method == "GET"


@respx.mock
async def test_create_webhook_posts_url_and_events(client, base_url):
    route = respx.post(f"{base_url}/webhooks").mock(
        return_value=httpx.Response(200, json=_WEBHOOK),
    )
    out = await ops.create_webhook(
        client,
        url="https://example.com/hook",
        events=["ORDER_COMPLETED", "ORDER_FAILED"],
    )
    assert out["signing_secret"] == "wsk_abc"
    req = route.calls.last.request
    assert req.method == "POST"
    sent = _json.loads(req.content)
    assert sent == {
        "url": "https://example.com/hook",
        "events": ["ORDER_COMPLETED", "ORDER_FAILED"],
    }


@respx.mock
async def test_create_webhook_omits_events_when_none(client, base_url):
    route = respx.post(f"{base_url}/webhooks").mock(
        return_value=httpx.Response(200, json=_WEBHOOK),
    )
    await ops.create_webhook(client, url="https://example.com/hook")
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"url": "https://example.com/hook"}


@respx.mock
async def test_create_webhook_sends_idempotency_key(client, base_url):
    route = respx.post(f"{base_url}/webhooks").mock(
        return_value=httpx.Response(200, json=_WEBHOOK),
    )
    await ops.create_webhook(
        client, url="https://example.com/hook", idempotency_key="idem-1",
    )
    assert route.calls.last.request.headers["Idempotency-Key"] == "idem-1"


@respx.mock
async def test_create_webhook_limit_exceeded_raises(client, base_url):
    respx.post(f"{base_url}/webhooks").mock(
        return_value=httpx.Response(
            422,
            json={"code": "TooManyWebhooks", "message": "max 10 webhooks"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.create_webhook(client, url="https://example.com/hook")
    assert exc.value.status_code == 422


@respx.mock
async def test_update_webhook_patches_both_fields(client, base_url):
    route = respx.patch(f"{base_url}/webhooks/wh_1").mock(
        return_value=httpx.Response(200, json=_WEBHOOK),
    )
    await ops.update_webhook(
        client,
        webhook_id="wh_1",
        url="https://new.example.com/hook",
        events=["ORDER_CANCELLED"],
    )
    req = route.calls.last.request
    assert req.method == "PATCH"
    sent = _json.loads(req.content)
    assert sent == {
        "url": "https://new.example.com/hook",
        "events": ["ORDER_CANCELLED"],
    }


@respx.mock
async def test_update_webhook_omits_unset_fields(client, base_url):
    route = respx.patch(f"{base_url}/webhooks/wh_1").mock(
        return_value=httpx.Response(200, json=_WEBHOOK),
    )
    await ops.update_webhook(client, webhook_id="wh_1", events=["ORDER_COMPLETED"])
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"events": ["ORDER_COMPLETED"]}


@respx.mock
async def test_delete_webhook_returns_empty_on_204(client, base_url):
    route = respx.delete(f"{base_url}/webhooks/wh_1").mock(
        return_value=httpx.Response(204),
    )
    out = await ops.delete_webhook(client, webhook_id="wh_1")
    assert out == {}
    assert route.calls.last.request.method == "DELETE"


@respx.mock
async def test_delete_webhook_404_raises(client, base_url):
    respx.delete(f"{base_url}/webhooks/missing").mock(
        return_value=httpx.Response(
            404, json={"code": "NotFound", "message": "no such webhook"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.delete_webhook(client, webhook_id="missing")
    assert exc.value.status_code == 404


@respx.mock
async def test_rotate_signing_secret_with_expiration(client, base_url):
    rotated = {**_WEBHOOK, "signing_secret": "wsk_new"}
    route = respx.post(f"{base_url}/webhooks/wh_1/rotate-signing-secret").mock(
        return_value=httpx.Response(200, json=rotated),
    )
    out = await ops.rotate_webhook_signing_secret(
        client, webhook_id="wh_1", expiration_period="PT5H30M",
    )
    assert out["signing_secret"] == "wsk_new"
    req = route.calls.last.request
    assert req.method == "POST"
    sent = _json.loads(req.content)
    assert sent == {"expiration_period": "PT5H30M"}


@respx.mock
async def test_rotate_signing_secret_without_expiration_sends_empty_body(client, base_url):
    route = respx.post(f"{base_url}/webhooks/wh_1/rotate-signing-secret").mock(
        return_value=httpx.Response(200, json=_WEBHOOK),
    )
    await ops.rotate_webhook_signing_secret(client, webhook_id="wh_1")
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {}


@respx.mock
async def test_rotate_signing_secret_404_raises(client, base_url):
    respx.post(f"{base_url}/webhooks/missing/rotate-signing-secret").mock(
        return_value=httpx.Response(404, json={"message": "no such webhook"}),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.rotate_webhook_signing_secret(client, webhook_id="missing")
    assert exc.value.status_code == 404
