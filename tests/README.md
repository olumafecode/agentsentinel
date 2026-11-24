# Tests

Unit tests for shared code today; cross-service, end-to-end and scenario tests as the services arrive.

| | |
|---|---|
| First built in | Every sprint |
| Stories | US-10, US-26, US-27, US-29 and each story's own tests |
| Requirements | NFR-09, NFR-14 |

## What belongs here

- `test_smoke.py`: the backlog loads and every requirement has a Must-have story
- `test_synthetic_schema.py`: the data schema and its rules
- `test_dataset_labeller.py`: the labelling rules R1 to R9 in code, including the worked examples
- `test_dataset.py`: the labelled dataset is the frozen one, split 70/15/15, with every failure mode in every split
- `test_dataset_matches_policy.py`: every label agrees with the bank policy in a real OPA server
- Integration, end-to-end and scenario tests from Sprint 1

## Rules for this folder

- Run everything with `python -m pytest -q` (on Windows, `py -m pytest -q`).
- CI runs the same command on every pull request; a failing test blocks the merge.
