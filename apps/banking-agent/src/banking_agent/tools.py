"""The tools Vera may propose, with their argument schemas (US-17.1).

They come from ``data/tools.json``, a copy of the demo bank's catalogue for Vera's
allowed tools. Vera offers them to the language model in live mode (US-24). She does
not police herself with them: whatever she proposes, the gateway decides.
"""

import json
from functools import cache
from importlib.resources import files
from typing import Any


@cache
def tool_schemas() -> tuple[dict[str, Any], ...]:
    """Each tool as name, description, high_impact, sensitive_parameters and parameters."""
    text = (
        files("banking_agent")
        .joinpath("data", "tools.json")
        .read_text(encoding="utf-8")
    )
    return tuple(json.loads(text)["tools"])


def tool_names() -> list[str]:
    return [tool["name"] for tool in tool_schemas()]
