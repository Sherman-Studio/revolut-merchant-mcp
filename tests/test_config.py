"""Config tests — required key, sandbox default, production guard, write flag."""

from __future__ import annotations

import pytest

from revolut_merchant_mcp.config import DEFAULT_API_VERSION, Config


def test_requires_secret_key(monkeypatch):
    monkeypatch.delenv("REVOLUT_MERCHANT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="REVOLUT_MERCHANT_SECRET_KEY"):
        Config.from_env()


def test_defaults_sandbox_and_read_only(monkeypatch):
    monkeypatch.setenv("REVOLUT_MERCHANT_SECRET_KEY", "sk_sandbox_x")
    monkeypatch.delenv("REVOLUT_SANDBOX", raising=False)
    monkeypatch.delenv("REVOLUT_MCP_ALLOW_WRITES", raising=False)
    cfg = Config.from_env()
    assert cfg.sandbox is True
    assert cfg.allow_writes is False
    assert cfg.api_version == DEFAULT_API_VERSION


def test_production_requires_explicit_acknowledgement(monkeypatch):
    monkeypatch.setenv("REVOLUT_MERCHANT_SECRET_KEY", "sk_live_x")
    monkeypatch.setenv("REVOLUT_SANDBOX", "false")
    monkeypatch.delenv("REVOLUT_I_UNDERSTAND_PRODUCTION", raising=False)
    with pytest.raises(RuntimeError, match="PRODUCTION"):
        Config.from_env()


def test_production_allowed_with_acknowledgement(monkeypatch):
    monkeypatch.setenv("REVOLUT_MERCHANT_SECRET_KEY", "sk_live_x")
    monkeypatch.setenv("REVOLUT_SANDBOX", "false")
    monkeypatch.setenv("REVOLUT_I_UNDERSTAND_PRODUCTION", "true")
    cfg = Config.from_env()
    assert cfg.sandbox is False


def test_allow_writes_flag(monkeypatch):
    monkeypatch.setenv("REVOLUT_MERCHANT_SECRET_KEY", "sk_sandbox_x")
    monkeypatch.setenv("REVOLUT_MCP_ALLOW_WRITES", "true")
    assert Config.from_env().allow_writes is True
