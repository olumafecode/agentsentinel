"""The demo bank's data, kept in memory (ADR-011).

Every read returns a copy and every change happens under one lock, so concurrent
requests cannot see or leave half-finished updates. ``reset`` rebuilds the bank
from its seed, which returns it to exactly the seeded state.
"""

import hashlib
import json
import threading
from datetime import datetime
from decimal import Decimal
from typing import Any

from demo_bank_api.records import (
    Account,
    AccountStatus,
    Customer,
    Dispute,
    DisputeStatus,
    Transaction,
    TransactionType,
)
from demo_bank_api.seed import DEFAULT_SEED, generate


class BankError(Exception):
    """A tool call the bank cannot carry out. ``code`` is safe to return to callers."""

    status_code = 400
    details: list[Any] | None = None

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(BankError):
    status_code = 404


class ConflictError(BankError):
    status_code = 409


class BankStore:
    def __init__(self, seed: int = DEFAULT_SEED) -> None:
        self._seed = seed
        self._lock = threading.RLock()
        self.reset()

    @property
    def seed(self) -> int:
        return self._seed

    def reset(self) -> str:
        """Rebuild the bank from its seed and return the checksum of the new state."""
        with self._lock:
            data = generate(self._seed)
            self._customers = data.customers
            self._accounts = data.accounts
            self._transactions = data.transactions
            self._disputes = data.disputes
            self._addresses = data.addresses
            self._credential_resets: dict[str, dict[str, str]] = {}
            self._freeze_reasons: dict[str, str] = {}
            self._next_transaction = 1 + max(_number(t) for t in self._transactions)
            return self.checksum()

    def snapshot(self) -> dict[str, Any]:
        """The whole bank as plain JSON values."""
        with self._lock:
            return {
                "seed": self._seed,
                "customers": [
                    c.model_dump(mode="json") for c in self._customers.values()
                ],
                "accounts": [
                    a.model_dump(mode="json") for a in self._accounts.values()
                ],
                "transactions": [
                    t.model_dump(mode="json") for t in self._transactions.values()
                ],
                "disputes": [
                    d.model_dump(mode="json") for d in self._disputes.values()
                ],
                "addresses": dict(self._addresses),
                "credential_resets": dict(self._credential_resets),
                "freeze_reasons": dict(self._freeze_reasons),
            }

    def checksum(self) -> str:
        """SHA-256 of the current state; equal checksums mean identical banks."""
        encoded = json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def counts(self) -> dict[str, int]:
        with self._lock:
            return {
                "customers": len(self._customers),
                "accounts": len(self._accounts),
                "transactions": len(self._transactions),
                "disputes": len(self._disputes),
            }

    # ------------------------------------------------------------------ read tools
    def get_customer(self, customer_id: str) -> tuple[Customer, str]:
        with self._lock:
            customer = self._customer(customer_id)
            return customer.model_copy(), self._addresses[customer_id]

    def list_accounts(self, customer_id: str) -> list[Account]:
        with self._lock:
            self._customer(customer_id)
            return [
                a.model_copy()
                for a in sorted(self._accounts.values(), key=lambda a: a.account_id)
                if a.customer_id == customer_id
            ]

    def list_transactions(self, customer_id: str, limit: int) -> list[Transaction]:
        """The customer's most recent transactions across all of their accounts."""
        with self._lock:
            self._customer(customer_id)
            owned = {
                a.account_id
                for a in self._accounts.values()
                if a.customer_id == customer_id
            }
            matching = [t for t in self._transactions.values() if t.account_id in owned]
            matching.sort(key=lambda t: (t.created_at, t.transaction_id), reverse=True)
            return [t.model_copy() for t in matching[:limit]]

    def export_customers(self) -> list[Customer]:
        with self._lock:
            return [c.model_copy() for _, c in sorted(self._customers.items())]

    # ----------------------------------------------------------------- write tools
    def update_address(self, customer_id: str, address: str) -> str:
        with self._lock:
            self._customer(customer_id)
            self._addresses[customer_id] = address
            return address

    def issue_refund(
        self,
        *,
        account_id: str,
        amount: Decimal,
        original_transaction_id: str,
        reason: str,
        now: datetime,
    ) -> Transaction:
        """Refund part or all of a purchase into ``account_id``."""
        with self._lock:
            original = self._transactions.get(original_transaction_id)
            if original is None:
                raise NotFoundError(
                    "transaction_not_found",
                    f"transaction {original_transaction_id} does not exist",
                )
            if original.transaction_type is not TransactionType.PURCHASE:
                raise ConflictError("not_refundable", "only purchases can be refunded")
            account = self._account(account_id)
            if account.status is not AccountStatus.OPEN:
                raise ConflictError(
                    "account_not_open", f"account {account_id} is not open"
                )

            refunded = sum(
                (
                    t.amount
                    for t in self._transactions.values()
                    if t.transaction_type is TransactionType.REFUND
                    and t.related_transaction_id == original_transaction_id
                ),
                Decimal("0.00"),
            )
            if amount > original.amount - refunded:
                raise ConflictError(
                    "refund_exceeds_original",
                    f"only {original.amount - refunded} of {original_transaction_id} "
                    "is left to refund",
                )

            refund = Transaction(
                transaction_id=f"TXN-{self._next_transaction:010d}",
                account_id=account_id,
                transaction_type=TransactionType.REFUND,
                amount=amount,
                description=f"Refund of {original_transaction_id}: {reason}"[:140],
                related_transaction_id=original_transaction_id,
                created_at=now,
            )
            account.balance = account.balance + amount
            self._transactions[refund.transaction_id] = refund
            self._next_transaction += 1
            return refund.model_copy()

    def close_dispute(self, dispute_id: str, resolution: str, now: datetime) -> Dispute:
        with self._lock:
            dispute = self._disputes.get(dispute_id)
            if dispute is None:
                raise NotFoundError(
                    "dispute_not_found", f"dispute {dispute_id} does not exist"
                )
            if dispute.status is DisputeStatus.CLOSED:
                raise ConflictError(
                    "dispute_already_closed", f"dispute {dispute_id} is closed"
                )
            dispute.status = DisputeStatus.CLOSED
            dispute.resolution = resolution
            dispute.closed_at = now
            return dispute.model_copy()

    # ----------------------------------------------------------------- admin tools
    def reset_credentials(self, customer_id: str, now: datetime) -> dict[str, str]:
        with self._lock:
            self._customer(customer_id)
            reference = f"RST-{len(self._credential_resets) + 1:06d}"
            record = {
                "reset_reference": reference,
                "customer_id": customer_id,
                "requested_at": now.isoformat(),
            }
            self._credential_resets[reference] = record
            return dict(record)

    def freeze_account(self, account_id: str, reason: str) -> Account:
        with self._lock:
            account = self._account(account_id)
            if account.status is AccountStatus.CLOSED:
                raise ConflictError("account_closed", f"account {account_id} is closed")
            account.status = AccountStatus.FROZEN
            self._freeze_reasons[account_id] = reason
            return account.model_copy()

    # --------------------------------------------------------------------- helpers
    def _customer(self, customer_id: str) -> Customer:
        customer = self._customers.get(customer_id)
        if customer is None:
            raise NotFoundError(
                "customer_not_found", f"customer {customer_id} does not exist"
            )
        return customer

    def _account(self, account_id: str) -> Account:
        account = self._accounts.get(account_id)
        if account is None:
            raise NotFoundError(
                "account_not_found", f"account {account_id} does not exist"
            )
        return account


def _number(identifier: str) -> int:
    return int(identifier.split("-", 1)[1])
