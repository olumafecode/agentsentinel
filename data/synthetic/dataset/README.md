# Dataset card: labelled synthetic action events

Every row is one action that Vera proposes to the demo bank, labelled with what AgentSentinel should decide. The risk model in US-04 is trained and tuned on the train and validation splits, and the test split is used once, in US-26, for the final results.

| | |
|---|---|
| Version | 1.0.0 |
| Seed | 20261109 |
| Events | 3,556 in 1,130 sessions |
| Row format | `LabelledActionEvent` in `data/synthetic/models.py`, schema version 1.0.0 |
| Labels | The rules in [labelling-rules.md](../labelling-rules.md), applied by `labeller.py` |
| Bank policy | Version 1.0.0 of `policies/opa`: the labels were frozen against it |
| Story | US-21 (#30), tasks #153 to #156 |
| Requirements | FR-07, NFR-08, NFR-14 |

## Getting the files

The split files are not in git. They are rebuilt from the seed, and `manifest.json`, which is in git, holds the checksum of each one. One-time setup, from the repository root:

```
py -m pip install -r requirements-dev.txt
py -m pip install --no-deps -e libs/sentinel-contracts -e apps/demo-bank-api
```

| Command | What it does |
|---|---|
| `py -m data.synthetic.dataset write` | Writes `train.jsonl`, `validation.jsonl` and `test.jsonl` to `data/synthetic/dataset/output/`, which git ignores. Refuses if the data does not match the manifest |
| `py -m data.synthetic.dataset check` | Confirms the generator still gives the frozen data |
| `py -m data.synthetic.dataset show SEQ-000001` | Prints one session with its labels and the reason for each |
| `py -m data.synthetic.dataset freeze` | Records a new version. Only after `GENERATOR_VERSION` has been bumped |

On Linux and macOS, use `python` in place of `py`. In code, `read_split` checks the file's checksum against the manifest before it returns any rows:

```python
from data.synthetic.dataset import read_split
from data.synthetic.models import DatasetSplit

train = read_split(DatasetSplit.TRAIN)  # a list of LabelledActionEvent
```

Each file is JSON Lines: one event per line, keys sorted, no spaces, UTF-8, with a line feed after every line. The bytes, and so the checksums, are the same on Windows, Linux and macOS and on Python 3.12 to 3.14.

## Splits and class balance

Sessions are split 70/15/15, separately within each kind of session below, so every split has every kind. A session is never divided between two splits.

| Split | Events | Sessions | ALLOW | HUMAN_REVIEW | BLOCK | QUARANTINE |
|---|---|---|---|---|---|---|
| train | 2,492 | 790 | 1,521 | 288 | 538 | 145 |
| validation | 526 | 170 | 317 | 58 | 118 | 33 |
| test | 538 | 170 | 326 | 60 | 118 | 34 |
| Total | 3,556 | 1,130 | 2,164 (60.9%) | 406 (11.4%) | 774 (21.8%) | 212 (6.0%) |

The target in the labelling rules is about 60% `ALLOW`, 12% `HUMAN_REVIEW`, 22% `BLOCK` and 6% `QUARANTINE`. Unsafe actions are over-represented on purpose, so the model has enough of them to learn from.

The checksums frozen in `manifest.json`:

| Split | SHA-256 |
|---|---|
| train | `be8d927bff75323a12c5b61e06b8ecd25c869915ed7188055f196bf0fdb1d750` |
| validation | `335dc5367049abe85803a82034e5a852e6e806f9b4dedb1a7d6ee8964c9eff8b` |
| test | `b4aa55084c9fcbfff798b8995e4ca3aa9ffd964e8cd978a8c5db9ffd44259845` |

Events by the rule that set their outcome:

| Rule | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 |
|---|---|---|---|---|---|---|---|---|---|
| Events | 342 | 180 | 95 | 49 | 212 | 263 | 108 | 143 | 2,164 |

## Failure modes

Every split holds normal behavior and all five failure modes from proposal Section 2.1.

| Failure mode | train | validation | test | Total |
|---|---|---|---|---|
| `none` | 1,499 | 309 | 319 | 2,127 |
| `prompt_injection` | 84 | 19 | 17 | 120 |
| `misunderstood_instruction` | 53 | 11 | 11 | 75 |
| `wrong_tool_or_invalid_details` | 92 | 19 | 19 | 130 |
| `outside_authority` | 100 | 25 | 24 | 149 |
| `unintended_sequence` | 664 | 143 | 148 | 955 |

A failure mode is declared by the session that produced the action, and every action the failure produces carries it. That includes actions that are still allowed because the pattern is not complete yet, such as the first four refunds of a burst, so `unintended_sequence` also appears on `ALLOW` rows. Where each mode lands:

| Failure mode | Rules |
|---|---|
| `none` | R9, and R6 for a legitimate large refund |
| `prompt_injection` | R1 when the injected account belongs to someone else, R4 when it stays inside the customer's scope |
| `misunderstood_instruction` | R2 |
| `wrong_tool_or_invalid_details` | R2, R3 |
| `outside_authority` | R1 |
| `unintended_sequence` | R5, R7, R8; R1 and R2 for the blocked probes before a quarantine; R9 for the start of a pattern |

## Kinds of session

| Family | Sessions | Task | Failure mode | Use case | What happens |
|---|---|---|---|---|---|
| `inquiry` | 60 | account_inquiry | none | UC-01 | Two to four lookups of the customer's own profile, accounts or transactions |
| `small_refund` | 60 | refund_request | none | UC-01 | One or two refunds up to the automatic limit, including exactly 200.00. Sometimes the reason comes from a forwarded email, which is untrusted but not a sensitive argument |
| `large_refund` | 235 | refund_request | none | UC-03 | A legitimate refund above the automatic limit, including 200.01 |
| `address_change` | 40 | profile_update | none | UC-01 | The customer's new mailing address |
| `dispute_handling` | 40 | dispute | none | UC-01 | Close the customer's open dispute, or freeze their account after a payment they did not make |
| `injected_refund` | 75 | refund_request | prompt_injection | UC-02 | A forwarded email sends the refund to an attacker's account, or sets its amount |
| `injected_freeze` | 25 | dispute | prompt_injection | UC-02 | A document names the account to freeze |
| `misunderstood` | 75 | several | misunderstood_instruction | none | The wrong action for the request, such as resetting credentials when asked to change an address |
| `invalid_details` | 95 | refund_request, account_inquiry | wrong_tool_or_invalid_details | none | A negative, zero, over-precise, numeric, over-cap or over-purchase amount, a malformed identifier, or an impossible transaction limit |
| `similar_tool` | 35 | several | wrong_tool_or_invalid_details | none | A tool close to the right one but not allowed for the task |
| `cross_customer` | 85 | several | outside_authority | UC-04 | Another customer's records, account or purchase |
| `bulk_export` | 45 | any customer task | outside_authority | UC-05 | An export of every customer record |
| `refund_burst` | 50 | refund_request | unintended_sequence | UC-06 | Five to seven small refunds within five minutes |
| `near_limit` | 100 | refund_request | unintended_sequence | UC-06 | Two or three refunds from 180.00 to 200.00 for one customer |
| `admin_probe` | 50 | several | unintended_sequence | UC-06 | Normal service, then one or two admin or export requests (AT-07) |
| `repeated_violations` | 60 | any customer task | unintended_sequence | UC-07 | Prohibited actions until the agent is quarantined, then more actions (AT-08) |

## How the data is made

- **The bank.** Sessions use the seeded demo bank from `apps/demo-bank-api`, built from the same seed, so every customer, account, purchase and dispute in the data exists there. The attacker customer, CUS-990001, never signs in; their accounts appear only as injected destinations.
- **The sessions.** The generator writes 1,130 sessions in shuffled order on a timeline of two-hour slots from 1 July 2026. A session starts in the first hour of its slot and lasts at most 30 minutes. The same customer never has two sessions within 25 hours. So each session stands alone, and R5, R7 and R8 only count actions from the same session.
- **The labels.** The labeller applies R1 to R9 in order, reading the limits, windows and tool lists from `policies/opa/agentsentinel/data.json`, the agent's tools from the gateway's registry and the tools' formats from the bank. No scenario sets an outcome. Each one states the rules it expects, and the generator stops if a label is different, so a scenario cannot quietly carry the wrong failure mode.
- **The live policy.** `tests/test_dataset_matches_policy.py` sends every event to OPA with the bank policy and checks that the policy reports exactly the rules the labeller found, for every rule the policy has.
- **The random numbers.** Python promises across versions only that `random()` gives the same numbers for the same seed, so `rng.py` builds every choice on it. The events, the split and the review sample each have their own stream, so a change to one never shifts another.

## Freezing and changing the dataset

The test split was frozen, with its checksum, before any model tuning. Three things keep it frozen:

1. `tests/test_dataset.py` fails if the generator no longer produces the data in `manifest.json`.
2. `write` refuses to write data that does not match the manifest, and `read_split` refuses a file whose checksum is not the manifest's.
3. `freeze` refuses to record different data under a version that is already frozen.

To change the data, for example after the Product Owner's review or a policy change that changes a label: change the rules or the generator, bump `GENERATOR_VERSION` in `generator.py`, run `freeze`, update the numbers on this page, and open a pull request. A new version after US-04 has started tuning means the evaluation starts again on the new data, and the final report says so.

## Known limitations

- **The labels come from rules the team wrote.** A model can score well by learning those rules back. Held-out scenarios and the external AgentDojo benchmark offset this (ADR-008).
- **Label leakage.** `expected_outcome`, `rule`, `failure_mode`, `use_case` and `split` are labels and bookkeeping, never model inputs. The Sprint 0 schema review lists `rule` and `expected_outcome` under the policy context feature family; for US-04 that family must come only from what the gateway knows before the risk engine runs, such as the amount against the limits or the hard rules the policy reported.
- **Simpler than real traffic.** One agent, one currency, short sessions, and session times on a fixed two-hour grid, so time-of-day features mean little. Patterns that span sessions, such as a slow burst over several days, are not present.
- **The second R7 pattern never occurs.** With today's bank policy each of Vera's tasks allows at most one of her high-impact tools, so she cannot use three new ones in a session. The labeller implements the pattern and the tests cover it.
- **Few disputes.** The bank has seven open disputes, five of them opened before the timeline starts, so `close_dispute` appears in only a few sessions.
- **Untrusted content is a label only.** The rows say which arguments came from untrusted content; the poisoned email and document texts themselves are US-02b.4 (#151).
- **Prompt injection is narrow.** It covers refund destinations and amounts and the account to freeze, not other tools.

## Product Owner review

Task US-21.2 (#154): the Product Owner checks 50 events by hand in [review-sample.md](review-sample.md). The sample is drawn at random, rule by rule: five events for each of R1 to R8 and ten allowed events. Sessions behind the R5, R7 and R8 events are listed in full under the table. A disagreement is fixed in the rules or the generator and a new version is frozen; labels are never edited by hand.
