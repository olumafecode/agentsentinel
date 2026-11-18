"""Who owns a bank record: the lookup the gateway uses to keep Vera in scope (US-01.1, ADR-013).

Before it allows an action that names an account, transaction or dispute, the gateway
asks the bank which customer owns each one. Only the bank knows. The lookup is not a
tool Vera can call: like a tool call, it needs an execution token, and only the
gateway can sign one.
"""

from typing import Annotated, Self

from pydantic import Field, model_validator

from sentinel_contracts.actions import Contract
from sentinel_contracts.identifiers import (
    AccountId,
    CustomerId,
    DisputeId,
    TransactionId,
)

OWNERSHIP_TOOL = "resolve_owners"
"""Tool name the lookup's execution token is issued for."""
OWNERSHIP_PATH = "/v1/internal/owners"
"""Where the bank answers the lookup."""
MAX_OWNERSHIP_QUERY = 100
"""Most records one lookup may ask about."""

OwnedRecordId = Annotated[
    AccountId | TransactionId | DisputeId,
    Field(description="An account, transaction or dispute ID"),
]


class OwnershipQuery(Contract):
    """The records whose owners the gateway needs to know."""

    identifiers: list[OwnedRecordId] = Field(
        min_length=1, max_length=MAX_OWNERSHIP_QUERY
    )

    @model_validator(mode="after")
    def _no_repeats(self) -> Self:
        if len(set(self.identifiers)) != len(self.identifiers):
            raise ValueError("identifiers must not repeat")
        return self


class OwnershipAnswer(Contract):
    """The owning customer of each record asked about, or None if the bank has no such record."""

    owners: dict[str, CustomerId | None]
