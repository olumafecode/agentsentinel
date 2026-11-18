"""How Vera decides which tool calls to propose.

A Planner turns the customer's message into tool calls. In scripted mode the calls
come from a scenario, so every run proposes exactly the same calls in the same order
(US-17). The live language model in US-24 is another Planner behind the same
interface, so the agent loop does not change.
"""

from collections.abc import Sequence
from typing import Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from sentinel_contracts import Provenance
from sentinel_contracts.identifiers import ArgumentName, ToolName
from sentinel_contracts.signing import canonical_json


class PlannedCall(BaseModel):
    """One tool call Vera intends to propose, with where each argument came from."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    tool_name: ToolName
    arguments: dict[ArgumentName, JsonValue] = Field(default_factory=dict)
    provenance: dict[ArgumentName, Provenance] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _labels_refer_to_arguments(self) -> Self:
        unknown = sorted(set(self.provenance) - set(self.arguments))
        if unknown:
            raise ValueError(f"provenance for arguments that do not exist: {unknown}")
        return self

    def same_call_as(self, other: "PlannedCall") -> bool:
        """True when both call the same tool with the same arguments."""
        return self.key() == other.key()

    def key(self) -> bytes:
        return canonical_json([self.tool_name, self.arguments])


class Planner(Protocol):
    def plan(self, turn: int, message: str) -> Sequence[PlannedCall]:
        """The calls to propose for the customer's message in turn ``turn`` (from 0)."""
        ...


class ScriptedPlanner:
    """Plays back a fixed list of calls for each turn."""

    def __init__(self, turns: Sequence[Sequence[PlannedCall]]) -> None:
        self._turns = [tuple(calls) for calls in turns]

    def plan(self, turn: int, message: str) -> Sequence[PlannedCall]:
        return self._turns[turn] if turn < len(self._turns) else ()
