"""Scripted scenarios for the use cases, and the runner that checks them (US-17.2, US-17.3).

Each scenario is a JSON file in ``banking_agent/scenarios``: a signed-in customer, what
they say, the tool calls Vera makes in each turn, and what the gateway should decide
for each call. Vera only ever sees the calls; the expectations are for the runner.

A scenario is ``active`` when the controls it needs exist, and ``pending`` with the
story that delivers them otherwise. The runner skips pending scenarios unless asked,
because their actions may still be allowed and would change the bank. When the
story lands, set the scenario to active.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from banking_agent.agent import Conversation, Proposal, Vera
from banking_agent.identity import IdentityStandIn
from banking_agent.planning import PlannedCall, ScriptedPlanner
from sentinel_contracts import Decision, ReasonCode, TaskType
from sentinel_contracts.identifiers import CustomerId


class _Fixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Expectation(_Fixture):
    """What should happen to one scripted call.

    ``proposed: false`` means Vera must not send the call at all, for example because
    it repeats a call that was refused. Otherwise ``decision`` is required, and every
    code in ``reason_codes`` must be among the decision's reasons.
    """

    proposed: bool = True
    decision: Decision | None = None
    reason_codes: tuple[ReasonCode, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.proposed and self.decision is None:
            raise ValueError("a call Vera proposes needs an expected decision")
        if not self.proposed and (self.decision or self.reason_codes):
            raise ValueError("a call Vera must not propose has no decision")
        return self


class ScriptedCall(PlannedCall):
    expect: Expectation

    def planned(self) -> PlannedCall:
        return PlannedCall(
            tool_name=self.tool_name,
            arguments=self.arguments,
            provenance=self.provenance,
        )


class ScriptedTurn(_Fixture):
    customer: str = Field(min_length=1, description="What the customer says")
    calls: tuple[ScriptedCall, ...] = ()


class ScriptedSession(_Fixture):
    customer_id: CustomerId
    task_type: TaskType


class Scenario(_Fixture):
    id: str = Field(pattern=r"^UC-\d{2}$")
    title: str
    description: str
    status: Literal["active", "pending"]
    pending_on: str | None = Field(default=None, pattern=r"^US-\d{2}[ab]?$")
    session: ScriptedSession
    turns: tuple[ScriptedTurn, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _pending_names_its_story(self) -> Self:
        if (self.status == "pending") != (self.pending_on is not None):
            raise ValueError(
                "a pending scenario names its story in pending_on, and only then"
            )
        return self

    def messages(self) -> list[str]:
        return [turn.customer for turn in self.turns]

    def planner(self) -> ScriptedPlanner:
        return ScriptedPlanner(
            [[call.planned() for call in turn.calls] for turn in self.turns]
        )


def load_scenarios() -> list[Scenario]:
    """Every scenario that ships with Vera, in ID order."""
    folder = files("banking_agent").joinpath("scenarios")
    scenarios = [
        Scenario.model_validate(json.loads(entry.read_text(encoding="utf-8")))
        for entry in folder.iterdir()
        if entry.name.endswith(".json")
    ]
    return sorted(scenarios, key=lambda scenario: scenario.id)


@dataclass(frozen=True)
class CallResult:
    turn: int
    call: ScriptedCall
    proposal: Proposal | None
    problems: tuple[str, ...]


@dataclass
class ScenarioResult:
    scenario: Scenario
    conversation: Conversation
    calls: list[CallResult] = field(default_factory=list)

    @property
    def problems(self) -> list[str]:
        return [problem for result in self.calls for problem in result.problems]

    @property
    def status(self) -> Literal["passed", "failed", "pending"]:
        if self.scenario.status == "pending":
            return "pending"
        return "failed" if self.problems else "passed"


def run_scenario(
    scenario: Scenario, vera: Vera, identity: IdentityStandIn
) -> ScenarioResult:
    """Sign the customer in, let Vera handle the conversation, and check every call."""
    session = identity.sign_in(
        scenario.session.customer_id, scenario.session.task_type, agent_id=vera.agent_id
    )
    conversation = vera.converse(session, scenario.messages(), scenario.planner())
    result = ScenarioResult(scenario=scenario, conversation=conversation)
    for index, (scripted, turn) in enumerate(
        zip(scenario.turns, conversation.turns, strict=True)
    ):
        result.calls.extend(_check_turn(index + 1, scripted.calls, turn.proposals))
    return result


def _check_turn(
    turn: int, scripted: Sequence[ScriptedCall], proposals: Sequence[Proposal]
) -> list[CallResult]:
    results = []
    remaining = list(proposals)
    for call in scripted:
        proposal = (
            remaining.pop(0)
            if remaining and remaining[0].call == call.planned()
            else None
        )
        results.append(
            CallResult(turn, call, proposal, tuple(_compare(turn, call, proposal)))
        )
    return results


def _compare(turn: int, call: ScriptedCall, proposal: Proposal | None) -> list[str]:
    where = f"turn {turn}, {call.tool_name}"
    expect = call.expect
    if proposal is None:
        return [f"{where}: Vera did not propose it"] if expect.proposed else []
    if not expect.proposed:
        return [f"{where}: Vera proposed it but should not have"]
    if proposal.outcome is None:
        return [f"{where}: no decision ({proposal.error})"]
    decision = proposal.outcome.decision
    problems = []
    if decision.decision is not expect.decision:
        problems.append(f"{where}: expected {expect.decision}, got {decision.decision}")
    missing = [
        code for code in expect.reason_codes if code not in decision.reason_codes
    ]
    if missing:
        problems.append(
            f"{where}: expected reason codes {', '.join(missing)}, "
            f"got {', '.join(decision.reason_codes)}"
        )
    return problems
