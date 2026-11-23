"""The agents and tools the gateway knows about.

Both lists ship with the package as JSON in ``sentinel_gateway/data``. Anything not
listed is unknown, and the gateway blocks actions from an unknown agent or for an
unknown tool (deny by default, NFR-01). An agent's status can change while the
gateway runs, for example when it is quarantined (US-05).
"""

import json
import threading
from collections.abc import Iterable, Iterator, Mapping
from enum import StrEnum
from importlib.resources import files
from types import MappingProxyType
from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from sentinel_contracts.identifiers import AgentId, ArgumentName, ToolName


class AgentStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"


class ToolCategory(StrEnum):
    READ = "read"
    WRITE = "write"
    FINANCIAL = "financial"
    EXPORT = "export"
    ADMIN = "admin"


class _Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AgentProfile(_Entry):
    """One registered agent, in the shape of the Agent entity in the schema."""

    agent_id: AgentId
    name: Annotated[str, StringConstraints(min_length=2, max_length=40)]
    role: Annotated[str, StringConstraints(min_length=3, max_length=40)]
    allowed_tools: tuple[ToolName, ...] = Field(min_length=1)
    status: AgentStatus
    review_threshold: float = Field(ge=0, le=1)
    block_threshold: float = Field(ge=0, le=1)
    created_at: AwareDatetime

    @model_validator(mode="after")
    def _thresholds_are_ordered(self) -> Self:
        if self.review_threshold > self.block_threshold:
            raise ValueError("review_threshold must not be higher than block_threshold")
        return self


class ToolProfile(_Entry):
    """One bank tool, in the shape of the ToolDefinition entity in the schema.

    The entity's allowed_task_types are not here: which tasks may use a tool is bank
    policy, kept in policies/opa/agentsentinel/data.json (US-02a).
    """

    tool_name: ToolName
    category: ToolCategory
    description: Annotated[str, StringConstraints(min_length=3, max_length=200)]
    high_impact: bool
    sensitive_parameters: tuple[ArgumentName, ...]


class AgentRegistry:
    """Registered agents, looked up by ID. Safe to use from several threads."""

    def __init__(self, agents: Iterable[AgentProfile]) -> None:
        self._agents: dict[str, AgentProfile] = {}
        for agent in agents:
            if agent.agent_id in self._agents:
                raise ValueError(f"agent {agent.agent_id} is listed twice")
            self._agents[agent.agent_id] = agent
        self._lock = threading.Lock()

    @classmethod
    def load(cls) -> Self:
        """Read the agents that ship with the gateway."""
        return cls(
            AgentProfile.model_validate(entry)
            for entry in _read("agents.json")["agents"]
        )

    def get(self, agent_id: str) -> AgentProfile | None:
        with self._lock:
            return self._agents.get(agent_id)

    def set_status(self, agent_id: str, status: AgentStatus) -> AgentProfile:
        """Change an agent's status, for example to quarantine it, and return the new entry."""
        with self._lock:
            agent = self._agents[agent_id].model_copy(update={"status": status})
            self._agents[agent_id] = agent
            return agent

    def ids(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._agents)

    def __len__(self) -> int:
        with self._lock:
            return len(self._agents)


class ToolRegistry(Mapping[str, ToolProfile]):
    """Known bank tools, looked up by name. It does not change while the gateway runs."""

    def __init__(self, tools: Iterable[ToolProfile]) -> None:
        entries: dict[str, ToolProfile] = {}
        for tool in tools:
            if tool.tool_name in entries:
                raise ValueError(f"tool {tool.tool_name} is listed twice")
            entries[tool.tool_name] = tool
        self._tools = MappingProxyType(entries)

    @classmethod
    def load(cls) -> Self:
        """Read the tools that ship with the gateway."""
        return cls(
            ToolProfile.model_validate(entry) for entry in _read("tools.json")["tools"]
        )

    def __getitem__(self, tool_name: str) -> ToolProfile:
        return self._tools[tool_name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._tools)

    def __len__(self) -> int:
        return len(self._tools)


def _read(name: str) -> dict:
    return json.loads(
        files("sentinel_gateway").joinpath("data", name).read_text(encoding="utf-8")
    )
