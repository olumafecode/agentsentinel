"""The checks the gateway runs on every action (ADR-012).

The orchestrator sorts them by stage, so the order here matters only within a stage:
cheap checks without network calls come first. Each story that adds a rule adds it
here, with any client it needs passed in as an argument.
"""

from sentinel_gateway.checks import (
    AgentStatusCheck,
    Check,
    ContextBindingCheck,
    KnownToolCheck,
    RequestFreshnessCheck,
)
from sentinel_gateway.scope import (
    CustomerScopeCheck,
    OwnershipLookup,
    ToolAllowlistCheck,
)


def default_checks(*, ownership: OwnershipLookup) -> list[Check]:
    """Every check, given the clients the checks need."""
    return [
        # CONTEXT (US-18)
        ContextBindingCheck(),
        AgentStatusCheck(),
        RequestFreshnessCheck(),
        KnownToolCheck(),
        # HARD_RULE (US-01)
        ToolAllowlistCheck(),
        CustomerScopeCheck(ownership),
    ]
