"""Orders-domain operations tests.

One test per catalogued endpoint asserting verb + path + query params + request
body + parsed response, plus error-path tests (non-2xx -> RevolutAPIError).
respx mocks the sandbox host; ``client``/``base_url`` come from conftest.
"""

from __future__ import annotations

import json as _json

import httpx
import pytest
import respx

from revolut_merchant_mcp import operations as ops
from revolut_merchant_mcp.client import RevolutAPIError


def _sent(route) -> dict:
    return _json.loads(route.calls.last.request.content)


# ---------------------------------------------------------------- read paths


@respx.mock
async def test_list_orders_no_filters(client, base_url):
    route = respx.get(f"{base_url}/orders").mock(
        return_value=httpx.Response(200, json={"orders": [{"id": "ord_1"}]}),
    )
    out = await ops.list_orders(client)
    assert out == {"orders": [{"id": "ord_1"}]}
    assert route.calls.last.request.method == "GET"
    # No filters -> no query string.
    assert route.calls.last.request.url.query == b""


@respx.mock
async def test_list_orders_all_filters(client, base_url):
    route = respx.get(f"{base_url}/orders").mock(
        return_value=httpx.Response(200, json={"orders": []}),
    )
    await ops.list_orders(
        client,
        limit=25,
        from_="2026-01-01T00:00:00Z",
        to="2026-02-01T00:00:00Z",
        customer_id="cus_1",
        merchant_order_data_reference="ref_1",
        state="completed",
        location_id="loc_1",
    )
    params = route.calls.last.request.url.params
    assert params["limit"] == "25"
    assert params["from"] == "2026-01-01T00:00:00Z"
    assert params["to"] == "2026-02-01T00:00:00Z"
    assert params["customer_id"] == "cus_1"
    assert params["merchant_order_data_reference"] == "ref_1"
    assert params["state"] == "completed"
    assert params["location_id"] == "loc_1"


@respx.mock
async def test_get_order(client, base_url):
    respx.get(f"{base_url}/orders/ord_1").mock(
        return_value=httpx.Response(200, json={"id": "ord_1", "state": "completed"}),
    )
    out = await ops.get_order(client, order_id="ord_1")
    assert out["id"] == "ord_1"
    assert out["state"] == "completed"


# ---------------------------------------------------------------- write paths


@respx.mock
async def test_create_order_minimal_uppercases_currency_keeps_minor_amount(client, base_url):
    route = respx.post(f"{base_url}/orders").mock(
        return_value=httpx.Response(
            201, json={"id": "ord_1", "state": "pending", "checkout_url": "https://x"},
        ),
    )
    out = await ops.create_order(client, amount=799, currency="gbp", description="Pro")
    assert out["checkout_url"] == "https://x"
    sent = _sent(route)
    assert sent == {"amount": 799, "currency": "GBP", "description": "Pro"}


@respx.mock
async def test_create_order_customer_id_folds_into_customer(client, base_url):
    route = respx.post(f"{base_url}/orders").mock(
        return_value=httpx.Response(201, json={"id": "ord_2"}),
    )
    await ops.create_order(
        client,
        amount=1000,
        currency="usd",
        customer_id="cus_9",
        capture_mode="manual",
        authorisation_type="pre_authorisation",
        line_items=[{"name": "Widget", "quantity": {"value": 1}}],
        metadata={"k": "v"},
        idempotency_key="idem-1",
    )
    sent = _sent(route)
    assert sent["customer"] == {"id": "cus_9"}
    assert sent["capture_mode"] == "manual"
    assert sent["authorisation_type"] == "pre_authorisation"
    assert sent["line_items"] == [{"name": "Widget", "quantity": {"value": 1}}]
    assert sent["metadata"] == {"k": "v"}
    assert route.calls.last.request.headers["Idempotency-Key"] == "idem-1"


@respx.mock
async def test_update_order_patches_subset(client, base_url):
    route = respx.patch(f"{base_url}/orders/ord_1").mock(
        return_value=httpx.Response(200, json={"id": "ord_1", "amount": 500}),
    )
    out = await ops.update_order(
        client, order_id="ord_1", amount=500, description="updated",
    )
    assert out["amount"] == 500
    assert route.calls.last.request.method == "PATCH"
    assert _sent(route) == {"amount": 500, "description": "updated"}


@respx.mock
async def test_increment_authorisation_body_and_path(client, base_url):
    route = respx.post(f"{base_url}/orders/ord_1/increment-authorisation").mock(
        return_value=httpx.Response(
            200, json={"id": "ord_1", "incremental_authorisations": [{"amount": 200}]},
        ),
    )
    out = await ops.increment_authorisation(
        client, order_id="ord_1", amount=200, reference="ref",
    )
    assert out["incremental_authorisations"][0]["amount"] == 200
    assert _sent(route) == {"amount": 200, "reference": "ref"}


@respx.mock
async def test_capture_order_partial(client, base_url):
    route = respx.post(f"{base_url}/orders/ord_1/capture").mock(
        return_value=httpx.Response(200, json={"id": "ord_1", "state": "processing"}),
    )
    out = await ops.capture_order(client, order_id="ord_1", amount=300)
    assert out["state"] == "processing"
    assert _sent(route) == {"amount": 300}


@respx.mock
async def test_capture_order_full_sends_no_body(client, base_url):
    route = respx.post(f"{base_url}/orders/ord_1/capture").mock(
        return_value=httpx.Response(200, json={"id": "ord_1", "state": "processing"}),
    )
    await ops.capture_order(client, order_id="ord_1")
    # Full capture: no amount -> empty/no JSON body.
    assert route.calls.last.request.content in (b"", b"null")


@respx.mock
async def test_cancel_order(client, base_url):
    route = respx.post(f"{base_url}/orders/ord_1/cancel").mock(
        return_value=httpx.Response(200, json={"id": "ord_1", "state": "cancelled"}),
    )
    out = await ops.cancel_order(client, order_id="ord_1")
    assert out["state"] == "cancelled"
    assert route.calls.last.request.method == "POST"


@respx.mock
async def test_refund_order_creates_refund_type(client, base_url):
    route = respx.post(f"{base_url}/orders/ord_1/refund").mock(
        return_value=httpx.Response(
            201, json={"id": "ord_r", "type": "refund", "related_order_id": "ord_1"},
        ),
    )
    out = await ops.refund_order(
        client, order_id="ord_1", amount=250, currency="eur", description="oops",
    )
    assert out["type"] == "refund"
    assert out["related_order_id"] == "ord_1"
    assert _sent(route) == {"amount": 250, "currency": "EUR", "description": "oops"}


@respx.mock
async def test_pay_order_with_saved_payment_method(client, base_url):
    spm = {
        "type": "card",
        "id": "pm_1",
        "initiator": "merchant",
        "environment": "production",
    }
    route = respx.post(f"{base_url}/orders/ord_1/payments").mock(
        return_value=httpx.Response(
            200, json={"id": "pay_1", "order_id": "ord_1", "payment_method": "card"},
        ),
    )
    out = await ops.pay_order(client, order_id="ord_1", saved_payment_method=spm)
    assert out["id"] == "pay_1"
    assert out["order_id"] == "ord_1"
    assert _sent(route) == {"saved_payment_method": spm}


# ---------------------------------------------------------------- error paths


@respx.mock
async def test_get_order_404_raises(client, base_url):
    respx.get(f"{base_url}/orders/missing").mock(
        return_value=httpx.Response(
            404, json={"code": "not_found", "message": "Order not found"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.get_order(client, order_id="missing")
    assert exc.value.status_code == 404
    assert exc.value.code == "not_found"


@respx.mock
async def test_create_order_422_raises(client, base_url):
    respx.post(f"{base_url}/orders").mock(
        return_value=httpx.Response(
            422, json={"code": "invalid", "message": "bad amount"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.create_order(client, amount=-1, currency="GBP")
    assert exc.value.status_code == 422
