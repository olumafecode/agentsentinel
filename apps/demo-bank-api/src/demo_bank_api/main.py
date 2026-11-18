"""HTTP interface of the demo bank (US-16).

Every tool call must carry a gateway-signed execution token bound to that exact
call (ADR-001, ADR-010). A call without one is refused with HTTP 403, so the only
way to use a bank tool is through the Sentinel Gateway.

Run with:  uvicorn demo_bank_api.main:create_app --factory --port 8001
"""

import hmac
import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from demo_bank_api import __version__
from demo_bank_api.config import Settings
from demo_bank_api.store import BankError, BankStore
from demo_bank_api.tools import TOOLS
from sentinel_contracts import (
    TOKEN_HEADER,
    OwnershipAnswer,
    OwnershipQuery,
    ReplayGuard,
    TokenClaims,
    TokenError,
    verify_token,
)
from sentinel_contracts.ownership import OWNERSHIP_PATH, OWNERSHIP_TOOL

MAX_BODY_BYTES = 64 * 1024

log = logging.getLogger("demo_bank_api")


class RequestError(BankError):
    """A request the bank refuses before running any tool."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(code, message)
        self.status_code = status_code
        self.details = details


def create_app(
    settings: Settings | None = None,
    *,
    store: BankStore | None = None,
    clock: Callable[[], float] = time.time,
) -> FastAPI:
    """Build the bank. Reads settings from the environment when none are given."""
    settings = settings or Settings.from_env()
    store = store or BankStore(seed=settings.seed)
    replay_guard = ReplayGuard(clock=clock)

    app = FastAPI(
        title="AgentSentinel demo bank API",
        version=__version__,
        description="Synthetic bank tools. Every tool call needs a gateway execution token.",
    )

    @app.exception_handler(BankError)
    async def bank_error(_: Request, exc: BankError) -> JSONResponse:
        error: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.details:
            error["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content={"error": error})

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        """Liveness: the process is running."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    def readyz() -> dict[str, Any]:
        """Readiness: the bank data is loaded and the service can take calls."""
        return {"status": "ready", "seed": store.seed, **store.counts()}

    @app.get("/v1/tools", tags=["tools"])
    def list_tools() -> dict[str, Any]:
        """Describe every tool and its arguments. Needs no token: it holds no customer data."""
        return {"tools": [spec.catalogue_entry() for spec in TOOLS.values()]}

    def authorize(tool_name: str, token: str, arguments: dict[str, Any]) -> TokenClaims:
        """Accept a call only with an unused gateway token for exactly this call."""
        try:
            claims = verify_token(
                token,
                key=settings.execution_token_key,
                audience=settings.audience,
                tool_name=tool_name,
                arguments=arguments,
                now=clock(),
            )
            replay_guard.consume(claims)
        except TokenError as exc:
            log.warning("refused %s: %s", tool_name, exc.code)
            raise RequestError(403, exc.code, str(exc)) from exc
        return claims

    @app.post("/v1/tools/{tool_name}", tags=["tools"])
    async def call_tool(tool_name: str, request: Request) -> dict[str, Any]:
        """Run one tool. The JSON body holds the tool's arguments."""
        token = _require_token(request, tool_name)
        spec = TOOLS.get(tool_name)
        if spec is None:
            raise RequestError(
                404, "unknown_tool", f"there is no tool called {tool_name}"
            )

        arguments = _read_arguments(await request.body())
        claims = authorize(tool_name, token, arguments)
        parsed = _validate(spec.arguments_model, arguments, tool_name)
        now = datetime.fromtimestamp(clock(), tz=UTC)
        result = spec.run(store, parsed, now)
        log.info("ran %s for correlation %s", tool_name, claims.correlation_id)
        return {
            "tool_name": tool_name,
            "correlation_id": claims.correlation_id,
            "result": result,
        }

    @app.post(OWNERSHIP_PATH, tags=["internal"])
    async def resolve_owners(request: Request) -> dict[str, Any]:
        """Say which customer owns each account, transaction or dispute (US-01.1).

        For the gateway only: it needs an execution token issued for resolve_owners.
        The body is ``{"identifiers": [...]}``; unknown records map to null.
        """
        token = _require_token(request, OWNERSHIP_TOOL)
        arguments = _read_arguments(await request.body())
        authorize(OWNERSHIP_TOOL, token, arguments)
        query = _validate(OwnershipQuery, arguments, OWNERSHIP_TOOL)
        answer = OwnershipAnswer(owners=store.owners(query.identifiers))
        return answer.model_dump(mode="json")

    @app.post("/admin/reset", tags=["admin"])
    def reset_bank(
        x_admin_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """Return the bank to its seeded state. Needs the DEMO_ADMIN_KEY value."""
        if settings.admin_key is None:
            raise RequestError(
                404, "not_found", "reset is disabled; DEMO_ADMIN_KEY is not set"
            )
        if x_admin_key is None or not hmac.compare_digest(
            x_admin_key.encode("utf-8"), settings.admin_key.encode("utf-8")
        ):
            raise RequestError(
                403, "invalid_admin_key", "the admin key is missing or wrong"
            )
        checksum = store.reset()
        log.info("bank reset to seed %s", store.seed)
        return {"status": "reset", "seed": store.seed, "checksum": checksum}

    return app


def _require_token(request: Request, tool_name: str) -> str:
    token = request.headers.get(TOKEN_HEADER)
    if not token:
        log.warning("refused %s: no execution token", tool_name)
        raise RequestError(
            403, "missing_token", "a gateway execution token is required"
        )
    return token


def _validate[M: BaseModel](
    model: type[M], arguments: dict[str, Any], tool_name: str
) -> M:
    try:
        return model.model_validate(arguments)
    except ValidationError as exc:
        raise RequestError(
            422,
            "invalid_arguments",
            f"the arguments for {tool_name} are not valid",
            exc.errors(include_url=False, include_context=False, include_input=False),
        ) from exc


def _read_arguments(body: bytes) -> dict[str, Any]:
    if len(body) > MAX_BODY_BYTES:
        raise RequestError(413, "body_too_large", "the request body is too large")
    try:
        arguments = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestError(
            400, "invalid_json", "the request body must be JSON"
        ) from exc
    if not isinstance(arguments, dict):
        raise RequestError(
            400, "invalid_json", "the request body must be a JSON object"
        )
    return arguments
