"""HTTP interface of the Sentinel Gateway (US-18.2).

POST /v1/actions/evaluate is the only way an agent's action reaches a bank tool. The
agent proves who it is with its API key and sends the customer's session token; the
gateway decides, and forwards an allowed action to the bank with a single-use
execution token (ADR-001, ADR-010, ADR-012).

Run with:  uvicorn sentinel_gateway.main:create_app --factory --port 8000
"""

import json
import logging
import time
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager
from typing import Any, NoReturn

import httpx2
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from sentinel_contracts import SESSION_HEADER, ActionOutcome, ProtectedActionRequest
from sentinel_gateway import __version__
from sentinel_gateway.audit import AuditSink, AuditUnavailable, JsonLinesAuditSink
from sentinel_gateway.auth import AgentKeyring, bearer_credentials
from sentinel_gateway.bank import BankClient
from sentinel_gateway.checks import Check, default_checks
from sentinel_gateway.config import ConfigError, Settings
from sentinel_gateway.decisions import CorrelationConflict, DecisionStore
from sentinel_gateway.orchestrator import Orchestrator
from sentinel_gateway.registry import AgentRegistry, ToolRegistry
from sentinel_gateway.service import ApprovalRequester, Gateway

MAX_BODY_BYTES = 64 * 1024
CORRELATION_HEADER = "X-Correlation-ID"
REPLAY_HEADER = "X-Idempotent-Replay"

log = logging.getLogger("sentinel_gateway")


class GatewayError(Exception):
    """A request the gateway refuses before it can evaluate the action."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


def create_app(
    settings: Settings | None = None,
    *,
    agents: AgentRegistry | None = None,
    tools: ToolRegistry | None = None,
    checks: Iterable[Check] | None = None,
    bank_client: httpx2.Client | None = None,
    audit: AuditSink | None = None,
    approvals: ApprovalRequester | None = None,
    clock: Callable[[], float] = time.time,
) -> FastAPI:
    """Build the gateway. Reads settings from the environment when none are given."""
    settings = settings or Settings.from_env()
    agents = AgentRegistry.load() if agents is None else agents
    tools = ToolRegistry.load() if tools is None else tools
    unregistered = settings.agent_keys.agent_ids - agents.ids()
    if unregistered:
        raise ConfigError(
            f"AGENT_KEYS has keys for agents that are not registered: {sorted(unregistered)}"
        )

    orchestrator = Orchestrator(default_checks() if checks is None else checks)
    bank = BankClient(
        settings.bank_url,
        timeout_seconds=settings.bank_timeout_seconds,
        client=bank_client,
        clock=clock,
    )
    gateway = Gateway(
        settings=settings,
        agents=agents,
        tools=tools,
        orchestrator=orchestrator,
        decisions=DecisionStore(clock=clock),
        bank=bank,
        audit=JsonLinesAuditSink() if audit is None else audit,
        approvals=approvals,
        clock=clock,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        bank.close()

    app = FastAPI(
        title="AgentSentinel Sentinel Gateway",
        version=__version__,
        description="Every protected action an agent proposes is decided here first.",
        lifespan=lifespan,
    )

    @app.exception_handler(GatewayError)
    async def gateway_error(_: Request, exc: GatewayError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message, exc.headers)

    @app.exception_handler(CorrelationConflict)
    async def correlation_conflict(
        _: Request, exc: CorrelationConflict
    ) -> JSONResponse:
        log.warning("refused a reused correlation ID %s", exc.correlation_id)
        return _error(
            409,
            "correlation_id_conflict",
            "this correlation ID was already used for a different request",
        )

    @app.exception_handler(AuditUnavailable)
    async def audit_unavailable(_: Request, exc: AuditUnavailable) -> JSONResponse:
        log.error("action refused because the audit trail is unavailable: %s", exc)
        return _error(
            503,
            "audit_unavailable",
            "the action was not evaluated because it could not be audited; try again",
        )

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        """Liveness: the process is running."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    def readyz() -> dict[str, Any]:
        """Readiness: the registries are loaded and the gateway can take actions."""
        return {
            "status": "ready",
            "agents": len(agents),
            "tools": len(tools),
            "checks": [check.name for check in orchestrator.checks],
        }

    @app.post(
        "/v1/actions/evaluate",
        tags=["actions"],
        response_model=ActionOutcome,
        openapi_extra=_EVALUATE_DOCS,
        responses={
            400: {"description": "The body is not a JSON object"},
            401: {"description": "The agent key is missing or wrong"},
            409: {"description": "The correlation ID was used for a different request"},
            413: {"description": "The body is larger than 64 KB"},
            503: {"description": "The audit trail is unavailable; nothing was run"},
        },
    )
    async def evaluate(request: Request) -> JSONResponse:
        """Decide on one proposed action and, if it is allowed, run it at the bank.

        Every action that can be read gets a decision, including a malformed one, which
        is blocked. The response holds the decision and, for ALLOW, the bank's result.
        """
        agent_id = _authenticate(
            request.headers.get("Authorization"), settings.agent_keys
        )
        _check_length(request.headers.get("Content-Length"))
        body = _read_body(await request.body())
        evaluation = await run_in_threadpool(
            gateway.evaluate,
            body,
            agent_id=agent_id,
            session_token=request.headers.get(SESSION_HEADER),
        )
        headers = {CORRELATION_HEADER: evaluation.correlation_id}
        if evaluation.replayed:
            headers[REPLAY_HEADER] = "true"
        return JSONResponse(evaluation.outcome.model_dump(mode="json"), headers=headers)

    _document_request(app)
    return app


_EVALUATE_DOCS: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ProtectedActionRequest"}
            }
        },
    },
    "parameters": [
        {
            "name": SESSION_HEADER,
            "in": "header",
            "required": False,
            "description": "Signed customer session token. Without one the action is blocked.",
            "schema": {"type": "string"},
        }
    ],
    "security": [{"AgentKey": []}],
}


def _document_request(app: FastAPI) -> None:
    """Add the request schema and the agent key scheme to /docs.

    The endpoint reads its body itself, so that a malformed action is still decided
    and audited instead of being turned away by the framework, which means FastAPI
    cannot describe the body on its own.
    """
    build = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = build()
            request_schema = ProtectedActionRequest.model_json_schema(
                ref_template="#/components/schemas/{model}"
            )
            components = schema.setdefault("components", {})
            schemas = components.setdefault("schemas", {})
            for name, definition in request_schema.pop("$defs", {}).items():
                schemas.setdefault(name, definition)
            schemas["ProtectedActionRequest"] = request_schema
            components["securitySchemes"] = {
                "AgentKey": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "The agent's API key from AGENT_KEYS",
                }
            }
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]


def _authenticate(authorization: str | None, keyring: AgentKeyring) -> str:
    presented = bearer_credentials(authorization)
    challenge = {"WWW-Authenticate": "Bearer"}
    if presented is None:
        raise GatewayError(
            401, "missing_agent_key", "an agent API key is required", challenge
        )
    agent_id = keyring.authenticate(presented)
    if agent_id is None:
        log.warning("refused a request with an unknown agent key")
        raise GatewayError(
            401, "invalid_agent_key", "the agent API key is not valid", challenge
        )
    return agent_id


def _check_length(content_length: str | None) -> None:
    if (
        content_length
        and content_length.isdigit()
        and int(content_length) > MAX_BODY_BYTES
    ):
        _too_large()


def _read_body(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_BODY_BYTES:
        _too_large()
    try:
        body = json.loads(raw, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise GatewayError(
            400, "invalid_json", "the request body must be JSON"
        ) from exc
    if not isinstance(body, dict):
        raise GatewayError(
            400, "invalid_json", "the request body must be a JSON object"
        )
    return body


def _reject_constant(name: str) -> NoReturn:
    raise ValueError(f"{name} is not valid JSON")


def _too_large() -> NoReturn:
    raise GatewayError(413, "body_too_large", "the request body is larger than 64 KB")


def _error(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )
