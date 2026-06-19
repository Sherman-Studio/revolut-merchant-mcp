"""Revolut Merchant API MCP server.

An open-source Model Context Protocol server exposing the Revolut **Merchant**
API (customers, orders, subscriptions, plans) to MCP-aware AI assistants.
"""

from .client import RevolutAPIError, RevolutClient
from .config import Config

__version__ = "0.1.0"

__all__ = ["RevolutAPIError", "RevolutClient", "Config", "__version__"]
