# Model training

Trains the risk model on the labelled synthetic dataset.

| | |
|---|---|
| First built in | Sprint 2 |
| Stories | US-04, on the dataset from US-21 |
| Requirements | FR-07; NFR-08, NFR-14 |

## What belongs here

- Training scripts and notebooks (US-04)

The dataset generator, the labelling code and the dataset card are in `data/synthetic/dataset` (US-21), next to the schema and the labelling rules they implement. Read a split with `read_split` from `data.synthetic.dataset`; it checks the file against the frozen manifest first.

## Rules for this folder

- Labels follow `data/synthetic/labelling-rules.md`.
- The test split is frozen and its checksum recorded before any tuning.

Status: the dataset is ready (US-21). Training code arrives with US-04.
