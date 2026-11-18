"""Vera's agent loop (US-17).

For each customer message Vera asks her planner which tool calls to make and proposes
them to the gateway one at a time. She never calls the bank herself. How she reacts:

ALLOW         The gateway has run the call; Vera reports the result and goes on.
HUMAN_REVIEW  The call is held for a person; Vera says so and stops this turn.
BLOCK         Vera tells the customer the action was refused and stops this turn.
              She never proposes the same call again in this conversation.
QUARANTINE    Vera says she cannot continue and proposes nothing more at all.

If the gateway cannot be reached, Vera says nothing was done and stops the turn. If it
refuses her request itself (a wrong agent key, for example), she ends the conversation.
"""

import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from banking_agent import replies
from banking_agent.gateway import GatewayClient, GatewayRefused, GatewayUnavailable
from banking_agent.planning import PlannedCall, Planner
from sentinel_contracts import (
    ActionOutcome,
    Decision,
    ProtectedActionRequest,
    TaskType,
)

_SETTLED = (Decision.BLOCK, Decision.QUARANTINE, Decision.HUMAN_REVIEW)


@dataclass(frozen=True)
class SessionContext:
    """The signed-in customer's session, as the chat channel hands it to Vera."""

    session_id: str
    customer_id: str
    task_type: TaskType
    token: str = field(repr=False)


@dataclass(frozen=True)
class Proposal:
    """One call Vera sent to the gateway, and what came back."""

    call: PlannedCall
    correlation_id: str
    outcome: ActionOutcome | None = None
    error: str | None = None

    @property
    def decision(self) -> Decision | None:
        return self.outcome.decision.decision if self.outcome else None


@dataclass
class Turn:
    message: str
    proposals: list[Proposal] = field(default_factory=list)
    not_proposed: list[PlannedCall] = field(default_factory=list)
    reply: str = ""


@dataclass
class Conversation:
    session: SessionContext
    turns: list[Turn] = field(default_factory=list)
    ended: bool = False

    def proposed_calls(self) -> list[PlannedCall]:
        """Every call Vera sent, in order."""
        return [p.call for turn in self.turns for p in turn.proposals]

    def correlation_ids(self) -> list[str]:
        return [p.correlation_id for turn in self.turns for p in turn.proposals]


class _Next(Enum):
    CONTINUE = "continue"
    END_TURN = "end_turn"
    END_CONVERSATION = "end_conversation"


_AFTER_DECISION = {
    Decision.ALLOW: _Next.CONTINUE,
    Decision.HUMAN_REVIEW: _Next.END_TURN,
    Decision.BLOCK: _Next.END_TURN,
    Decision.QUARANTINE: _Next.END_CONVERSATION,
}


class Vera:
    def __init__(
        self,
        gateway: GatewayClient,
        *,
        agent_id: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._gateway = gateway
        self.agent_id = agent_id
        self._clock = clock

    def converse(
        self, session: SessionContext, messages: Sequence[str], planner: Planner
    ) -> Conversation:
        """Handle each customer message in turn and return the whole conversation."""
        conversation = Conversation(session=session)
        settled: list[tuple[PlannedCall, Decision]] = []
        for index, message in enumerate(messages):
            turn = Turn(message=message)
            conversation.turns.append(turn)
            calls = planner.plan(index, message)
            if conversation.ended:
                turn.not_proposed.extend(calls)
                continue
            lines, ended = self._handle_turn(session, turn, calls, settled)
            conversation.ended = ended
            turn.reply = " ".join(lines) or replies.NOTHING_TO_DO
        return conversation

    def _handle_turn(
        self,
        session: SessionContext,
        turn: Turn,
        calls: Sequence[PlannedCall],
        settled: list[tuple[PlannedCall, Decision]],
    ) -> tuple[list[str], bool]:
        lines: list[str] = []
        next_step = _Next.CONTINUE
        for call in calls:
            if next_step is not _Next.CONTINUE:
                turn.not_proposed.append(call)
                continue
            earlier = next((d for c, d in settled if c.same_call_as(call)), None)
            if earlier is not None:
                turn.not_proposed.append(call)
                held = earlier is Decision.HUMAN_REVIEW
                lines.append(replies.ALREADY_HELD if held else replies.ALREADY_REFUSED)
                continue

            proposal, line, next_step = self._propose(session, call)
            turn.proposals.append(proposal)
            lines.append(line)
            if proposal.decision in _SETTLED:
                settled.append((call, proposal.decision))
        return lines, next_step is _Next.END_CONVERSATION

    def _propose(
        self, session: SessionContext, call: PlannedCall
    ) -> tuple[Proposal, str, _Next]:
        request = ProtectedActionRequest(
            correlation_id=str(uuid.uuid4()),
            session_id=session.session_id,
            agent_id=self.agent_id,
            customer_scope=session.customer_id,
            task_type=session.task_type,
            tool_name=call.tool_name,
            arguments=call.arguments,
            provenance_labels=call.provenance,
            requested_at=datetime.fromtimestamp(self._clock(), tz=UTC),
        )
        try:
            outcome = self._gateway.evaluate(request, session.token)
        except GatewayUnavailable as exc:
            proposal = Proposal(call, request.correlation_id, error=exc.code)
            return proposal, replies.UNAVAILABLE, _Next.END_TURN
        except GatewayRefused as exc:
            proposal = Proposal(call, request.correlation_id, error=exc.code)
            return proposal, replies.DISCONNECTED, _Next.END_CONVERSATION
        proposal = Proposal(call, request.correlation_id, outcome=outcome)
        line = replies.describe(call.tool_name, outcome)
        return proposal, line, _AFTER_DECISION[outcome.decision.decision]
