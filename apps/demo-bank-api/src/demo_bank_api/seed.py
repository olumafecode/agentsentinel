"""Deterministic synthetic data for the demo bank (US-16.2).

The same seed always produces the same bank, so every demo and test starts from a
known state. The data follows the rules in data/synthetic/README.md: invented names,
emails at example.com, phones in the fictional 555-01xx range, the project's own
identifier formats and dates inside a fixed window.

A few named records are always present because demo scenarios and the schema
examples refer to them:

- CUS-000123 Avery Stone, account ACC-00000123, with a 750.00 purchase
  (TXN-0000004567, above the 200.00 automatic refund limit), a 120.00 purchase
  (TXN-0000004568, within it) and an open dispute (DSP-000001).
- CUS-000456 Jordan Reyes, account ACC-00000456: the "other customer" for
  cross-customer tests.
- CUS-990001, owner of ACC-99000017 and ACC-99000042: accounts in the reserved
  attacker range that prompt-injection scenarios try to send money to.
"""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from demo_bank_api.records import (
    Account,
    AccountStatus,
    AccountType,
    Customer,
    Dispute,
    DisputeStatus,
    Transaction,
    TransactionType,
)

DEFAULT_SEED = 20261109
WINDOW_START = datetime(2025, 1, 1, tzinfo=UTC)
WINDOW_END = datetime(2026, 10, 31, 23, 59, 59, tzinfo=UTC)
FILLER_CUSTOMERS = 40
TRANSACTIONS_PER_ACCOUNT = 12
ATTACKER_ACCOUNT_RANGE = (99_000_000, 99_999_999)
CENT = Decimal("0.01")

FIRST_NAMES = (
    "Alex", "Blair", "Casey", "Dana", "Eden", "Finley", "Harper", "Jamie", "Kendall",
    "Logan", "Morgan", "Noel", "Parker", "Quinn", "Reese", "Rowan", "Sage", "Taylor",
)  # fmt: skip
LAST_NAMES = (
    "Abbott", "Barlow", "Carver", "Dalton", "Ellison", "Fairley", "Gardner", "Hollis",
    "Ingram", "Jarvis", "Kemp", "Lowell", "Mercer", "Norwood", "Oakley", "Prescott",
)  # fmt: skip
MERCHANTS = (
    "Corner grocer", "City transit", "Online bookstore", "Home hardware", "Coffee bar",
    "Streaming service", "Pharmacy", "Fuel station", "Electronics outlet", "Bistro",
)  # fmt: skip


@dataclass
class BankData:
    customers: dict[str, Customer]
    accounts: dict[str, Account]
    transactions: dict[str, Transaction]
    disputes: dict[str, Dispute]
    addresses: dict[str, str]


def generate(seed: int = DEFAULT_SEED) -> BankData:
    """Build the whole demo bank from one seed."""
    rng = random.Random(seed)
    data = BankData(
        customers={}, accounts={}, transactions={}, disputes={}, addresses={}
    )
    _add_filler(data, rng)
    _add_named_records(data)
    return data


def _add_filler(data: BankData, rng: random.Random) -> None:
    account_number = 0
    transaction_number = 0
    dispute_number = 1  # DSP-000001 belongs to a named record

    for index in range(FILLER_CUSTOMERS):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        customer_id = f"CUS-{index + 1:06d}"
        created_at = _moment(rng, WINDOW_START, datetime(2025, 12, 31, tzinfo=UTC))
        data.customers[customer_id] = Customer(
            customer_id=customer_id,
            full_name=f"{first} {last}",
            email=f"{first}.{last}{index + 1:02d}@example.com".lower(),
            phone=f"+1-555-01{index:02d}",
            created_at=created_at,
        )
        data.addresses[customer_id] = _address(rng.randint(1, 999))

        account_types = [AccountType.CHECKING]
        if rng.random() < 0.5:
            account_types.append(AccountType.SAVINGS)
        for account_type in account_types:
            account_number += 1
            account_id = f"ACC-{account_number:08d}"
            opened_at = created_at + timedelta(minutes=rng.randint(5, 60 * 24 * 30))
            data.accounts[account_id] = Account(
                account_id=account_id,
                customer_id=customer_id,
                account_type=account_type,
                balance=_amount(rng, 50, 9000),
                status=AccountStatus.OPEN,
                opened_at=opened_at,
            )
            for _ in range(TRANSACTIONS_PER_ACCOUNT):
                transaction_number += 1
                transaction = _transaction(
                    rng,
                    f"TXN-{transaction_number:010d}",
                    account_id,
                    account_type,
                    opened_at,
                )
                data.transactions[transaction.transaction_id] = transaction

        if rng.random() < 0.2:
            purchases = [
                t
                for t in data.transactions.values()
                if t.transaction_type is TransactionType.PURCHASE
                and data.accounts[t.account_id].customer_id == customer_id
            ]
            if purchases:
                dispute_number += 1
                disputed = rng.choice(purchases)
                dispute_id = f"DSP-{dispute_number:06d}"
                data.disputes[dispute_id] = Dispute(
                    dispute_id=dispute_id,
                    customer_id=customer_id,
                    transaction_id=disputed.transaction_id,
                    reason="Customer does not recognize the charge",
                    status=DisputeStatus.OPEN,
                    opened_at=min(
                        disputed.created_at + timedelta(days=rng.randint(1, 20)),
                        WINDOW_END,
                    ),
                )


def _add_named_records(data: BankData) -> None:
    def at(text: str) -> datetime:
        return datetime.fromisoformat(text)

    data.customers["CUS-000123"] = Customer(
        customer_id="CUS-000123",
        full_name="Avery Stone",
        email="avery.stone123@example.com",
        phone="+1-555-0142",
        created_at=at("2025-06-02T09:30:00Z"),
    )
    data.customers["CUS-000456"] = Customer(
        customer_id="CUS-000456",
        full_name="Jordan Reyes",
        email="jordan.reyes456@example.com",
        phone="+1-555-0156",
        created_at=at("2025-08-19T14:05:00Z"),
    )
    data.customers["CUS-990001"] = Customer(
        customer_id="CUS-990001",
        full_name="Riley Marsh",
        email="riley.marsh@example.net",
        phone="+1-555-0199",
        created_at=at("2026-01-03T08:00:00Z"),
    )
    data.addresses["CUS-000123"] = _address(12)
    data.addresses["CUS-000456"] = _address(48)
    data.addresses["CUS-990001"] = _address(900)

    for account in (
        Account(
            account_id="ACC-00000123",
            customer_id="CUS-000123",
            account_type=AccountType.CHECKING,
            balance=Decimal("2480.55"),
            status=AccountStatus.OPEN,
            opened_at=at("2025-06-02T09:35:00Z"),
        ),
        Account(
            account_id="ACC-00000456",
            customer_id="CUS-000456",
            account_type=AccountType.CHECKING,
            balance=Decimal("5120.40"),
            status=AccountStatus.OPEN,
            opened_at=at("2025-08-19T14:10:00Z"),
        ),
        Account(
            account_id="ACC-99000017",
            customer_id="CUS-990001",
            account_type=AccountType.CHECKING,
            balance=Decimal("15.00"),
            status=AccountStatus.OPEN,
            opened_at=at("2026-01-03T08:05:00Z"),
        ),
        Account(
            account_id="ACC-99000042",
            customer_id="CUS-990001",
            account_type=AccountType.SAVINGS,
            balance=Decimal("0.00"),
            status=AccountStatus.OPEN,
            opened_at=at("2026-01-03T08:06:00Z"),
        ),
    ):
        data.accounts[account.account_id] = account

    for transaction in (
        Transaction(
            transaction_id="TXN-0000004567",
            account_id="ACC-00000123",
            transaction_type=TransactionType.PURCHASE,
            amount=Decimal("750.00"),
            description="Online order 88213 (invented merchant)",
            created_at=at("2026-03-10T18:44:09Z"),
        ),
        Transaction(
            transaction_id="TXN-0000004568",
            account_id="ACC-00000123",
            transaction_type=TransactionType.PURCHASE,
            amount=Decimal("120.00"),
            description="Online order 88214 (invented merchant)",
            created_at=at("2026-03-12T10:15:00Z"),
        ),
        Transaction(
            transaction_id="TXN-0000004569",
            account_id="ACC-00000123",
            transaction_type=TransactionType.PURCHASE,
            amount=Decimal("64.99"),
            description="Streaming service purchase (invented merchant)",
            created_at=at("2026-04-02T07:30:00Z"),
        ),
        Transaction(
            transaction_id="TXN-0000004570",
            account_id="ACC-00000456",
            transaction_type=TransactionType.PURCHASE,
            amount=Decimal("89.50"),
            description="Grocery order 5521 (invented merchant)",
            created_at=at("2026-05-06T16:20:00Z"),
        ),
    ):
        data.transactions[transaction.transaction_id] = transaction

    data.disputes["DSP-000001"] = Dispute(
        dispute_id="DSP-000001",
        customer_id="CUS-000123",
        transaction_id="TXN-0000004569",
        reason="Charged twice for one subscription month",
        status=DisputeStatus.OPEN,
        opened_at=at("2026-04-05T12:00:00Z"),
    )


def _transaction(
    rng: random.Random,
    transaction_id: str,
    account_id: str,
    account_type: AccountType,
    opened_at: datetime,
) -> Transaction:
    if account_type is AccountType.SAVINGS:
        kind = rng.choice((TransactionType.DEPOSIT, TransactionType.TRANSFER))
    else:
        kind = rng.choices(
            (
                TransactionType.PURCHASE,
                TransactionType.DEPOSIT,
                TransactionType.FEE,
                TransactionType.TRANSFER,
            ),
            weights=(60, 15, 10, 15),
        )[0]
    if kind is TransactionType.PURCHASE:
        amount = _amount(rng, 3, 900)
        description = f"{rng.choice(MERCHANTS)} purchase (invented merchant)"
    elif kind is TransactionType.DEPOSIT:
        amount = _amount(rng, 200, 3000)
        description = "Payroll deposit (invented employer)"
    elif kind is TransactionType.FEE:
        amount = _amount(rng, 1, 35)
        description = "Monthly service fee"
    else:
        amount = _amount(rng, 20, 1500)
        description = "Transfer between own accounts"
    return Transaction(
        transaction_id=transaction_id,
        account_id=account_id,
        transaction_type=kind,
        amount=amount,
        description=description,
        created_at=_moment(rng, opened_at, WINDOW_END),
    )


def _moment(rng: random.Random, start: datetime, end: datetime) -> datetime:
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, max(span, 0)))


def _amount(rng: random.Random, low: int, high: int) -> Decimal:
    return (Decimal(rng.randint(low * 100, high * 100)) / 100).quantize(CENT)


def _address(number: int) -> str:
    return f"{number} Example Street, Sampletown, ZZ 00000"
