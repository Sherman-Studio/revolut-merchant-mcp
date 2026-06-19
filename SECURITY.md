# Security Policy

`revolut-merchant-mcp` talks to a payments API, so we take security reports
seriously and ask that you disclose responsibly.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting:

1. Go to the **Security** tab of this repository.
2. Click **Report a vulnerability**.
3. Describe the issue, affected versions, and reproduction steps.

We aim to acknowledge reports within **3 working days** and to provide a
remediation timeline after triage. We'll credit you in the release notes unless
you'd prefer to remain anonymous.

## Scope

In scope:

- Leakage or mishandling of the Revolut Merchant secret key.
- Requests sent to the wrong host (sandbox key reaching production or vice
  versa), or the production/write guards being bypassable.
- Injection or SSRF via tool arguments reaching the HTTP layer.

Out of scope:

- Vulnerabilities in the Revolut API itself — report those to Revolut.
- Issues that require an attacker to already control your MCP client config or
  environment variables (that's where your secret lives).

## Handling credentials safely

- The server reads your Merchant secret from `REVOLUT_MERCHANT_SECRET_KEY`. Treat
  it like any payment credential and prefer a **sandbox** key for anything
  agent-driven.
- The server is **sandbox-first** (production requires an explicit
  acknowledgement flag) and **read-only by default** (write tools require
  `REVOLUT_MCP_ALLOW_WRITES=true`). Leave both at their defaults unless you have a
  specific reason not to.

## Supported versions

This is pre-1.0 software; only the latest release on `main` receives security
fixes.
