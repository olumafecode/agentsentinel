"""Least privilege: which tools an agent may use, and whose data (US-01, FR-03).

Both checks are hard rules. They run only after the context checks have passed, so
the session, the agent and the tool are all known and trusted here.

ToolAllowlistCheck   The tool must be one the agent may use, for the task the
                     customer asked for (US-01.2). Moves into OPA in US-02a.
CustomerScopeCheck   Every customer, account, transaction or dispute the action
                     names must belong to the signed-in customer (US-01.1).
"""

import re
from collections.abc import Collection, Iterator, Mapping, Sequence
from enum import StrEnum
from typing import Any, Protocol, get_args

from sentinel_contracts import Decision, ProtectedActionRequest, ReasonCode
from sentinel_contracts.identifiers import (
    AccountId,
    CustomerId,
    DisputeId,
    TransactionId,
)
from sentinel_contracts.ownership import MAX_OWNERSHIP_QUERY
from sentinel_gateway.checks import (
    NO_OBJECTION,
    ActionContext,
    Check,
    CheckRecord,
    Finding,
    Stage,
    objection,
)

_HARD_STOPS = (Decision.BLOCK, Decision.QUARANTINE)


class RecordKind(StrEnum):
    CUSTOMER = "customer"
    ACCOUNT = "account"
    TRANSACTION = "transaction"
    DISPUTE = "dispute"


RECORD_PATTERNS: Mapping[RecordKind, re.Pattern[str]] = {
    kind: re.compile(get_args(format_)[1].pattern)
    for kind, format_ in (
        (RecordKind.CUSTOMER, CustomerId),
        (RecordKind.ACCOUNT, AccountId),
        (RecordKind.TRANSACTION, TransactionId),
        (RecordKind.DISPUTE, DisputeId),
    )
}
"""The identifier formats that point at one customer's data, from sentinel_contracts."""


class OwnershipLookup(Protocol):
    """Says which customer owns each account, transaction or dispute."""

    def owners(
        self, request: ProtectedActionRequest, identifiers: Collection[str]
    ) -> Mapping[str, str | None]:
        """Return the owning customer ID of each record, or None for an unknown one."""
        ...


class ToolAllowlistCheck(Check):
    """The agent may use the tool, and the tool fits the customer's task (US-01.2)."""

    name = "tool_allowlist"
    stage = Stage.HARD_RULE

    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        agent, tool, task = context.agent, context.tool, context.request.task_type
        tool_name = context.request.tool_name
        for_agent = agent is not None and tool_name in agent.allowed_tools
        for_task = tool is not None and task in tool.allowed_task_types
        if for_agent and for_task:
            return NO_OBJECTION

        problems = []
        if not for_agent:
            agent_name = agent.name if agent is not None else "This agent"
            problems.append(f"{agent_name} is not allowed to use {tool_name}")
        if not for_task:
            problems.append(f"{tool_name} is not allowed for {task.value} tasks")
        return objection(
            Decision.BLOCK,
            ReasonCode.TOOL_NOT_ALLOWED,
            summary=f"{', and '.join(problems)}.",
            allowed_for_agent=for_agent,
            allowed_for_task=for_task,
        )


class CustomerScopeCheck(Check):
    """Every record the action names must belong to the signed-in customer (US-01.1).

    Any argument value that is a customer, account, transaction or dispute ID counts,
    whatever the argument is called and however deeply it is nested. Customer IDs are
    compared with the session's customer directly. For the other records the bank is
    asked who owns them; a record the bank does not know is treated as out of scope,
    and a lookup that fails blocks the action.

    The lookup is skipped when an earlier check has already blocked the action, so a
    refused action does not make the gateway call the bank at all.
    """

    name = "customer_scope"
    stage = Stage.HARD_RULE

    def __init__(self, ownership: OwnershipLookup) -> None:
        self._ownership = ownership

    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        request = context.request
        customer = request.customer_scope
        named = referenced_records(request.arguments)
        outside = {
            record: record
            for record in named.get(RecordKind.CUSTOMER, set())
            if record != customer
        }
        records = set().union(
            *(ids for kind, ids in named.items() if kind is not RecordKind.CUSTOMER)
        )

        if len(records) > MAX_OWNERSHIP_QUERY:
            return objection(
                Decision.BLOCK,
                ReasonCode.INVALID_ARGUMENTS,
                summary="The action names more records than the gateway can check "
                f"(the limit is {MAX_OWNERSHIP_QUERY}).",
                records=len(records),
            )

        unknown: list[str] = []
        stopped = any(r.finding.decision in _HARD_STOPS for r in earlier)
        if records and not stopped:
            owners = self._ownership.owners(request, records)
            for record in sorted(records):
                owner = owners.get(record)
                if owner is None:
                    unknown.append(record)
                elif owner != customer:
                    outside[record] = owner

        if outside or unknown:
            return objection(
                Decision.BLOCK,
                ReasonCode.OUTSIDE_CUSTOMER_SCOPE,
                summary="The action refers to data that does not belong to the "
                f"signed-in customer ({_first_few(sorted([*outside, *unknown]))}).",
                outside_scope=dict(sorted(outside.items())),
                unknown=unknown,
            )
        if records and stopped:
            return Finding(details={"ownership_not_checked": sorted(records)})
        return NO_OBJECTION


def referenced_records(arguments: Mapping[str, Any]) -> dict[RecordKind, set[str]]:
    """Every customer, account, transaction and dispute ID among the argument values."""
    found: dict[RecordKind, set[str]] = {}
    for text in _strings(arguments):
        for kind, pattern in RECORD_PATTERNS.items():
            if pattern.fullmatch(text):
                found.setdefault(kind, set()).add(text)
    return found


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from _strings(key)
            yield from _strings(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _strings(item)


def _first_few(identifiers: Sequence[str], limit: int = 3) -> str:
    shown = ", ".join(identifiers[:limit])
    hidden = len(identifiers) - limit
    return f"{shown} and {hidden} more" if hidden > 0 else shown
