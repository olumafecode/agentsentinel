"""Everything the gateway sends to the demo bank.

- ``BankClient.execute`` forwards an allowed action (US-18.4). It never raises:
  whatever happens at the bank comes back as an ExecutionResult.
- ``BankOwnershipLookup`` asks which customer owns the records an action names
  (US-01.1, ADR-013). It raises BankLookupError when the bank cannot say, so the
  check that asked fails closed.

Every request carries an execution token for exactly that request in
X-Execution-Token. The body is the canonical JSON the token's argument hash was
computed from.
"""

import time
from collections.abc import Callable, Collection, Mapping
from datetime import UTC, datetime
from typing import Any

import httpx2
from pydantic import ValidationError

from sentinel_contracts import (
    TOKEN_HEADER,
    ExecutionError,
    ExecutionResult,
    ExecutionStatus,
    OwnershipAnswer,
    OwnershipQuery,
    ProtectedActionRequest,
    issue_token,
)
from sentinel_contracts.ownership import OWNERSHIP_PATH, OWNERSHIP_TOOL
from sentinel_contracts.signing import canonical_json

DEFAULT_TIMEOUT_SECONDS = 5.0


class BankLookupError(Exception):
    """The bank could not say who owns the records asked about."""


class BankClient:
    """Calls the bank. Pass ``client`` to use a test client."""

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
            response = self._post(f"/v1/tools/{tool_name}", dict(arguments), token)
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

    def owners(self, query: OwnershipQuery, token: str) -> dict[str, str | None]:
        """Ask who owns each record in ``query``. Raises BankLookupError if the bank cannot say."""
        try:
            response = self._post(OWNERSHIP_PATH, query.model_dump(mode="json"), token)
        except httpx2.HTTPError as exc:
            raise BankLookupError("the bank could not be reached") from exc
        if response.status_code != 200:
            raise BankLookupError(
                f"the bank answered the lookup with HTTP {response.status_code}"
            )
        try:
            answer = OwnershipAnswer.model_validate_json(response.content)
        except ValidationError as exc:
            raise BankLookupError("the bank's answer could not be read") from exc
        if set(answer.owners) != set(query.identifiers):
            raise BankLookupError("the bank did not answer for every record")
        return dict(answer.owners)

    def close(self) -> None:
        """Close the connection pool, unless the client was passed in."""
        if self._owns_client:
            self._client.close()

    def _post(self, path: str, body: Any, token: str) -> httpx2.Response:
        return self._client.post(
            f"{self._base_url}{path}",
            content=canonical_json(body),
            headers={"Content-Type": "application/json", TOKEN_HEADER: token},
        )

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


class BankOwnershipLookup:
    """Asks the bank who owns records, with a single-use token for each lookup.

    The token is bound to the action's correlation ID and customer, like the token
    for the action itself, so the lookup appears in the same trail.
    """

    def __init__(
        self,
        bank: BankClient,
        *,
        key: bytes,
        audience: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._bank = bank
        self._key = key
        self._audience = audience
        self._clock = clock

    def owners(
        self, request: ProtectedActionRequest, identifiers: Collection[str]
    ) -> dict[str, str | None]:
        query = OwnershipQuery(identifiers=sorted(identifiers))
        token = issue_token(
            key=self._key,
            correlation_id=request.correlation_id,
            tool_name=OWNERSHIP_TOOL,
            arguments=query.model_dump(mode="json"),
            customer_scope=request.customer_scope,
            audience=self._audience,
            now=self._clock(),
        )
        return self._bank.owners(query, token)


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
