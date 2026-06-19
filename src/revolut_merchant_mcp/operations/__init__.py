"""Revolut Merchant API operations, split one module per domain.

Each domain module (``customers``, ``orders``, ``subscriptions``, ``plans``,
``webhooks``) holds the pure, framework-free async wrappers over
``RevolutClient`` plus a ``register(mcp, client, allow_writes, safe)`` that wires
that domain's MCP tools. The pure functions are re-exported here via
``from .<domain> import *`` so the historical flat import surface keeps working::

    from revolut_merchant_mcp import operations as ops
    await ops.list_customers(client, email="a@b.com")

``server.py`` iterates the per-domain ``register`` callables exposed below.
"""

from __future__ import annotations

from .customers import *  # noqa: F401,F403
from .customers import register as register_customers
from .orders import *  # noqa: F401,F403
from .orders import register as register_orders
from .plans import *  # noqa: F401,F403
from .plans import register as register_plans
from .subscriptions import *  # noqa: F401,F403
from .subscriptions import register as register_subscriptions
from .webhooks import *  # noqa: F401,F403
from .webhooks import register as register_webhooks

# Ordered list of domain registrars for server.py to iterate.
REGISTRARS = (
    register_customers,
    register_orders,
    register_subscriptions,
    register_plans,
    register_webhooks,
)
