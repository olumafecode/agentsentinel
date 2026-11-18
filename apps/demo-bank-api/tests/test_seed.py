"""The seed produces the same synthetic bank every time (US-16.2) and follows the data rules."""

import re
from datetime import timedelta

from demo_bank_api.records import TransactionType
from demo_bank_api.seed import (
    ATTACKER_ACCOUNT_RANGE,
    DEFAULT_SEED,
    WINDOW_END,
    WINDOW_START,
    generate,
)
from demo_bank_api.store import BankStore


def test_same_seed_gives_the_same_bank():
    assert BankStore().checksum() == BankStore().checksum()


def test_different_seed_gives_a_different_bank():
    assert BankStore(seed=DEFAULT_SEED + 1).checksum() != BankStore().checksum()


def test_named_demo_records_are_always_present():
    for seed in (DEFAULT_SEED, 1, 42):
        data = generate(seed)
        assert data.customers["CUS-000123"].full_name == "Avery Stone"
        assert data.accounts["ACC-00000123"].customer_id == "CUS-000123"
        assert data.transactions["TXN-0000004567"].amount == 750
        assert data.accounts["ACC-99000017"].customer_id == "CUS-990001"
        assert data.disputes["DSP-000001"].transaction_id == "TXN-0000004569"


def test_identifiers_are_unique_and_well_formed():
    data = generate()
    assert all(re.fullmatch(r"CUS-\d{6}", c) for c in data.customers)
    assert all(re.fullmatch(r"ACC-\d{8}", a) for a in data.accounts)
    assert all(re.fullmatch(r"TXN-\d{10}", t) for t in data.transactions)
    assert all(re.fullmatch(r"DSP-\d{6}", d) for d in data.disputes)


def test_contact_details_are_reserved_fictional_values():
    data = generate()
    for customer in data.customers.values():
        assert re.fullmatch(r"[a-z0-9._+-]+@example\.(com|org|net)", customer.email)
        assert re.fullmatch(r"\+1-555-01\d{2}", customer.phone)
    for address in data.addresses.values():
        assert re.fullmatch(r"\d+ Example Street, Sampletown, ZZ 00000", address)


def test_only_the_attacker_customer_owns_reserved_attacker_accounts():
    low, high = ATTACKER_ACCOUNT_RANGE
    for account in generate().accounts.values():
        in_range = low <= int(account.account_id[4:]) <= high
        assert in_range == (account.customer_id == "CUS-990001")


def test_every_date_is_inside_the_fixed_window():
    data = generate()
    moments = [c.created_at for c in data.customers.values()]
    moments += [a.opened_at for a in data.accounts.values()]
    moments += [t.created_at for t in data.transactions.values()]
    moments += [d.opened_at for d in data.disputes.values()]
    assert all(WINDOW_START <= m <= WINDOW_END for m in moments)
    assert all(m.utcoffset() == timedelta(0) for m in moments)


def test_every_transaction_and_dispute_points_at_a_real_record():
    data = generate()
    assert all(t.account_id in data.accounts for t in data.transactions.values())
    for dispute in data.disputes.values():
        disputed = data.transactions[dispute.transaction_id]
        assert disputed.transaction_type is TransactionType.PURCHASE
        assert data.accounts[disputed.account_id].customer_id == dispute.customer_id


def test_accounts_open_after_their_customer_is_created():
    data = generate()
    for account in data.accounts.values():
        assert account.opened_at >= data.customers[account.customer_id].created_at


def test_seed_has_a_useful_size():
    counts = BankStore().counts()
    assert counts["customers"] == 43
    assert counts["accounts"] >= 44
    assert counts["transactions"] >= 500
    assert counts["disputes"] >= 2
