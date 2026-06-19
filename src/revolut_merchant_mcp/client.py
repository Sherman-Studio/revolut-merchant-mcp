"""Thin async transport client for the Revolut Merchant API.

There is no official Revolut Python SDK, so this is the one place that knows how
to *talk* to Revolut: base-URL selection (sandbox vs production), the
``Authorization`` / ``Revolut-Api-Version`` headers, idempotency keys, retry with
backoff on transient failures, and turning non-2xx responses into a single
``RevolutAPIError``.

It deliberately knows nothing about customers, orders, or subscriptions — the
``operations`` module builds typed calls on top of this. Keeping the layers split
means the transport concerns (auth, retries, versioning) are unit-tested once,
here, with mocked HTTP and no live keys.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

# Public Merchant API hosts. Sandbox and production are entirely separate
# accounts with separate keys (a sandbox key will 401 against production).
SANDBOX_BASE = "https://sandbox-merchant.revolut.com/api"
PRODUCTION_BASE = "https://merchant.revolut.com/api"

# Status codes worth retrying: Revolut rate-limit + transient server errors.
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class RevolutAPIError(Exception):
    """A non-2xx Revolut response, or a transport failure after all retries.

    ``status_code`` is None for transport-level failures (DNS, connect, read
    timeout). ``code`` / ``message`` are pulled from Revolut's JSON error body
    when present.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        payload: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.payload = payload or {}
        super().__init__(message)


class RevolutClient:
    def __init__(
        self,
        *,
        secret_key: str,
        api_version: str,
        sandbox: bool = True,
        timeout: float = 30.0,
        max_retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        if not secret_key:
            raise ValueError("RevolutClient requires a secret_key")
        self._secret_key = secret_key
        self._api_version = api_version
        self._base_url = SANDBOX_BASE if sandbox else PRODUCTION_BASE
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        return self._base_url

    def _headers(self, idempotency_key: str | None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "Revolut-Api-Version": self._api_version,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            # Revolut dedupes retried writes by this header, so a network retry
            # of e.g. "create order" can't double-charge.
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        """Make an API call and return the parsed JSON body (``{}`` for an empty
        2xx). Raises ``RevolutAPIError`` on a non-2xx response or after
        exhausting retries on transient failures."""
        client = self._get_client()
        headers = self._headers(idempotency_key)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                resp = await client.request(
                    method, path, json=json, params=params, headers=headers,
                )
            except httpx.TransportError as exc:
                # DNS/connect/read failures — retry, then give up.
                last_exc = exc
                if attempt < self._max_retries:
                    await self._sleep(attempt)
                    continue
                raise RevolutAPIError(
                    f"Revolut transport error after {attempt + 1} attempts: {exc}",
                ) from exc

            if resp.status_code in _RETRY_STATUSES and attempt < self._max_retries:
                logger.warning(
                    "Revolut %s %s -> %s, retrying (attempt %s)",
                    method, path, resp.status_code, attempt + 1,
                )
                await self._sleep(attempt)
                continue

            return self._handle_response(resp)

        raise RevolutAPIError(  # pragma: no cover - defensive
            f"Revolut request failed: {last_exc}",
        )

    async def get(self, path: str, *, params: dict | None = None) -> dict:
        return await self.request("GET", path, params=params)

    async def post(
        self, path: str, *, json: dict | None = None, idempotency_key: str | None = None,
    ) -> dict:
        return await self.request("POST", path, json=json, idempotency_key=idempotency_key)

    async def patch(
        self, path: str, *, json: dict | None = None, idempotency_key: str | None = None,
    ) -> dict:
        return await self.request("PATCH", path, json=json, idempotency_key=idempotency_key)

    async def delete(self, path: str) -> dict:
        return await self.request("DELETE", path)

    def _handle_response(self, resp: httpx.Response) -> dict:
        if 200 <= resp.status_code < 300:
            if not resp.content:
                return {}
            try:
                body = resp.json()
            except ValueError:
                return {}
            # Wrap a bare list defensively so callers get a predictable dict.
            return body if isinstance(body, dict) else {"data": body}

        # Non-2xx: pull Revolut's structured error when present.
        code: str | None = None
        message = f"Revolut API error {resp.status_code}"
        payload: dict = {}
        try:
            payload = resp.json()
            if isinstance(payload, dict):
                code = payload.get("code") or payload.get("error")
                message = payload.get("message") or payload.get("description") or message
        except ValueError:
            payload = {}
        raise RevolutAPIError(
            message,
            status_code=resp.status_code,
            code=str(code) if code is not None else None,
            payload=payload,
        )

    async def _sleep(self, attempt: int) -> None:
        # Exponential backoff; ``backoff_base=0`` in tests makes this a no-op.
        delay = self._backoff_base * (2**attempt)
        if delay:
            await asyncio.sleep(delay)
