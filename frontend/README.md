# EPRLens AI — Frontend

Next.js 15 (App Router) · React 19 · TypeScript (strict) · Tailwind CSS v4 · Radix primitives · Recharts · three.js (react-three-fiber).

> **Synthetic demo data.** Everything shown by default is generated test data about fictitious companies. EPRLens is pre-compliance decision support — not a CPCB filing, certification or legal advice.

## Run it (no AWS, no env vars)

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000  (mock mode)
npm run lint
npm run typecheck
npm run build
npm test             # unit + component tests (Vitest)
npm run test:e2e     # Playwright demo flow, desktop + mobile (uses installed Google Chrome)
```

A fresh clone runs entirely on bundled fixtures. Node 20+ recommended (developed on Node 22).

## Mock mode ⇄ live mode

| | Mock (default) | Live |
|---|---|---|
| Switch | `NEXT_PUBLIC_API_MODE=mock` (or unset) | `NEXT_PUBLIC_API_MODE=live` |
| Data | `src/lib/mocks/*.json` + real client-side logic (CSV parsing, unit conversion, reconciliation, scenario math) | `/api/*` route handlers → AWS Lambda / S3 |
| AWS keys | none | **server-only** env vars (see `.env.example`), never sent to the browser |

Only the adapter changes — components import `api` from `src/lib/api-client.ts` and are identical in both modes. Live mode steps:

1. `cp .env.example .env.local` and fill the server variables (`UPLOADS_BUCKET`, `LAMBDA_*`, AWS credentials/role).
2. Set `NEXT_PUBLIC_API_MODE=live` and restart `npm run dev`.
3. Uploads: browser → short-lived presigned S3 PUT (minted by `/api/uploads/presign`) → `/api/*` invokes the Lambda with the S3 key.

Request/response shapes: [`../docs/frontend-api-contracts.md`](../docs/frontend-api-contracts.md). Every `/api/*` response is validated with the zod schemas in `src/lib/contracts.ts`; a backend that drifts fails loudly (`contract_mismatch`) instead of rendering wrong numbers.

## Pages

| Route | What the user does |
|---|---|
| `/` | Understand the problem, enter the demo |
| `/onboarding` | Company name, role(s), industry, turnover, description → potential applicability (“requires verification”) |
| `/app/workspace` | Upload CSV, digital invoice PDF, packaging photo; run reconciliation |
| `/app/dashboard` | Totals, forecast, material mix, material-flow (3D + table), anomalies, rule-based “Why?” |
| `/app/review` | Findings, side-by-side original values, accept/reject with reason, audit history, CSV export |
| `/app/simulator` | Change g/unit or units → before/after kg and tonnes |

Demo script: [`../docs/demo-flow.md`](../docs/demo-flow.md) (3 minutes).

## Layout

```
src/app/            routes (+ api/ route handlers for live mode)
src/components/     ui/ layout/ data/ upload/ dashboard/ reconciliation/ scenario/ three/ onboarding/ marketing/
src/lib/            contracts.ts api-client.ts mock-adapter.ts live-adapter.ts formatters.ts units.ts
                    reconcile.ts scenario-math.ts review-store.ts material-flow.ts app-state.tsx mocks/
tests/              unit/ components/ e2e/
public/samples/     bundled synthetic sample files (CSV, one invoice PDF, three illustrative images)
```

## Design rules enforced in code

- “Synthetic demo data” badge wherever fixtures are shown; quantities in kg with tonnes from 1,000 kg.
- The image result is a **probable material**, never an official EPR/legal category; uncertain results are visually different and ask for confirmation.
- Status vocabulary: confirmed / declared / estimated / needs review / unknown / reviewed — shown with text + icon + border style (never colour alone).
- Original values are never overwritten; a correction is stored beside them with a reason in an append-only history (localStorage in mock mode).
- No risk score and no “compliant” status. Model outlier scores are labelled “not a probability of non-compliance”. The forecast shows no uncertainty interval because the model does not return one.
- Every error says what the user can do next. 3D is optional: reduced-motion / no-WebGL / small screens use the full 2D view and table.
- No invented success states: results appear only after the adapter returns them.

## Mock-mode limits (by design)

Mock mode recognises the **bundled sample files** by name (it will not pretend to classify or parse arbitrary uploads); CSV files are genuinely parsed and validated in the browser. Use **Reset demo** in the sidebar to clear local state.

## Known notes

- `npm audit` reports advisories in dev tooling dependencies of Next 15 (PostCSS/braces); the proposed fix is a major upgrade (Next 16) which is out of scope here.
- In `npm run dev` with React StrictMode, react-three-fiber can log “Attempted to synchronously unmount a root” warnings. These are dev-only; the production build and Playwright runs are clean.
