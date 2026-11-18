"""Records the demo bank keeps.

Customer, Account and Transaction use the same fields and formats as
data/synthetic/models.py; tests/test_bank_seed_matches_schema.py checks that.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from sentinel_contracts.identifiers import (
    AccountId,
    CustomerId,
    DisputeId,
    TransactionId,
)

Money = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"


class AccountStatus(StrEnum):
    OPEN = "open"
    FROZEN = "frozen"
    CLOSED = "closed"


class TransactionType(StrEnum):
    PURCHASE = "purchase"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    FEE = "fee"
    REFUND = "refund"


class DisputeStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Record(BaseModel):
    """Base for bank records: unknown fields are rejected and every change is validated."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Customer(Record):
    customer_id: CustomerId
    full_name: str = Field(min_length=3, max_length=80)
    email: str
    phone: str
    created_at: AwareDatetime


class Account(Record):
    account_id: AccountId
    customer_id: CustomerId
    account_type: AccountType
    currency: Literal["USD"] = "USD"
    balance: Money = Field(ge=0)
    status: AccountStatus
    opened_at: AwareDatetime


class Transaction(Record):
    transaction_id: TransactionId
    account_id: AccountId
    transaction_type: TransactionType
    amount: Money = Field(gt=0)
    currency: Literal["USD"] = "USD"
    description: str = Field(max_length=140)
    related_transaction_id: TransactionId | None = None
    created_at: AwareDatetime


class Dispute(Record):
    dispute_id: DisputeId
    customer_id: CustomerId
    transaction_id: TransactionId
    reason: str = Field(max_length=200)
    status: DisputeStatus
    opened_at: AwareDatetime
    resolution: str | None = Field(default=None, max_length=300)
    closed_at: AwareDatetime | None = None
