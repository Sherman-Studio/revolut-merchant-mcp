"""Plans domain operations.

Pure, framework-free async wrappers over ``RevolutClient`` for the Merchant
subscription-plans endpoints. NOTE: existing code uses the ``/plans`` path; the
research catalog suggests the live path is ``/subscription-plans`` — kept as-is
for backward-compat in this refactor (tracked in uncertain_endpoints).

``register`` attaches the MCP tools (read always, write gated). Tool functions
share names with the pure ops and call them via ``_``-prefixed private aliases.
"""

from __future__ import annotations

from ..client import RevolutClient

__all__ = [
    "list_plans",
    "get_plan",
    "create_plan",
]


async def list_plans(client: RevolutClient) -> dict:
    """List merchant subscription plans."""
    return await client.get("/plans")


async def get_plan(client: RevolutClient, *, plan_id: str) -> dict:
    """Retrieve a single plan (including its variations) by id."""
    return await client.get(f"/plans/{plan_id}")


async def create_plan(
    client: RevolutClient,
    *,
    name: str,
    variations: list[dict],
    trial_period: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Create a subscription plan. WRITE.

    A plan has one or more ``variations`` (e.g. "Monthly", "Yearly"); each
    variation carries one or more billing ``phases`` (e.g. a free trial phase
    followed by a recurring phase). Any phase ``amount`` is in the minor unit of
    its ``currency`` (e.g. 9900 == GBP £99.00); cycle lengths are ISO 8601
    durations (e.g. "P1M"). ``trial_period`` is the plan-level default trial as
    an ISO 8601 duration (e.g. "P14D"). ``variations`` is passed through as-is so
    the full phase/item structure is available to the caller.
    """
    body: dict = {"name": name, "variations": variations}
    if trial_period:
        body["trial_period"] = trial_period
    return await client.post("/plans", json=body, idempotency_key=idempotency_key)


_list_plans = list_plans
_get_plan = get_plan
_create_plan = create_plan


def register(mcp, client, allow_writes, safe) -> None:
    """Register the plans-domain MCP tools."""

    @mcp.tool()
    async def list_plans() -> dict:
        """List Merchant subscription plans."""
        return await safe(_list_plans(client))

    @mcp.tool()
    async def get_plan(plan_id: str) -> dict:
        """Retrieve a single plan, including its variations, by id."""
        return await safe(_get_plan(client, plan_id=plan_id))

    if allow_writes:

        @mcp.tool()
        async def create_plan(
            name: str,
            variations: list[dict],
            trial_period: str | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            """Create a Merchant subscription plan. Phase amounts are in the minor
            unit (cents/pence). WRITE — requires REVOLUT_MCP_ALLOW_WRITES."""
            return await safe(
                _create_plan(
                    client,
                    name=name,
                    variations=variations,
                    trial_period=trial_period,
                    idempotency_key=idempotency_key,
                ),
            )
