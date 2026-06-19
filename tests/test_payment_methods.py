"""Payment-methods operations tests: each op hits the right verb/path and returns
the parsed body. respx mocks the sandbox host.

Payment methods are customer-nested (``/customers/{id}/payment-methods``) and so
live in the ``customers`` domain module; the pure ops are imported from there.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from revolut_merchant_mcp.client import RevolutAPIError
from revolut_merchant_mcp.operations import customers as pm


@respx.mock
async def test_list_payment_methods(client, base_url):
    route = respx.get(f"{base_url}/customers/cus_1/payment-methods").mock(
        return_value=httpx.Response(
            200, json={"payment_methods": [{"id": "pm_1", "method_type": "card"}]},
        ),
    )
    out = await pm.list_payment_methods(client, customer_id="cus_1")
    assert out == {"payment_methods": [{"id": "pm_1", "method_type": "card"}]}
    req = route.calls.last.request
    assert req.method == "GET"
    assert req.url.path == "/api/customers/cus_1/payment-methods"


@respx.mock
async def test_get_payment_method(client, base_url):
    route = respx.get(f"{base_url}/customers/cus_1/payment-methods/pm_1").mock(
        return_value=httpx.Response(
            200, json={"id": "pm_1", "method_type": "card", "saved_for": "cus_1"},
        ),
    )
    out = await pm.get_payment_method(
        client, customer_id="cus_1", payment_method_id="pm_1",
    )
    assert out["id"] == "pm_1"
    assert out["method_type"] == "card"
    req = route.calls.last.request
    assert req.method == "GET"
    assert req.url.path == "/api/customers/cus_1/payment-methods/pm_1"


@respx.mock
async def test_delete_payment_method_returns_empty_on_204(client, base_url):
    route = respx.delete(f"{base_url}/customers/cus_1/payment-methods/pm_1").mock(
        return_value=httpx.Response(204),
    )
    out = await pm.delete_payment_method(
        client, customer_id="cus_1", payment_method_id="pm_1",
    )
    assert out == {}
    req = route.calls.last.request
    assert req.method == "DELETE"
    assert req.url.path == "/api/customers/cus_1/payment-methods/pm_1"
    # DELETE carries no request body.
    assert not req.content


@respx.mock
async def test_get_payment_method_404_raises(client, base_url):
    respx.get(f"{base_url}/customers/cus_1/payment-methods/missing").mock(
        return_value=httpx.Response(
            404, json={"code": "not_found", "message": "Payment method not found"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await pm.get_payment_method(
            client, customer_id="cus_1", payment_method_id="missing",
        )
    assert exc.value.status_code == 404
    assert exc.value.code == "not_found"


@respx.mock
async def test_delete_payment_method_404_raises(client, base_url):
    respx.delete(f"{base_url}/customers/cus_1/payment-methods/missing").mock(
        return_value=httpx.Response(
            404, json={"code": "not_found", "message": "Payment method not found"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await pm.delete_payment_method(
            client, customer_id="cus_1", payment_method_id="missing",
        )
    assert exc.value.status_code == 404
