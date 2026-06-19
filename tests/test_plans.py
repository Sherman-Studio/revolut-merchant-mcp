"""Plans-domain operations tests: each op hits the right path/verb, sends the
right query/body, and returns the parsed response. respx mocks the sandbox host.
Mirrors tests/test_operations.py structure."""

from __future__ import annotations

import json as _json

import httpx
import pytest
import respx

from revolut_merchant_mcp import operations as ops
from revolut_merchant_mcp.client import RevolutAPIError


@respx.mock
async def test_list_plans(client, base_url):
    route = respx.get(f"{base_url}/subscription-plans").mock(
        return_value=httpx.Response(200, json={"plans": [{"id": "plan_1"}]}),
    )
    out = await ops.list_plans(client)
    assert out == {"plans": [{"id": "plan_1"}]}
    assert route.calls.last.request.method == "GET"
    assert route.calls.last.request.url.path.endswith("/subscription-plans")


@respx.mock
async def test_get_plan(client, base_url):
    route = respx.get(f"{base_url}/subscription-plans/plan_1").mock(
        return_value=httpx.Response(200, json={"id": "plan_1", "variations": []}),
    )
    out = await ops.get_plan(client, plan_id="plan_1")
    assert out["id"] == "plan_1"
    assert route.calls.last.request.method == "GET"


@respx.mock
async def test_create_plan_posts_name_and_variations(client, base_url):
    route = respx.post(f"{base_url}/subscription-plans").mock(
        return_value=httpx.Response(201, json={"id": "plan_2", "name": "Gold"}),
    )
    variations = [
        {
            "name": "Monthly",
            "phases": [
                {"amount": 9900, "currency": "GBP", "cycle_duration": "P1M"},
            ],
        },
    ]
    out = await ops.create_plan(client, name="Gold", variations=variations)
    assert out == {"id": "plan_2", "name": "Gold"}

    req = route.calls.last.request
    assert req.method == "POST"
    assert req.url.path.endswith("/subscription-plans")
    sent = _json.loads(req.content)
    assert sent == {"name": "Gold", "variations": variations}
    # No trial_period given -> key omitted.
    assert "trial_period" not in sent


@respx.mock
async def test_create_plan_includes_trial_period_when_given(client, base_url):
    route = respx.post(f"{base_url}/subscription-plans").mock(
        return_value=httpx.Response(201, json={"id": "plan_3"}),
    )
    await ops.create_plan(
        client,
        name="Pro",
        variations=[{"name": "Yearly", "phases": []}],
        trial_period="P14D",
    )
    sent = _json.loads(route.calls.last.request.content)
    assert sent["trial_period"] == "P14D"
    assert sent["name"] == "Pro"


@respx.mock
async def test_create_plan_forwards_idempotency_key(client, base_url):
    route = respx.post(f"{base_url}/subscription-plans").mock(
        return_value=httpx.Response(201, json={"id": "plan_4"}),
    )
    await ops.create_plan(
        client,
        name="Silver",
        variations=[{"name": "Monthly", "phases": []}],
        idempotency_key="idem-123",
    )
    assert route.calls.last.request.headers["Idempotency-Key"] == "idem-123"


@respx.mock
async def test_get_plan_404_raises_api_error(client, base_url):
    respx.get(f"{base_url}/subscription-plans/missing").mock(
        return_value=httpx.Response(
            404, json={"code": "not_found", "message": "Plan not found"},
        ),
    )
    with pytest.raises(RevolutAPIError) as excinfo:
        await ops.get_plan(client, plan_id="missing")
    assert excinfo.value.status_code == 404
    assert excinfo.value.code == "not_found"
