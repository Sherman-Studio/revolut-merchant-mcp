"""Customers-domain operations tests.

Thorough respx-mocked coverage of every Customers endpoint (incl. the nested
payment-methods sub-resource): method + path + query params + request body +
parsed response, plus error-path coverage. Mirrors tests/test_operations.py.
"""

from __future__ import annotations

import json as _json

import httpx
import pytest
import respx

from revolut_merchant_mcp.client import RevolutAPIError
from revolut_merchant_mcp.operations import customers as ops


# --------------------------------------------------------------------------- #
# Customers
# --------------------------------------------------------------------------- #
@respx.mock
async def test_list_customers_no_filter_omits_params(client, base_url):
    route = respx.get(f"{base_url}/customers").mock(
        return_value=httpx.Response(200, json={"customers": [{"id": "cus_1"}]}),
    )
    out = await ops.list_customers(client)
    assert out == {"customers": [{"id": "cus_1"}]}
    # No query params when nothing supplied.
    assert str(route.calls.last.request.url) == f"{base_url}/customers"


@respx.mock
async def test_list_customers_with_email_and_pagination(client, base_url):
    route = respx.get(f"{base_url}/customers").mock(
        return_value=httpx.Response(200, json={"customers": []}),
    )
    await ops.list_customers(client, email="a@b.com", limit=10, offset=2)
    params = route.calls.last.request.url.params
    assert params["email"] == "a@b.com"
    assert params["limit"] == "10"
    assert params["offset"] == "2"
    assert route.calls.last.request.method == "GET"


@respx.mock
async def test_get_customer(client, base_url):
    route = respx.get(f"{base_url}/customers/cus_1").mock(
        return_value=httpx.Response(
            200,
            json={"id": "cus_1", "email": "a@b.com", "payment_methods": []},
        ),
    )
    out = await ops.get_customer(client, customer_id="cus_1")
    assert out["id"] == "cus_1"
    assert "payment_methods" in out
    assert route.calls.last.request.method == "GET"


@respx.mock
async def test_create_customer_full_body(client, base_url):
    route = respx.post(f"{base_url}/customers").mock(
        return_value=httpx.Response(201, json={"id": "cus_2", "email": "x@y.com"}),
    )
    out = await ops.create_customer(
        client,
        email="x@y.com",
        full_name="X Y",
        phone="+447700900000",
        date_of_birth="1990-01-01",
    )
    assert out["id"] == "cus_2"
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {
        "email": "x@y.com",
        "full_name": "X Y",
        "phone": "+447700900000",
        "date_of_birth": "1990-01-01",
    }
    assert route.calls.last.request.method == "POST"


@respx.mock
async def test_create_customer_minimal_only_email(client, base_url):
    route = respx.post(f"{base_url}/customers").mock(
        return_value=httpx.Response(201, json={"id": "cus_3"}),
    )
    await ops.create_customer(client, email="only@email.com")
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"email": "only@email.com"}


@respx.mock
async def test_update_customer_sends_only_provided_fields(client, base_url):
    route = respx.patch(f"{base_url}/customers/cus_1").mock(
        return_value=httpx.Response(200, json={"id": "cus_1", "phone": "+10000000000"}),
    )
    out = await ops.update_customer(client, customer_id="cus_1", phone="+10000000000")
    assert out["phone"] == "+10000000000"
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"phone": "+10000000000"}
    assert route.calls.last.request.method == "PATCH"


@respx.mock
async def test_update_customer_empty_string_is_sent(client, base_url):
    # Distinguish "" (clear field) from None (omit) — None is the only skip.
    route = respx.patch(f"{base_url}/customers/cus_1").mock(
        return_value=httpx.Response(200, json={"id": "cus_1"}),
    )
    await ops.update_customer(client, customer_id="cus_1", full_name="")
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"full_name": ""}


@respx.mock
async def test_delete_customer_returns_empty_dict(client, base_url):
    route = respx.delete(f"{base_url}/customers/cus_1").mock(
        return_value=httpx.Response(204),
    )
    out = await ops.delete_customer(client, customer_id="cus_1")
    assert out == {}
    assert route.calls.last.request.method == "DELETE"


# --------------------------------------------------------------------------- #
# Payment methods (nested sub-resource)
# --------------------------------------------------------------------------- #
@respx.mock
async def test_list_payment_methods_no_filter(client, base_url):
    route = respx.get(f"{base_url}/customers/cus_1/payment-methods").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": "pm_1", "type": "card", "saved_for": "MERCHANT"}],
        ),
    )
    out = await ops.list_payment_methods(client, customer_id="cus_1")
    # A bare list is wrapped by the client into {"data": [...]}.
    assert out == {"data": [{"id": "pm_1", "type": "card", "saved_for": "MERCHANT"}]}
    assert str(route.calls.last.request.url) == (
        f"{base_url}/customers/cus_1/payment-methods"
    )


@respx.mock
async def test_list_payment_methods_only_merchant_query(client, base_url):
    route = respx.get(f"{base_url}/customers/cus_1/payment-methods").mock(
        return_value=httpx.Response(200, json=[]),
    )
    await ops.list_payment_methods(client, customer_id="cus_1", only_merchant=True)
    assert route.calls.last.request.url.params["only_merchant"] == "true"


@respx.mock
async def test_get_payment_method(client, base_url):
    route = respx.get(
        f"{base_url}/customers/cus_1/payment-methods/pm_1",
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "pm_1",
                "type": "card",
                "saved_for": "MERCHANT",
                "last_four": "4242",
            },
        ),
    )
    out = await ops.get_payment_method(
        client, customer_id="cus_1", payment_method_id="pm_1",
    )
    assert out["last_four"] == "4242"
    assert route.calls.last.request.method == "GET"


@respx.mock
async def test_update_payment_method_body(client, base_url):
    route = respx.patch(
        f"{base_url}/customers/cus_1/payment-methods/pm_1",
    ).mock(
        return_value=httpx.Response(
            200, json={"id": "pm_1", "saved_for": "CUSTOMER"},
        ),
    )
    out = await ops.update_payment_method(
        client, customer_id="cus_1", payment_method_id="pm_1", saved_for="CUSTOMER",
    )
    assert out["saved_for"] == "CUSTOMER"
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"saved_for": "CUSTOMER"}
    assert route.calls.last.request.method == "PATCH"


@respx.mock
async def test_delete_payment_method_returns_empty_dict(client, base_url):
    route = respx.delete(
        f"{base_url}/customers/cus_1/payment-methods/pm_1",
    ).mock(return_value=httpx.Response(204))
    out = await ops.delete_payment_method(
        client, customer_id="cus_1", payment_method_id="pm_1",
    )
    assert out == {}
    assert route.calls.last.request.method == "DELETE"


# --------------------------------------------------------------------------- #
# Error paths
# --------------------------------------------------------------------------- #
@respx.mock
async def test_get_customer_404_raises(client, base_url):
    respx.get(f"{base_url}/customers/missing").mock(
        return_value=httpx.Response(
            404, json={"code": "not_found", "message": "Customer not found"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.get_customer(client, customer_id="missing")
    assert exc.value.status_code == 404
    assert exc.value.code == "not_found"


@respx.mock
async def test_get_payment_method_404_raises(client, base_url):
    respx.get(
        f"{base_url}/customers/cus_1/payment-methods/missing",
    ).mock(
        return_value=httpx.Response(
            404, json={"code": "not_found", "message": "Payment method not found"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.get_payment_method(
            client, customer_id="cus_1", payment_method_id="missing",
        )
    assert exc.value.status_code == 404
