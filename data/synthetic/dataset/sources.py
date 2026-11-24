"""What the dataset is built from (US-21).

- The bank policy's data in policies/opa: the refund limits, the time windows and the
  tools each task allows. The labels read the same file as the live policy in OPA,
  so the two cannot drift apart.
- The gateway's agent registry, for the tools each agent may use (rule R2).
- The demo bank's tool catalogue, for which tools are high impact and which of their
  arguments are sensitive (rule R4), and for each argument's format (rule R3).
- The seeded demo bank, for who owns each record (rule R1) and for the customers,
  accounts, purchases and disputes the scenarios use.
"""

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

from data.synthetic.models import Agent, AgentStatus
from demo_bank_api.records import (
    AccountStatus,
    DisputeStatus,
    Transaction,
    TransactionType,
)
from demo_bank_api.seed import ATTACKER_ACCOUNT_RANGE, BankData, generate
from demo_bank_api.store import BankStore
from demo_bank_api.tools import TOOLS, ToolSpec

ROOT = Path(__file__).resolve().parents[3]
POLICY_DATA = ROOT / "policies/opa/agentsentinel/data.json"
POLICY_MANIFEST = ROOT / "policies/opa/.manifest"
AGENTS = ROOT / "services/sentinel-gateway/src/sentinel_gateway/data/agents.json"


@dataclass(frozen=True)
class BankPolicy:
    """The settings and tool lists in the bank policy's data (labelling-rules.md)."""

    version: str
    automatic_refund_limit: Decimal
    refund_hard_cap: Decimal
    quarantine_after: int
    quarantine_window: timedelta
    refund_burst_above: int
    refund_burst_window: timedelta
    near_limit_from: Decimal
    near_limit_to: Decimal
    near_limit_refunds: int
    near_limit_window: timedelta
    task_tools: Mapping[str, frozenset[str]]
    bulk_export_tools: frozenset[str]
    refund_amount_argument: Mapping[str, str]

    @classmethod
    def load(
        cls, data_file: Path = POLICY_DATA, manifest_file: Path = POLICY_MANIFEST
    ) -> "BankPolicy":
        data = json.loads(data_file.read_text(encoding="utf-8"))
        settings = data["settings"]
        quarantine = settings["quarantine"]
        burst = settings["refund_burst"]
        near = settings["near_limit"]
        return cls(
            version=json.loads(manifest_file.read_text(encoding="utf-8"))["revision"],
            automatic_refund_limit=Decimal(settings["automatic_refund_limit"]),
            refund_hard_cap=Decimal(settings["refund_hard_cap"]),
            quarantine_after=quarantine["blocked_actions"],
            quarantine_window=timedelta(minutes=quarantine["window_minutes"]),
            refund_burst_above=burst["more_than"],
            refund_burst_window=timedelta(minutes=burst["window_minutes"]),
            near_limit_from=Decimal(near["band_from"]),
            near_limit_to=Decimal(near["band_to"]),
            near_limit_refunds=near["refunds"],
            near_limit_window=timedelta(hours=near["window_hours"]),
            task_tools=MappingProxyType(
                {task: frozenset(tools) for task, tools in data["task_tools"].items()}
            ),
            bulk_export_tools=frozenset(data["bulk_export_tools"]),
            refund_amount_argument=MappingProxyType(data["refund_amount_argument"]),
        )


@dataclass(frozen=True)
class Purchase:
    """A purchase in the seeded bank, which a refund can point back to."""

    transaction_id: str
    account_id: str
    amount: Decimal
    created_at: datetime


class Bank:
    """The seeded demo bank, read only. Nothing in the dataset is ever executed."""

    def __init__(self, seed: int) -> None:
        self._store = BankStore(seed)  # for owners(), the same answer the gateway gets
        data: BankData = generate(seed)
        self._amounts = {t: tx.amount for t, tx in data.transactions.items()}
        self._addresses = dict(data.addresses)
        self._accounts: dict[str, list[str]] = defaultdict(list)
        for account_id, account in sorted(data.accounts.items()):
            if account.status is AccountStatus.OPEN:
                self._accounts[account.customer_id].append(account_id)
        self._purchases: dict[str, list[Purchase]] = defaultdict(list)
        for t in sorted(data.transactions.values(), key=_posted):
            if t.transaction_type is TransactionType.PURCHASE:
                owner = data.accounts[t.account_id].customer_id
                self._purchases[owner].append(
                    Purchase(t.transaction_id, t.account_id, t.amount, t.created_at)
                )
        self._disputes = sorted(
            (d.dispute_id, d.customer_id, d.opened_at)
            for d in data.disputes.values()
            if d.status is DisputeStatus.OPEN
        )
        self.customers: tuple[str, ...] = tuple(
            sorted(
                customer
                for customer, accounts in self._accounts.items()
                if any(not is_attacker_account(a) for a in accounts)
            )
        )
        """Customers who can sign in to a session: all but the attacker."""
        self.attacker_accounts: tuple[str, ...] = tuple(
            sorted(a for a in data.accounts if is_attacker_account(a))
        )
        """Accounts in the reserved attacker range (data/synthetic/README.md, rule 10)."""

    def owners(self, identifiers: Iterable[str]) -> dict[str, str | None]:
        """The bank's own answer to who owns each record, as the gateway asks it."""
        return self._store.owners(identifiers)

    def transaction_amount(self, transaction_id: object) -> Decimal | None:
        if not isinstance(transaction_id, str):
            return None
        return self._amounts.get(transaction_id)

    def address(self, customer_id: str) -> str:
        return self._addresses[customer_id]

    def accounts(self, customer_id: str) -> tuple[str, ...]:
        """The customer's open accounts."""
        return tuple(self._accounts.get(customer_id, ()))

    def purchases(self, customer_id: str, before: datetime) -> tuple[Purchase, ...]:
        """The customer's purchases posted before ``before``, oldest first."""
        return tuple(
            p for p in self._purchases.get(customer_id, ()) if p.created_at < before
        )

    def open_disputes(self, customer_id: str, before: datetime) -> tuple[str, ...]:
        """The customer's disputes opened before ``before`` and still open."""
        return tuple(
            dispute_id
            for dispute_id, owner, opened_at in self._disputes
            if owner == customer_id and opened_at < before
        )


def _posted(transaction: Transaction) -> tuple[datetime, str]:
    return transaction.created_at, transaction.transaction_id


def is_attacker_account(account_id: str) -> bool:
    low, high = ATTACKER_ACCOUNT_RANGE
    number = account_id.removeprefix("ACC-")
    return number.isdigit() and low <= int(number) <= high


@dataclass(frozen=True)
class Sources:
    """Everything the labeller and the scenarios read."""

    policy: BankPolicy
    agents: Mapping[str, Agent]
    tools: Mapping[str, ToolSpec]
    bank: Bank

    @classmethod
    def load(cls, seed: int) -> "Sources":
        registry = json.loads(AGENTS.read_text(encoding="utf-8"))
        agents = (Agent.model_validate(entry) for entry in registry["agents"])
        return cls(
            policy=BankPolicy.load(),
            agents=MappingProxyType(
                {a.agent_id: a for a in agents if a.status is AgentStatus.ACTIVE}
            ),
            tools=MappingProxyType(dict(TOOLS)),
            bank=Bank(seed),
        )
