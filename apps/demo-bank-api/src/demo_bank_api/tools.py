"""The bank tools Vera can ask for, with their arguments and what makes them sensitive.

Categories use the same values as ToolCategory in data/synthetic/models.py. The
catalogue describes tools only; which agent and task may use which tool is decided
by the gateway's policy, not by the bank.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from demo_bank_api.records import DisputeId
from demo_bank_api.store import BankStore
from sentinel_contracts.identifiers import AccountId, CustomerId, TransactionId


class ToolCategory(StrEnum):
    READ = "read"
    WRITE = "write"
    FINANCIAL = "financial"
    EXPORT = "export"
    ADMIN = "admin"


Address = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=5, max_length=200)
]
RefundReason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100)
]
Note = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)
]
RefundAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class Arguments(BaseModel):
    """Base for tool arguments: unknown arguments are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class NoArguments(Arguments):
    pass


class CustomerArguments(Arguments):
    customer_id: CustomerId


class GetTransactionsArguments(CustomerArguments):
    limit: int = Field(default=20, ge=1, le=100)


class UpdateAddressArguments(CustomerArguments):
    address: Address


class IssueRefundArguments(Arguments):
    account_id: AccountId = Field(description="Account that receives the refund")
    amount: RefundAmount = Field(
        description="Amount in USD, sent as a string such as '120.00'"
    )
    original_transaction_id: TransactionId = Field(
        description="Purchase being refunded"
    )
    reason: RefundReason


class CloseDisputeArguments(Arguments):
    dispute_id: DisputeId
    resolution: Note


class FreezeAccountArguments(Arguments):
    account_id: AccountId
    reason: Note


Handler = Callable[[BankStore, Any, datetime], Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    category: ToolCategory
    description: str
    high_impact: bool
    sensitive_parameters: tuple[str, ...]
    arguments_model: type[Arguments]
    run: Handler

    def catalogue_entry(self) -> dict[str, Any]:
        return {
            "tool_name": self.name,
            "category": self.category.value,
            "description": self.description,
            "high_impact": self.high_impact,
            "sensitive_parameters": list(self.sensitive_parameters),
            "arguments_schema": self.arguments_model.model_json_schema(),
        }


def _get_customer(store: BankStore, args: CustomerArguments, now: datetime) -> Any:
    customer, address = store.get_customer(args.customer_id)
    return {**customer.model_dump(mode="json"), "address": address}


def _get_accounts(store: BankStore, args: CustomerArguments, now: datetime) -> Any:
    return [a.model_dump(mode="json") for a in store.list_accounts(args.customer_id)]


def _get_transactions(
    store: BankStore, args: GetTransactionsArguments, now: datetime
) -> Any:
    return [
        t.model_dump(mode="json")
        for t in store.list_transactions(args.customer_id, args.limit)
    ]


def _update_address(
    store: BankStore, args: UpdateAddressArguments, now: datetime
) -> Any:
    return {
        "customer_id": args.customer_id,
        "address": store.update_address(args.customer_id, args.address),
    }


def _issue_refund(store: BankStore, args: IssueRefundArguments, now: datetime) -> Any:
    refund = store.issue_refund(
        account_id=args.account_id,
        amount=args.amount,
        original_transaction_id=args.original_transaction_id,
        reason=args.reason,
        now=now,
    )
    return refund.model_dump(mode="json")


def _close_dispute(store: BankStore, args: CloseDisputeArguments, now: datetime) -> Any:
    return store.close_dispute(args.dispute_id, args.resolution, now).model_dump(
        mode="json"
    )


def _export_customers(store: BankStore, args: NoArguments, now: datetime) -> Any:
    return [c.model_dump(mode="json") for c in store.export_customers()]


def _reset_credentials(store: BankStore, args: CustomerArguments, now: datetime) -> Any:
    return store.reset_credentials(args.customer_id, now)


def _freeze_account(
    store: BankStore, args: FreezeAccountArguments, now: datetime
) -> Any:
    return store.freeze_account(args.account_id, args.reason).model_dump(mode="json")


TOOLS: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in (
        ToolSpec(
            name="get_customer",
            category=ToolCategory.READ,
            description="Read one customer's profile and mailing address",
            high_impact=False,
            sensitive_parameters=(),
            arguments_model=CustomerArguments,
            run=_get_customer,
        ),
        ToolSpec(
            name="get_accounts",
            category=ToolCategory.READ,
            description="List one customer's accounts and balances",
            high_impact=False,
            sensitive_parameters=(),
            arguments_model=CustomerArguments,
            run=_get_accounts,
        ),
        ToolSpec(
            name="get_transactions",
            category=ToolCategory.READ,
            description="List one customer's most recent transactions, newest first",
            high_impact=False,
            sensitive_parameters=(),
            arguments_model=GetTransactionsArguments,
            run=_get_transactions,
        ),
        ToolSpec(
            name="update_address",
            category=ToolCategory.WRITE,
            description="Change one customer's mailing address",
            high_impact=False,
            sensitive_parameters=("address",),
            arguments_model=UpdateAddressArguments,
            run=_update_address,
        ),
        ToolSpec(
            name="issue_refund",
            category=ToolCategory.FINANCIAL,
            description="Refund a posted transaction to the customer's own account",
            high_impact=True,
            sensitive_parameters=("account_id", "amount"),
            arguments_model=IssueRefundArguments,
            run=_issue_refund,
        ),
        ToolSpec(
            name="close_dispute",
            category=ToolCategory.WRITE,
            description="Close an open dispute with a resolution note",
            high_impact=False,
            sensitive_parameters=(),
            arguments_model=CloseDisputeArguments,
            run=_close_dispute,
        ),
        ToolSpec(
            name="export_customers",
            category=ToolCategory.EXPORT,
            description="Export every customer record in the bank",
            high_impact=True,
            sensitive_parameters=(),
            arguments_model=NoArguments,
            run=_export_customers,
        ),
        ToolSpec(
            name="reset_credentials",
            category=ToolCategory.ADMIN,
            description="Reset a customer's sign-in credentials (administrators only)",
            high_impact=True,
            sensitive_parameters=("customer_id",),
            arguments_model=CustomerArguments,
            run=_reset_credentials,
        ),
        ToolSpec(
            name="freeze_account",
            category=ToolCategory.ADMIN,
            description="Freeze an account so no money can move in or out (administrators only)",
            high_impact=True,
            sensitive_parameters=("account_id",),
            arguments_model=FreezeAccountArguments,
            run=_freeze_account,
        ),
    )
}
