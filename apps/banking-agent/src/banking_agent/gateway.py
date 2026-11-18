"""Vera's client for the Sentinel Gateway (US-17.1).

Every action goes to ``POST /v1/actions/evaluate`` with Vera's agent key and the
customer's session token. A call that fails to arrive, or arrives while the gateway
cannot audit it (HTTP 503), is sent again unchanged. That is safe: the gateway
answers a repeated correlation ID with the stored outcome and never runs the action
twice (US-18.5).
"""

import time
from collections.abc import Callable

import httpx2
from pydantic import ValidationError

from sentinel_contracts import SESSION_HEADER, ActionOutcome, ProtectedActionRequest

EVALUATE_PATH = "/v1/actions/evaluate"


class GatewayError(Exception):
    """The gateway gave no decision."""

    def __init__(self, code: str, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class GatewayUnavailable(GatewayError):
    """The gateway could not be reached or could not audit the action. Try later."""


class GatewayRefused(GatewayError):
    """The gateway refused the request itself, for example because the agent key is wrong."""


class GatewayClient:
    def __init__(
        self,
        base_url: str,
        agent_key: str,
        *,
        timeout_seconds: float = 15.0,
        retries: int = 2,
        retry_delay_seconds: float = 0.5,
        client: httpx2.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._url = base_url.rstrip("/") + EVALUATE_PATH
        self._agent_key = agent_key
        self._retries = retries
        self._retry_delay = retry_delay_seconds
        self._owns_client = client is None
        self._client = client or httpx2.Client(timeout=httpx2.Timeout(timeout_seconds))
        self._sleep = sleep

    def evaluate(
        self, request: ProtectedActionRequest, session_token: str
    ) -> ActionOutcome:
        """Send one action and return the gateway's outcome."""
        body = request.model_dump(mode="json")
        headers = {
            "Authorization": f"Bearer {self._agent_key}",
            SESSION_HEADER: session_token,
        }
        failure = GatewayUnavailable(
            "gateway_unreachable", "the gateway did not answer"
        )
        for attempt in range(self._retries + 1):
            if attempt:
                self._sleep(self._retry_delay * attempt)
            try:
                response = self._client.post(self._url, json=body, headers=headers)
            except httpx2.HTTPError as exc:
                failure = GatewayUnavailable(
                    "gateway_unreachable", f"the gateway could not be reached: {exc}"
                )
                continue
            if response.status_code == 503:
                failure = GatewayUnavailable(*_error(response), response.status_code)
                continue
            if response.status_code != 200:
                raise GatewayRefused(*_error(response), response.status_code)
            try:
                return ActionOutcome.model_validate_json(response.content)
            except ValidationError as exc:
                raise GatewayRefused(
                    "invalid_response", "the gateway's answer could not be read"
                ) from exc
        raise failure

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def _error(response: httpx2.Response) -> tuple[str, str]:
    try:
        error = response.json()["error"]
        return str(error["code"]), str(error["message"])
    except (ValueError, KeyError, TypeError):
        return "gateway_error", f"the gateway answered with HTTP {response.status_code}"
