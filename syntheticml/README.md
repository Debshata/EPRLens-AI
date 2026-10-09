# EPRLens AI — Synthetic Data & ML Work Package

> **SYNTHETIC — EPRLens Demo.** EPRLens AI is a pre-compliance and EPR-intelligence aid. It does not replace CPCB, file returns, issue certificates, certify recyclers, guarantee compliance or give legal advice.

Start here:

1. `docs/DECISIONS-REQUIRED.md` — every open decision (DS-01 … DS-25) with options and recommendations.
2. `docs/epr-domain-summary.md` — what the EPR handbook says, and what needs official verification.
3. `docs/dummy-entities.md` — the shared entity master used by every part of the project.
4. `synthetic-data/README.md` — how to regenerate and test.

Status (2026-10-09): entity master and full synthetic dataset generated (`synthetic-data/MANIFEST.json`, `docs/synthetic-data-provenance.md`). The full output lives in `data/generated/` (git-ignored); committed samples are in `synthetic-data/outputs/sample/`. Next phase: ML training scripts (`ml/scripts/`).
