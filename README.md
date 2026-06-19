# revolut-merchant-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for the
**Revolut Merchant API** — letting MCP-aware AI assistants (Claude Desktop,
Cursor, agent harnesses) read and manage Revolut **customers, orders,
subscriptions, and plans**.

> **Why this exists.** The existing community Revolut MCP wraps the Revolut
> *Business* API (accounts, balances, transfers). This server targets the
> *Merchant* API — the surface you use to **accept payments and run
> subscriptions** — which had no MCP server until now.

Status: **alpha / proof-of-concept.** Sandbox-first, read-only by default.

## Features

- **Read tools** (always on): `list_customers`, `get_customer`, `list_orders`,
  `get_order`, `list_subscriptions`, `get_subscription`, `list_plans`, `get_plan`
- **Write tools** (opt-in via `REVOLUT_MCP_ALLOW_WRITES=true`):
  `create_customer`, `create_order`, `create_subscription`, `cancel_subscription`
- **Safe defaults**: sandbox unless you explicitly opt into production; writes
  disabled unless explicitly enabled; idempotency keys + transient-error retry in
  the transport layer.

## Install

```bash
# with uv (recommended)
uv pip install -e ".[dev]"

# or pip
pip install -e ".[dev]"
```

## Configure

Copy `.env.example` and set your sandbox key:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `REVOLUT_MERCHANT_SECRET_KEY` | ✅ | — | Merchant API secret (sandbox or live) |
| `REVOLUT_API_VERSION` | | `2024-09-01` | Sent as `Revolut-Api-Version` |
| `REVOLUT_SANDBOX` | | `true` | `false` = production (guarded) |
| `REVOLUT_I_UNDERSTAND_PRODUCTION` | | `false` | Required to run against production |
| `REVOLUT_MCP_ALLOW_WRITES` | | `false` | Register the create/cancel tools |

Sandbox keys come from the Revolut Sandbox Business dashboard (Merchant API).

## Run

```bash
REVOLUT_MERCHANT_SECRET_KEY=sk_sandbox_... revolut-merchant-mcp
```

The server speaks MCP over **stdio**.

### Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "revolut-merchant": {
      "command": "revolut-merchant-mcp",
      "env": {
        "REVOLUT_MERCHANT_SECRET_KEY": "sk_sandbox_...",
        "REVOLUT_SANDBOX": "true"
      }
    }
  }
}
```

## Architecture

```
config.py       env → Config (sandbox/prod guard, write gate)
client.py       async transport: auth, versioning, idempotency, retry, errors
operations.py   one framework-free async fn per Merchant endpoint (unit-tested)
server.py       FastMCP wrapper — registers operations as tools (writes gated)
```

`operations.py` has **no MCP dependency**, so the API layer is fully testable
with `respx` and reusable outside the server.

## Develop

```bash
ruff check .
pytest
```

Tests mock the Revolut sandbox host with `respx` — no live keys, no network.

## Safety notes

- This server can create live customers, orders, and subscriptions when writes
  are enabled against a production key. Both are off by default and each requires
  an explicit opt-in.
- Treat your Merchant secret like any payment credential. Prefer a sandbox key
  for anything agent-driven.

## License

MIT © Sherman Studio Ltd. Not affiliated with or endorsed by Revolut.
