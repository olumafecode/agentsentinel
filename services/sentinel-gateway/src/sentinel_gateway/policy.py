"""The bank's policy, decided by Open Policy Agent (US-02a, ADR-002, ADR-015).

PolicyCheck sends each action, with its agent and tool, to OPA and turns OPA's answer
into a finding. The rules themselves are Rego in ``policies/opa``: which tools each
task allows, the ban on bulk export, and the refund amount rules. OPA answers with
every rule the action breaks; the check asks for the strongest decision among them and
records the rules and the policy bundle's version, so an audited decision shows what
it was judged against.

OpaClient raises PolicyUnavailable when OPA cannot answer, or answers with something
the gateway cannot trust, such as a policy without a version. The orchestrator then
blocks the action with DEPENDENCY_UNAVAILABLE and logs the fault (AT-12).
"""

from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal, Protocol

import httpx2
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from sentinel_contracts import Decision, ReasonCode
from sentinel_contracts.actions import Summary
from sentinel_contracts.identifiers import SemVer
from sentinel_gateway.checks import ActionContext, Check, CheckRecord, Finding, Stage

DECISION_PATH = "/v1/data/agentsentinel/gateway/decision"
"""Where OPA serves the gateway's decision document (policies/opa/agentsentinel/gateway)."""
DEFAULT_TIMEOUT_SECONDS = 2.0

_RANK = {Decision.HUMAN_REVIEW: 1, Decision.BLOCK: 2}
_REASON_ORDER = (
    ReasonCode.MISSING_CONTEXT,
    ReasonCode.POLICY_DENY,
    ReasonCode.TOOL_NOT_ALLOWED,
    ReasonCode.INVALID_ARGUMENTS,
    ReasonCode.REFUND_OVER_LIMIT,
)
"""Which reason leads when several rules match. Reasons not listed come after these."""


class PolicyUnavailable(Exception):
    """OPA could not give a decision the gateway can use."""


class _Answer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Violation(_Answer):
    """One bank rule the action breaks, as the policy reports it."""

    rule: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{2,60}$")]
    decision: Literal[Decision.BLOCK, Decision.HUMAN_REVIEW]
    reason: ReasonCode
    message: Summary


class PolicyAnswer(_Answer):
    """What the policy says about one action, and the bundle version that said it."""

    version: SemVer
    violations: tuple[Violation, ...] = Field(max_length=50)


class PolicyEngine(Protocol):
    """Judges an action against the bank's policy. OpaClient in production."""

    def evaluate(self, document: Mapping[str, Any]) -> PolicyAnswer:
        """Return every rule ``document`` breaks. Raise PolicyUnavailable if unsure."""
        ...

    def ready(self) -> bool:
        """True when the policy is loaded and answering."""
        ...


class _DecisionDocument(_Answer):
    violations: tuple[Violation, ...] = Field(max_length=50)


class _BundleInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    revision: SemVer


class _Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    bundles: dict[str, _BundleInfo] = Field(min_length=1, max_length=1)


class _DataResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: _DecisionDocument
    provenance: _Provenance


class OpaClient:
    """Asks a running OPA server for the gateway's decision document.

    OPA must serve ``policies/opa`` as a bundle (``opa run --server --bundle``), so
    that it reports the bundle's revision, which becomes the decision's
    policy_version. Pass ``client`` to use a test client.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx2.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx2.Client(
            timeout=httpx2.Timeout(timeout_seconds), follow_redirects=False
        )

    def evaluate(self, document: Mapping[str, Any]) -> PolicyAnswer:
        try:
            response = self._client.post(
                f"{self._base_url}{DECISION_PATH}",
                params={"provenance": "true"},
                json={"input": dict(document)},
            )
        except httpx2.TimeoutException as exc:
            raise PolicyUnavailable("OPA did not answer in time") from exc
        except httpx2.HTTPError as exc:
            raise PolicyUnavailable("OPA could not be reached") from exc
        if response.status_code != 200:
            raise PolicyUnavailable(f"OPA answered with HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise PolicyUnavailable("OPA's answer is not JSON") from exc
        if not isinstance(body, dict) or "result" not in body:
            raise PolicyUnavailable("the gateway policy is not loaded in OPA")
        try:
            answer = _DataResponse.model_validate(body)
        except ValidationError as exc:
            raise PolicyUnavailable(
                "OPA's answer has no valid policy version or violations"
            ) from exc
        (bundle,) = answer.provenance.bundles.values()
        return PolicyAnswer(
            version=bundle.revision, violations=answer.result.violations
        )

    def ready(self) -> bool:
        try:
            response = self._client.get(
                f"{self._base_url}/health", params={"bundles": "true"}
            )
        except httpx2.HTTPError:
            return False
        return response.status_code == 200

    def close(self) -> None:
        """Close the connection pool, unless the client was passed in."""
        if self._owns_client:
            self._client.close()


class PolicyCheck(Check):
    """The action keeps to the bank's policy in OPA (US-02a, FR-03, FR-04, FR-06)."""

    name = "bank_policy"
    stage = Stage.HARD_RULE

    def __init__(self, engine: PolicyEngine) -> None:
        self._engine = engine

    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        answer = self._engine.evaluate(policy_input(context))
        ordered = sorted(answer.violations, key=_precedence)
        details = {"matched_rules": [violation.rule for violation in ordered]}
        if not ordered:
            return Finding(policy_version=answer.version, details=details)
        strongest = ordered[0]
        return Finding(
            decision=strongest.decision,
            reasons=tuple(dict.fromkeys(violation.reason for violation in ordered)),
            summary=strongest.message,
            policy_version=answer.version,
            details=details,
        )


def policy_input(context: ActionContext) -> dict[str, Any]:
    """The input document the policy reads, as described in policies/opa/README.md."""
    agent, tool, request = context.agent, context.tool, context.request
    if agent is None or tool is None:
        raise ValueError("the policy needs a registered agent and a known tool")
    return {
        "agent": {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "allowed_tools": list(agent.allowed_tools),
        },
        "tool": {
            "tool_name": tool.tool_name,
            "category": tool.category.value,
            "high_impact": tool.high_impact,
            "sensitive_parameters": list(tool.sensitive_parameters),
        },
        "action": {
            "task_type": request.task_type.value,
            "tool_name": request.tool_name,
            "customer_scope": request.customer_scope,
            "arguments": dict(request.arguments),
            "provenance_labels": {
                name: label.value for name, label in request.provenance_labels.items()
            },
        },
    }


def _precedence(violation: Violation) -> tuple[int, int, str]:
    reason = violation.reason
    order = (
        _REASON_ORDER.index(reason) if reason in _REASON_ORDER else len(_REASON_ORDER)
    )
    return (-_RANK[violation.decision], order, violation.rule)
