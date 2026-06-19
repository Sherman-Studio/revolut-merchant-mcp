"""Operations-layer tests: each Merchant op hits the right path/verb and returns
the parsed body. respx mocks the sandbox host."""

from __future__ import annotations

import httpx
import respx

from revolut_merchant_mcp import operations as ops


@respx.mock
async def test_list_customers_with_email_filter(client, base_url):
    route = respx.get(f"{base_url}/customers").mock(
        return_value=httpx.Response(200, json={"customers": [{"id": "cus_1"}]}),
    )
    out = await ops.list_customers(client, email="a@b.com")
    assert out == {"customers": [{"id": "cus_1"}]}
    assert route.calls.last.request.url.params["email"] == "a@b.com"


@respx.mock
async def test_get_customer(client, base_url):
    respx.get(f"{base_url}/customers/cus_1").mock(
        return_value=httpx.Response(200, json={"id": "cus_1", "email": "a@b.com"}),
    )
    out = await ops.get_customer(client, customer_id="cus_1")
    assert out["id"] == "cus_1"


@respx.mock
async def test_create_customer_posts_full_name(client, base_url):
    route = respx.post(f"{base_url}/customers").mock(
        return_value=httpx.Response(201, json={"id": "cus_2"}),
    )
    await ops.create_customer(client, email="x@y.com", full_name="X Y")
    import json as _json

    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"email": "x@y.com", "full_name": "X Y"}


@respx.mock
async def test_create_order_uppercases_currency_and_keeps_minor_amount(client, base_url):
    route = respx.post(f"{base_url}/orders").mock(
        return_value=httpx.Response(201, json={"id": "ord_1", "state": "pending"}),
    )
    await ops.create_order(client, amount=799, currency="gbp", description="Pro")
    import json as _json

    sent = _json.loads(route.calls.last.request.content)
    assert sent["amount"] == 799
    assert sent["currency"] == "GBP"
    assert sent["description"] == "Pro"


@respx.mock
async def test_list_subscriptions_filtered_by_customer(client, base_url):
    route = respx.get(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(200, json={"subscriptions": []}),
    )
    await ops.list_subscriptions(client, customer_id="cus_1")
    assert route.calls.last.request.url.params["customer_id"] == "cus_1"


@respx.mock
async def test_create_subscription_body(client, base_url):
    route = respx.post(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(
            201, json={"id": "sub_1", "state": "pending", "setup_order_token": "tok_1"},
        ),
    )
    out = await ops.create_subscription(client, plan_variation_id="var_1", customer_id="cus_1")
    assert out["setup_order_token"] == "tok_1"
    import json as _json

    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"plan_variation_id": "var_1", "customer_id": "cus_1"}


@respx.mock
async def test_cancel_subscription_posts_then_reads_back(client, base_url):
    cancel = respx.post(f"{base_url}/subscriptions/sub_1/cancel").mock(
        return_value=httpx.Response(204),
    )
    respx.get(f"{base_url}/subscriptions/sub_1").mock(
        return_value=httpx.Response(200, json={"id": "sub_1", "state": "cancelled"}),
    )
    out = await ops.cancel_subscription(client, subscription_id="sub_1")
    assert cancel.called
    assert out["state"] == "cancelled"


@respx.mock
async def test_get_plan(client, base_url):
    respx.get(f"{base_url}/subscription-plans/plan_1").mock(
        return_value=httpx.Response(200, json={"id": "plan_1", "variations": []}),
    )
    out = await ops.get_plan(client, plan_id="plan_1")
    assert out["id"] == "plan_1"
