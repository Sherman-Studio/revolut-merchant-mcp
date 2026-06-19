"""Environment-driven configuration for the Revolut Merchant MCP server.

All settings come from environment variables so the server can run unmodified
under Claude Desktop, Cursor, an MCP gateway, or Docker.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Default Merchant API version. Override with REVOLUT_API_VERSION.
DEFAULT_API_VERSION = "2024-09-01"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    secret_key: str
    api_version: str
    sandbox: bool
    allow_writes: bool

    @classmethod
    def from_env(cls) -> Config:
        """Build config from the environment.

        ``REVOLUT_MERCHANT_SECRET_KEY`` is required. ``REVOLUT_SANDBOX`` defaults
        to true — you must opt *in* to production. ``REVOLUT_MCP_ALLOW_WRITES``
        defaults to false, so out of the box the server only exposes read tools.
        """
        secret = os.environ.get("REVOLUT_MERCHANT_SECRET_KEY", "").strip()
        if not secret:
            raise RuntimeError(
                "REVOLUT_MERCHANT_SECRET_KEY is required. Get a sandbox key from "
                "https://sandbox-business.revolut.com (Merchant API).",
            )
        sandbox = _env_bool("REVOLUT_SANDBOX", True)
        if not sandbox and not _env_bool("REVOLUT_I_UNDERSTAND_PRODUCTION", False):
            raise RuntimeError(
                "Refusing to start against PRODUCTION. Set "
                "REVOLUT_I_UNDERSTAND_PRODUCTION=true to override (this server can "
                "create live customers/orders/subscriptions when writes are enabled).",
            )
        return cls(
            secret_key=secret,
            api_version=os.environ.get("REVOLUT_API_VERSION", DEFAULT_API_VERSION),
            sandbox=sandbox,
            allow_writes=_env_bool("REVOLUT_MCP_ALLOW_WRITES", False),
        )
