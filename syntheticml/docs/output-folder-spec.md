# Output Folder Specification

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo. Repository root = `syntheticml/`.

```
synthetic-data/
  README.md                  run instructions (fresh clone)
  requirements.txt           pinned dependencies (DS-19)
  config.yaml                full-dataset config (PROPOSED values)
  config/entity_seed.yaml    entity-master config (counts, distributions, seed)
  generate.py                full pipeline CLI            [after approval]
  generate_entities.py       entity-master CLI (pilot implemented)
  schemas/
    spec.py                  single source of field definitions
    build_schemas.py         writes *.schema.json from spec.py
    *.schema.json            JSON Schema (draft 2020-12) per table
  generators/
    identifiers.py           fake IDs, GSTIN-like values, invoice numbers
    geo.py                   states, GST state codes, cities, PIN prefixes
    names.py                 fictional name parts + real-brand denylist
    archetypes.py            industry → product/component archetypes
    entities.py              entity-master generation
    (sales.py, transactions.py, events.py, invoices.py, recycling.py,
     scenarios.py, anomalies.py, render_pdf.py)              [after approval]
  templates/invoices/        L01–L12 layout modules         [after approval]
  masters/                   entity CSVs + entity_manifest.json
  demo/demo_company.json
  seed/*.sample.json         small DB seed fixtures
  outputs/
    sample/                  committed small samples (≤ 20 PDFs/JSON, small CSVs)
  tests/                     generator unit tests
  MANIFEST.example.json

data/generated/              git-ignored full outputs
  csv/  invoices/pdf/  invoices/json/  manifests/MANIFEST.json

ml/scripts/train_forecast.py, train_anomaly.py   [after approval]
ml/evaluation/forecast_metrics.json, anomaly_metrics.json  [produced by runs only]
tests/synthetic/             cross-cutting integrity tests
frontend/src/lib/mocks/      contract-identical fixtures (same IDs)
backend/test-events/         Lambda test events (same IDs)
docs/                        this reference pack
```

Git policy: commit code, schemas, configs, docs, masters of the **test pack**, samples, manifests (example), tests. Do **not** commit `data/generated/`, the 1,000 PDFs, model checkpoints, secrets.
