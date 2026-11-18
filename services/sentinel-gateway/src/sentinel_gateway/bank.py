"""Forwards allowed actions to the demo bank (US-18.4).

Each call carries the execution token for exactly that call in X-Execution-Token.
The body is the canonical JSON of the arguments, the same bytes the token's argument
hash was computed from. The client never raises: whatever happens at the bank comes
back as an ExecutionResult.
"""

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

import httpx2

from sentinel_contracts import (
    TOKEN_HEADER,
    ExecutionError,
    ExecutionResult,
    ExecutionStatus,
)
from sentinel_contracts.signing import canonical_json

DEFAULT_TIMEOUT_SECONDS = 5.0


class BankClient:
    """Calls the bank's tool endpoint. Pass ``client`` to use a test client."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx2.Client | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx2.Client(
            timeout=httpx2.Timeout(timeout_seconds), follow_redirects=False
        )
        self._clock = clock

    def execute(
        self, tool_name: str, arguments: Mapping[str, Any], token: str
    ) -> ExecutionResult:
        try:
            response = self._client.post(
                f"{self._base_url}/v1/tools/{tool_name}",
                content=canonical_json(dict(arguments)),
                headers={"Content-Type": "application/json", TOKEN_HEADER: token},
            )
        except httpx2.TimeoutException:
            return self._result(
                ExecutionStatus.FAILED,
                tool_name,
                error=("bank_timeout", "the bank did not answer in time"),
            )
        except httpx2.HTTPError:
            return self._result(
                ExecutionStatus.FAILED,
                tool_name,
                error=("bank_unreachable", "the bank could not be reached"),
            )

        status_code = response.status_code
        body = _json_body(response)
        if status_code == 200 and isinstance(body, dict) and "result" in body:
            return self._result(
                ExecutionStatus.SUCCEEDED,
                tool_name,
                http_status=status_code,
                result=body["result"],
            )
        status = (
            ExecutionStatus.REJECTED
            if 400 <= status_code < 500
            else ExecutionStatus.FAILED
        )
        return self._result(
            status,
            tool_name,
            http_status=status_code,
            error=_bank_error(body, status_code),
        )

    def close(self) -> None:
        """Close the connection pool, unless the client was passed in."""
        if self._owns_client:
            self._client.close()

    def _result(
        self,
        status: ExecutionStatus,
        tool_name: str,
        *,
        http_status: int | None = None,
        result: Any = None,
        error: tuple[str, str] | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=status,
            tool_name=tool_name,
            http_status=http_status,
            result=result,
            error=ExecutionError(code=error[0], message=error[1]) if error else None,
            completed_at=datetime.fromtimestamp(self._clock(), tz=UTC),
        )


def _json_body(response: httpx2.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _bank_error(body: Any, status_code: int) -> tuple[str, str]:
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        code, message = error.get("code"), error.get("message")
        if isinstance(code, str) and isinstance(message, str) and code and message:
            return code[:64], message[:300]
    return "bank_error", f"the bank answered with HTTP {status_code}"
