# revolut-merchant-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for the
**Revolut Merchant API** — letting MCP-aware AI assistants (Claude Desktop,
Cursor, agent harnesses) read and manage Revolut **customers, payment methods,
orders, subscriptions, plans, and webhooks**.

> **Why this exists.** The existing community Revolut MCP wraps the Revolut
> *Business* API (accounts, balances, transfers). This server targets the
> *Merchant* API — the surface you use to **accept payments and run
> subscriptions** — which had no MCP server until now.

Status: **alpha / proof-of-concept.** Sandbox-first, read-only by default.

## Features

Broad Merchant API coverage across six domains. **Read tools are always
registered; write (mutating) tools are registered only when
`REVOLUT_MCP_ALLOW_WRITES=true`** — so the default posture is read-only.

| Domain | Read tools (always on) | Write tools (gated by `REVOLUT_MCP_ALLOW_WRITES`) |
|---|---|---|
| **Customers** | `list_customers`, `get_customer` | `create_customer`, `update_customer`, `delete_customer` |
| **Payment methods** (customer-nested) | `list_payment_methods`, `get_payment_method` | `update_payment_method`, `delete_payment_method` |
| **Orders** | `list_orders`, `get_order` | `create_order`, `update_order`, `capture_order`, `cancel_order`, `pay_order`, `refund_order`, `increment_authorisation` |
| **Subscriptions** | `list_subscriptions`, `get_subscription`, `list_subscription_cycles`, `get_subscription_cycle` | `create_subscription`, `update_subscription`, `cancel_subscription`, `change_subscription_plan`, `update_subscription_renewal_date` |
| **Plans** | `list_plans`, `get_plan` | `create_plan` |
| **Webhooks** | `list_webhooks`, `get_webhook` | `create_webhook`, `update_webhook`, `delete_webhook`, `rotate_webhook_signing_secret` |

That's **14 read tools** and **21 write tools** (35 total).

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
config.py        env → Config (sandbox/prod guard, write gate)
client.py        async transport: auth, versioning, idempotency, retry, errors
operations/      one module per domain (customers, orders, subscriptions,
                 plans, webhooks); each holds framework-free async fns plus a
                 register(mcp, client, allow_writes, safe) that wires its tools
server.py        FastMCP wrapper — iterates the domain registrars (writes gated)
```

The pure functions in `operations/` have **no MCP dependency**, so the API layer
is fully testable with `respx` and reusable outside the server. Payment methods
are customer-nested (`/customers/{id}/payment-methods`) and so live in the
`customers` module.

## Develop

```bash
ruff check .
pytest
```

Tests mock the Revolut sandbox host with `respx` — no live keys, no network.

## Safety notes

- This server can mutate live data (customers, payment methods, orders,
  subscriptions, plans, and webhooks — including refunds and order capture) when
  writes are enabled against a production key. Production and writes are both off
  by default and each requires an explicit opt-in.
- Treat your Merchant secret like any payment credential. Prefer a sandbox key
  for anything agent-driven.

## License

MIT © Sherman Studio Ltd. Not affiliated with or endorsed by Revolut.
