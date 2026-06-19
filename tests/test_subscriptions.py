"""Subscriptions-domain operations tests.

Each Merchant Subscriptions op is exercised for the right verb/path/query/body
and parsed response, plus error-path coverage (4xx -> RevolutAPIError). respx
mocks the sandbox host; the ``client`` / ``base_url`` fixtures come from
conftest.py.
"""

from __future__ import annotations

import json as _json

import httpx
import pytest
import respx

from revolut_merchant_mcp import operations as ops
from revolut_merchant_mcp.client import RevolutAPIError

# --- reads ------------------------------------------------------------------

@respx.mock
async def test_list_subscriptions_no_filter(client, base_url):
    route = respx.get(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(
            200, json={"next_page_token": None, "subscriptions": [{"id": "sub_1"}]},
        ),
    )
    out = await ops.list_subscriptions(client)
    assert out == {"next_page_token": None, "subscriptions": [{"id": "sub_1"}]}
    assert route.calls.last.request.method == "GET"
    # No filters -> no query string.
    assert route.calls.last.request.url.query == b""


@respx.mock
async def test_list_subscriptions_filtered_by_external_reference(client, base_url):
    route = respx.get(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(200, json={"subscriptions": []}),
    )
    await ops.list_subscriptions(client, external_reference="ext-42")
    assert route.calls.last.request.url.params["external_reference"] == "ext-42"


@respx.mock
async def test_list_subscriptions_filtered_by_customer(client, base_url):
    route = respx.get(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(200, json={"subscriptions": []}),
    )
    await ops.list_subscriptions(client, customer_id="cus_1")
    assert route.calls.last.request.url.params["customer_id"] == "cus_1"


@respx.mock
async def test_get_subscription(client, base_url):
    respx.get(f"{base_url}/subscriptions/sub_1").mock(
        return_value=httpx.Response(
            200, json={"id": "sub_1", "state": "active", "customer_id": "cus_1"},
        ),
    )
    out = await ops.get_subscription(client, subscription_id="sub_1")
    assert out["id"] == "sub_1"
    assert out["state"] == "active"


@respx.mock
async def test_list_subscription_cycles(client, base_url):
    route = respx.get(f"{base_url}/subscriptions/sub_1/cycles").mock(
        return_value=httpx.Response(
            200, json={"next_page_token": None, "cycles": [{"id": "cyc_1"}]},
        ),
    )
    out = await ops.list_subscription_cycles(client, subscription_id="sub_1")
    assert out["cycles"] == [{"id": "cyc_1"}]
    assert route.calls.last.request.method == "GET"


@respx.mock
async def test_get_subscription_cycle(client, base_url):
    respx.get(f"{base_url}/subscriptions/sub_1/cycles/cyc_1").mock(
        return_value=httpx.Response(
            200,
            json={"id": "cyc_1", "subscription_id": "sub_1", "state": "ongoing", "number": 1},
        ),
    )
    out = await ops.get_subscription_cycle(
        client, subscription_id="sub_1", cycle_id="cyc_1",
    )
    assert out["id"] == "cyc_1"
    assert out["subscription_id"] == "sub_1"


# --- writes -----------------------------------------------------------------

@respx.mock
async def test_create_subscription_minimal_body(client, base_url):
    route = respx.post(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(
            201, json={"id": "sub_1", "state": "pending"},
        ),
    )
    out = await ops.create_subscription(
        client, plan_variation_id="var_1", customer_id="cus_1",
    )
    assert out == {"id": "sub_1", "state": "pending"}
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"plan_variation_id": "var_1", "customer_id": "cus_1"}


@respx.mock
async def test_create_subscription_full_body_with_idempotency_key(client, base_url):
    route = respx.post(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(
            201, json={"id": "sub_2", "state": "pending", "setup_order_id": "ord_9"},
        ),
    )
    out = await ops.create_subscription(
        client,
        plan_variation_id="var_1",
        customer_id="cus_1",
        external_reference="ext-7",
        setup_order_redirect_url="https://example.com/done",
        trial_duration="P14D",
        idempotency_key="idem-123",
    )
    assert out["setup_order_id"] == "ord_9"
    req = route.calls.last.request
    sent = _json.loads(req.content)
    assert sent == {
        "plan_variation_id": "var_1",
        "customer_id": "cus_1",
        "external_reference": "ext-7",
        "setup_order_redirect_url": "https://example.com/done",
        "trial_duration": "P14D",
    }
    assert req.headers["Idempotency-Key"] == "idem-123"


@respx.mock
async def test_update_subscription_patches_external_reference(client, base_url):
    route = respx.patch(f"{base_url}/subscriptions/sub_1").mock(
        return_value=httpx.Response(
            200, json={"id": "sub_1", "external_reference": "ext-new"},
        ),
    )
    out = await ops.update_subscription(
        client, subscription_id="sub_1", external_reference="ext-new",
    )
    assert out["external_reference"] == "ext-new"
    assert route.calls.last.request.method == "PATCH"
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"external_reference": "ext-new"}


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
    assert _json.loads(cancel.calls.last.request.content) == {}
    assert out["state"] == "cancelled"


@respx.mock
async def test_change_subscription_plan_minimal(client, base_url):
    route = respx.post(f"{base_url}/subscriptions/sub_1/change-plan").mock(
        return_value=httpx.Response(204),
    )
    out = await ops.change_subscription_plan(
        client, subscription_id="sub_1", plan_variation_id="var_2", scheduled=True,
    )
    assert out == {}
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"plan_variation_id": "var_2", "scheduled": True}


@respx.mock
async def test_change_subscription_plan_full_body(client, base_url):
    route = respx.post(f"{base_url}/subscriptions/sub_1/change-plan").mock(
        return_value=httpx.Response(204),
    )
    await ops.change_subscription_plan(
        client,
        subscription_id="sub_1",
        plan_variation_id="var_2",
        scheduled=False,
        plan_variation_phase_id="phase_1",
        reason="upgrade",
    )
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {
        "plan_variation_id": "var_2",
        "scheduled": False,
        "plan_variation_phase_id": "phase_1",
        "reason": "upgrade",
    }


@respx.mock
async def test_update_subscription_renewal_date(client, base_url):
    route = respx.post(f"{base_url}/subscriptions/sub_1/change-renewal-date").mock(
        return_value=httpx.Response(204),
    )
    out = await ops.update_subscription_renewal_date(
        client, subscription_id="sub_1", renewal_date="2026-08-01",
    )
    assert out == {}
    assert route.calls.last.request.method == "POST"
    sent = _json.loads(route.calls.last.request.content)
    assert sent == {"renewal_date": "2026-08-01"}


# --- error paths ------------------------------------------------------------

@respx.mock
async def test_get_subscription_not_found_raises(client, base_url):
    respx.get(f"{base_url}/subscriptions/missing").mock(
        return_value=httpx.Response(
            404,
            json={"code": "not_found", "message": "Subscription not found",
                  "timestamp": "2026-06-19T00:00:00Z"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.get_subscription(client, subscription_id="missing")
    assert exc.value.status_code == 404
    assert exc.value.code == "not_found"


@respx.mock
async def test_change_subscription_plan_422_raises(client, base_url):
    respx.post(f"{base_url}/subscriptions/sub_1/change-plan").mock(
        return_value=httpx.Response(
            422,
            json={"code": "invalid_state", "message": "Cannot change plan",
                  "timestamp": "2026-06-19T00:00:00Z"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.change_subscription_plan(
            client, subscription_id="sub_1", plan_variation_id="var_2", scheduled=True,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "invalid_state"


@respx.mock
async def test_create_subscription_400_raises(client, base_url):
    respx.post(f"{base_url}/subscriptions").mock(
        return_value=httpx.Response(
            400,
            json={"code": "bad_request", "message": "customer_id is required",
                  "timestamp": "2026-06-19T00:00:00Z"},
        ),
    )
    with pytest.raises(RevolutAPIError) as exc:
        await ops.create_subscription(
            client, plan_variation_id="var_1", customer_id="cus_1",
        )
    assert exc.value.status_code == 400
