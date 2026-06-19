"""FastMCP server exposing the Revolut Merchant API as MCP tools.

Read tools are always registered. Write tools (create/update/cancel/delete) are
only registered when ``REVOLUT_MCP_ALLOW_WRITES=true`` — so the default posture
is read-only, which is the safe default for letting an autonomous model poke a
payments API.

Tool registration is delegated to the per-domain modules under
``operations`` (``customers`` — incl. payment-methods, ``orders``,
``subscriptions``, ``plans``, ``webhooks``). ``build_server`` constructs the
client and the error-mapping ``_safe`` helper, then calls each domain's
``register(mcp, client, allow_writes, safe)``.

Run it::

    REVOLUT_MERCHANT_SECRET_KEY=sk_sandbox_... revolut-merchant-mcp

or point your MCP client (Claude Desktop, Cursor) at ``revolut-merchant-mcp``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import RevolutAPIError, RevolutClient
from .config import Config
from .operations import customers, orders, plans, subscriptions, webhooks


def build_server(config: Config) -> FastMCP:
    """Construct a FastMCP server bound to a Revolut client built from ``config``.

    Factored out from ``main()`` so tests can build a server against a fake/mock
    client without going through the environment.
    """
    mcp = FastMCP("revolut-merchant")
    client = RevolutClient(
        secret_key=config.secret_key,
        api_version=config.api_version,
        sandbox=config.sandbox,
    )

    async def _safe(coro) -> dict[str, Any]:
        """Run an operation, mapping Revolut errors to a structured tool result
        the model can reason about instead of an opaque exception."""
        try:
            return await coro
        except RevolutAPIError as e:
            return {
                "error": str(e),
                "status_code": e.status_code,
                "code": e.code,
            }

    for mod in (customers, orders, subscriptions, plans, webhooks):
        mod.register(mcp, client, allow_writes=config.allow_writes, safe=_safe)

    return mcp


def main() -> None:
    """Console-script entry point: build from env and serve over stdio."""
    config = Config.from_env()
    server = build_server(config)
    server.run()


if __name__ == "__main__":
    main()
