"""Transport-client tests: auth headers, versioning, idempotency, retries,
error mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from revolut_merchant_mcp.client import (
    PRODUCTION_BASE,
    SANDBOX_BASE,
    RevolutAPIError,
    RevolutClient,
)


def test_sandbox_vs_production_base_url():
    sb = RevolutClient(secret_key="k", api_version="2024-09-01", sandbox=True)
    prod = RevolutClient(secret_key="k", api_version="2024-09-01", sandbox=False)
    assert sb.base_url == SANDBOX_BASE
    assert prod.base_url == PRODUCTION_BASE


def test_empty_secret_rejected():
    with pytest.raises(ValueError):
        RevolutClient(secret_key="", api_version="2024-09-01")


@respx.mock
async def test_sends_auth_and_version_headers(client, base_url):
    route = respx.get(f"{base_url}/customers").mock(
        return_value=httpx.Response(200, json={"customers": []}),
    )
    await client.get("/customers")
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer sk_sandbox_test"
    assert req.headers["Revolut-Api-Version"] == "2024-09-01"


@respx.mock
async def test_idempotency_key_forwarded_on_post(client, base_url):
    route = respx.post(f"{base_url}/orders").mock(
        return_value=httpx.Response(201, json={"id": "ord_1"}),
    )
    await client.post("/orders", json={"amount": 100, "currency": "GBP"}, idempotency_key="abc")
    assert route.calls.last.request.headers["Idempotency-Key"] == "abc"


@respx.mock
async def test_retries_on_503_then_succeeds(client, base_url):
    route = respx.get(f"{base_url}/plans").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"plans": [{"id": "plan_1"}]}),
        ],
    )
    body = await client.get("/plans")
    assert body == {"plans": [{"id": "plan_1"}]}
    assert route.call_count == 2


@respx.mock
async def test_non_2xx_raises_structured_error(client, base_url):
    respx.get(f"{base_url}/customers/missing").mock(
        return_value=httpx.Response(
            404, json={"code": "not_found", "message": "Customer not found"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await client.get("/customers/missing")
    assert exc.value.status_code == 404
    assert exc.value.code == "not_found"
    assert "not found" in str(exc.value).lower()


@respx.mock
async def test_empty_2xx_body_returns_empty_dict(client, base_url):
    respx.post(f"{base_url}/subscriptions/sub_1/cancel").mock(
        return_value=httpx.Response(204),
    )
    assert await client.post("/subscriptions/sub_1/cancel", json={}) == {}
