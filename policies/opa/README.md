# Bank policy as code

The bank's deterministic rules, written in Rego for Open Policy Agent: tool permissions per task, refund limits, the bulk export ban and data-origin rules.

| | |
|---|---|
| First built in | Sprint 2 |
| Stories | US-02a, US-02b, US-07 (Should) |
| Requirements | FR-03, FR-04, FR-06, FR-17; NFR-01, NFR-09 |

## What belongs here

- `.rego` policy files and their `_test.rego` unit tests
- Policy data such as the refund limits confirmed in `data/synthetic/labelling-rules.md`

## Rules for this folder

- Every rule has a unit test, including boundary values. Run them with `opa test policies/opa -v`.
- CI runs the policy tests automatically once the first `.rego` file exists.
- Bundles are versioned; the version is recorded in every audit event.

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
