# Committed samples — SYNTHETIC — EPRLens Demo

- `pdf/`, `json/`: 20 of the 1,000 generated invoice documents and their ground truth (one per layout, the EcoFizz 0.5 MT vs 500 MT demo anomaly, and one per test case where room allows).
- `csv/`: small slices of the full tables, mostly the demo company COMP_0001 (Jan–Mar 2026).
- `illustrative/`: the hand-composed example from the entity phase (99-range IDs).

The full dataset lives in `data/generated/` (git-ignored). Regenerate it with `python synthetic-data/generate.py --config synthetic-data/config.yaml --out data/generated`.
