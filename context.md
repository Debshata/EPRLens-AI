# EPRLens AI — Project Context (Single Source of Truth)

> **Document status:** DRAFT v0.4 — proposed enhancements awaiting owner approval
> **Created:** 2026-10-08
> **Last updated:** 2026-10-10
> **Owner / approver:** Project owner (the user). No other party may approve decisions.
> **Implementation status (2026-10-10):** Built and deployed — synthetic dataset and models, image classifier, 7 AWS Lambdas + S3 + DynamoDB in ap-south-1, Next.js frontend hosted on Lambda. See `README.md`. (This document's older sections describe the original plan; Supabase/Vercel were not used.)

### Change log
| Version | Date | Change |
|---|---|---|
| v0.1 | 2026-10-08 | Initial draft from owner brief. |
| v0.2 | 2026-10-08 | Owner restricted AWS to **S3, Lambda, DynamoDB only** (D051). Owner added **Supabase and Vercel** to the stack (D052). Textract, Bedrock, API Gateway, Amplify, CloudWatch, ECR and AWS Budgets removed from the plan. Affected decisions marked superseded; new pending decisions D053–D060 added; new contradictions C11–C15 added. |
| v0.3 | 2026-10-08 | Added Sections 41–45: EPR Domain Knowledge (from owner-supplied guide), ML/DL with Real Data (Kaggle), ML/DL with Synthetic Data (incl. synthetic invoices), AWS Engineer Runbook, Frontend Design Specification (green-adapted design system + Three.js waste-material components). Owner decisions recorded: D024 (synthetic invoices, no public invoice dataset), D035 (Three.js used for waste-material aesthetics — components still need approval), D037 (design system adopted with orange → green), D064 (EPR guide as domain reference). New pending D061–D069; new contradictions C16–C20. C1 updated with guide facts. |

| v0.4 | 2026-10-08 | Added proposal Sections 46–52 harmonizing four revised developer runbooks: material-flow digital twin, evidence-linked reconciliation, packaging optimization, synthetic tests, contracts, role-specific handoffs and acceptance criteria. Added pending decisions D070–D081 and tensions C21–C26. Existing approvals unchanged; features are not silently approved. |
| v0.5 | 2026-10-09 | Owner approved synthetic-data decisions DS-01…DS-25 (see `syntheticml/docs/DECISIONS-REQUIRED.md`) with safeguards; D024/D061 detail resolved (1,000 PDFs, ReportLab); full dummy entity master generated in `syntheticml/`. Decision Log entry DS-01–DS-25 appended. |
| v0.6 | 2026-10-09 | Owner approved full synthetic dataset generation. Generated in `syntheticml/` (generator 1.0.0): 174,224 transactions, 46,501 invoices, 718,353 material events, 14,649 recycling rows, 3,010 labelled anomalies + 693 hard negatives, exactly 1,000 PDFs + 1,000 JSON (12 ReportLab layouts). Companies gained a fake GSTIN-like field. ML training not started (D027/D028/D029 still pending). |
| v0.7 | 2026-10-09 | Synthetic ML phase run by owner instruction: forecast-v1 (XGBoost chosen on validation MAE; test R² 0.986, MAE −39 % vs last value) and anomaly-v1 (rules + Isolation Forest; test F1 0.912, FPR 0.0038). AWS-ready artifacts (ONNX forecast, joblib anomaly), notebook, AWS engineer PDF and tests committed in `syntheticml/` (commit a0afd74). D027/D028/D029 resolved for the synthetic MVP (see decision log). |
| v0.8 | 2026-10-10 | Implementation phase: frontend (6 pages, mock + live modes), 7 Lambdas (classify-image, parse-invoice, reconcile, forecast, detect-anomaly, scenario-engine, company-data), AWS scripts, public site on Lambda Function URL. D051 (S3/Lambda/DynamoDB only) respected; a Lambda Function URL (a Lambda feature) hosts the UI. Supabase and Vercel not used. `company-data` is a 7th Lambda beyond the runbook's six. |

---

## How to read this document

Every substantive statement carries one of these status tags:

| Tag | Meaning |
|---|---|
| **[CONFIRMED]** | Stated as a requirement by the project owner. Treat as binding. |
| **[PROPOSED]** | Suggested by the owner or by an assistant but **not yet approved**. Do not implement. |
| **[PENDING Dxxx]** | An open decision. Links to the Pending Decisions list (Section 7). Do not implement until it appears in the Decision Log (Section 38). |
| **[SUPERSEDED]** | An earlier item made obsolete by an approved decision. Kept for traceability. |
| **[ASSISTANT NOTE]** | An observation, risk or contradiction raised by the assistant. Not a requirement. |
| **[TBD]** | Value unknown. Never replace with a guessed or fabricated value. |

**Rules for any session continuing this project:**
1. Read Section 40 (Development Protocol), Section 7 (Pending Decisions) and Section 38 (Decision Log) before doing anything.
2. Never treat a [PROPOSED] item or an assistant recommendation as approved.
3. When the owner approves a decision, append it to Section 38 and mark it resolved in Section 7. Never delete or rewrite earlier Decision Log entries.

---

## 1. Project Overview

- **Name:** EPRLens AI **[CONFIRMED]**
- **Working tagline:** "See your waste. Predict your liability. Reduce your risk." **[PROPOSED — working only; final copy is PENDING D038]**
- **Project type:** AI-powered EPR (Extended Producer Responsibility) compliance-risk, waste-intelligence, document-intelligence and forecasting platform for Indian businesses. **[CONFIRMED]**
- **Context:** Built for an environmental hackathon focused on problems including waste. **[CONFIRMED]**
- **Must visibly and meaningfully use AWS.** **[CONFIRMED]**
- **AWS services allowed:** Amazon S3, AWS Lambda, Amazon DynamoDB **only**. **[CONFIRMED — D051]**
- **Additional platforms:** Supabase and Vercel, used where required. **[CONFIRMED — D052; exact roles PENDING D053]**
- **AWS budget:** approx. USD 25 total. **[CONFIRMED]**
- **Build window:** short; deliverable is a functional MVP. Exact deadline **[TBD — see Open Question Q1]**.

## 2. Problem Statement

**[CONFIRMED]** Indian producers, importers and brand owners (PIBOs) subject to EPR obligations often discover data problems (wrong quantities, misclassified materials, invoice mismatches, missing records, recycling shortfalls) late in the compliance cycle — typically when preparing formal submissions. By then corrections are costly and rushed.

There is limited tooling that lets a business, before formal submission:
- understand whether and how EPR is likely to apply to it,
- validate its own records against source documents,
- detect suspicious or implausible data,
- forecast upcoming packaging / waste exposure,
- and simulate the effect of packaging-reduction decisions.

## 3. Product Vision

**[CONFIRMED]** EPRLens AI is an **intelligence and pre-compliance layer** that helps businesses understand, validate, forecast and prepare their EPR data **before** formal regulatory submission.

**[CONFIRMED] EPRLens AI is NOT:**
- a CPCB replacement or a replacement for any government portal,
- a legal compliance guarantee,
- an EPR certificate issuer,
- a recycler certification authority,
- a regulatory filing portal.

All user-facing outputs must reflect this positioning (disclaimer wording is PENDING D038).

## 4. Target Users

**[PROPOSED — prioritisation PENDING D010]** Candidate segments:
- Small and mid-sized producers
- Importers
- Brand owners
- EPR consultants
- Compliance firms
- Sustainability teams

[ASSISTANT NOTE] The choice of primary persona affects UX (single company vs multi-client), user roles (D034), pricing (D039) and demo story (D012).

## 5. Core Value Proposition

**[CONFIRMED]** A business should not discover EPR-related data problems only at the end of the compliance cycle. EPRLens AI detects issues earlier by combining:
- Computer vision (probable material classification)
- Machine learning (forecasting)
- Anomaly detection
- Document AI (invoice extraction — method PENDING D055)
- Generative AI (explanations, structured extraction — provider PENDING D054)
- Deterministic rule-based logic (applicability, validation, scoring)
- Serverless infrastructure: AWS (S3, Lambda, DynamoDB) + Supabase + Vercel

**[CONFIRMED] MVP positioning statement:** "An AI-powered EPR intelligence platform that helps businesses identify potential EPR exposure, validate business records, forecast packaging volumes, detect suspicious data and simulate waste reduction decisions."

## 6. Approved Scope

### 6.1 Confirmed MVP feature candidates **[CONFIRMED as the scope ceiling — no additions without approval]**

| # | Feature | Notes |
|---|---|---|
| F1 | Company onboarding | |
| F2 | AI-assisted business profile extraction | NL description → structured attributes (LLM provider PENDING D054) |
| F3 | EPR applicability rules engine | Deterministic |
| F4 | Packaging / waste image classification | Probable material only; inference on Lambda |
| F5 | CSV upload | Transaction data |
| F6 | Invoice upload | |
| F7 | Invoice extraction | Textract removed; method PENDING D055 |
| F8 | Data validation | Deterministic rules |
| F9 | Anomaly detection | ML + rules |
| F10 | Packaging / waste forecasting | ML |
| F11 | EPR risk score | Deterministic preferred |
| F12 | GenAI explanation | Bedrock removed; provider PENDING D054 |
| F13 | What-If simulator | Deterministic preferred |
| F14 | Dashboard | |
| F15 | Basic commercial pricing presentation | |

[ASSISTANT NOTE] Whether all 15 fit the build window, and in what priority order, is itself a decision — **PENDING D050 (feature prioritisation / cut line)**. D051 makes F2, F7 and F12 dependent on non-AWS choices (D054, D055).

### 6.2 Explicitly out of scope **[CONFIRMED]**
- Any regulatory filing, certificate issuance or recycler certification.
- Any claim of legal compliance certainty.
- Any AWS service other than S3, Lambda and DynamoDB (D051).
- Any feature not in 6.1 unless approved.

## 7. Pending Decisions

Nothing below is approved unless its status says so. Recommendations are the assistant's and are **not** decisions.

| ID | Decision | Status | Assistant recommendation (not approved) |
|---|---|---|---|
| D001 | Final MVP page structure | Pending | Minimal set: Landing, Onboarding, Workspace (upload + scan + invoice), Dashboard (risk, forecast, anomalies, explanation, What-If), Pricing section on landing |
| D002 | Waste/packaging image dataset(s) | Pending | Present dataset cards (name, source, size, classes, licence, overlap) before any download |
| D003 | DL architecture | Pending | MobileNetV3 (smaller artefact helps fit Lambda zip limit, see D019) or EfficientNet-B0 |
| D004 | Forecasting target | Pending | Next-month total packaging kg per company (+ year-end projection by rolling forecast) |
| D005 | Synthetic anomaly ratio | Pending | ~3–5% of records, stratified by anomaly type |
| D006 | Authentication strategy | Pending | Supabase Auth now a candidate; Cognito excluded by D051. See Section 28 |
| D007 | Risk score weights | Pending | Deterministic weighted sum; weights proposed separately |
| D008 | **EPR regime(s) in scope** | Pending | Plastic packaging EPR only for MVP (see C1) |
| D009 | Image class taxonomy & label normalisation | Pending | Depends on D002 and D008 |
| D010 | Target user prioritisation / primary persona | Pending | Single SME producer/brand owner as demo persona |
| D011 | Final UX flow | Pending | Present after D001, D008, D010 |
| D012 | Final demo flow | Pending | Resolve ordering issues in C5 |
| D013 | Backend architecture | Pending — options changed by D051/D052 | Vercel (Next.js server routes) as API layer; AWS Lambda for ML inference, rules, validation and scoring. See Section 12 |
| D014 | Backend language split (TypeScript vs Python per function) | Pending | Python for ML Lambdas; TypeScript in Next.js server routes |
| D015 | AWS region | Pending | ap-south-1 (Mumbai) — the Bedrock/Textract availability constraint no longer applies |
| D016 | Database choice and data model | Pending — now coupled to D053 | See D053 |
| D017 | API design (endpoints, payloads, sync vs async) | Pending | REST via Next.js route handlers; spec to be proposed |
| D018 | Frontend hosting | Pending — Amplify excluded by D051 | **Vercel** (only remaining candidate; owner to confirm) |
| D019 | DL model serving method | Pending — ECR excluded by D051 | ONNX model + ONNX Runtime in a Lambda **zip** package / layer, if it fits the size limit; otherwise see C13 |
| D020 | Model serialisation formats | Pending | Likely ONNX for DL (because of D019); joblib for sklearn — decide after D003/D027 |
| D021 | Bedrock model choice | **SUPERSEDED by D051** | Replaced by D054 |
| D022 | Compliance-context grounding method for GenAI | Pending — Bedrock KB excluded | Static curated, owner-approved context file (stored in S3 or repo) injected into prompt |
| D023 | Textract API choice | **SUPERSEDED by D051** | Replaced by D055 |
| D024 | Invoice sample source | **APPROVED — see Decision Log** (synthetic invoices only; generation spec PENDING D061) | — |
| D025 | Synthetic data specification | Pending | Full spec to be presented before generation |
| D026 | Synthetic train/validation/test methodology | Pending | Time-based split for forecasting; company-held-out check |
| D027 | Final forecasting model | Pending | Only after comparison results are shown |
| D028 | Forecasting metrics & baselines | Pending | MAE, RMSE, R² vs naive last-value & seasonal-naive |
| D029 | Anomaly detection feature set & threshold | Pending | Isolation Forest + deterministic rules; compare |
| D030 | EPR applicability rules & source references | Pending | Rules only from owner-approved regulatory references |
| D031 | Risk score bands/thresholds | Pending | — |
| D032 | What-If scenarios in MVP | Pending | Start with 1–2 (reduce packaging weight %, change material) |
| D033 | Data storage & retention policy | Pending | Private S3 with lifecycle expiry on uploads (lifecycle rules are an S3 feature) |
| D034 | User roles / multi-tenancy | Pending | Single role for MVP |
| D035 | Three.js usage | **APPROVED in principle — see Decision Log** (waste-material aesthetic components; each component still needs approval under D062) | — |
| D036 | Chart library and chart types | Pending | Options to be presented |
| D037 | Branding & visual design | **Visual system APPROVED in principle — see Decision Log** (owner design system, orange → green). Exact tokens PENDING D063; logo/brand name styling still pending | — |
| D038 | Copywriting incl. tagline and disclaimers | Pending | — |
| D039 | Pricing tiers & amounts | Pending | Placeholders only (Section 33) |
| D040 | Business-model presentation format | Pending | — |
| D041 | Project folder structure | Pending | See Section 29 |
| D042 | Git initialisation & remote hosting | Pending | Needed anyway for Vercel Git deployments |
| D043 | Infrastructure provisioning tooling | Pending — options changed by D051 | SAM / CDK / Serverless Framework all deploy via **CloudFormation** (not an allowed service). Candidates: AWS CLI scripts, Terraform, or manual console. Recommend AWS CLI scripts committed to repo |
| D044 | AWS cost guardrails | Pending — AWS Budgets excluded by D051 | Lambda reserved concurrency caps, S3 lifecycle expiry, DynamoDB on-demand; billing alert only if owner allows (see D057) |
| D045 | Units convention | Pending | Store kg; display tonnes when ≥ 1,000 kg |
| D046 | Rate limiting approach | Pending — API Gateway throttling no longer available | Lambda reserved concurrency + simple rate limit in Vercel route handlers |
| D047 | Testing scope & tooling | Pending | — |
| D048 | How mock/synthetic data is labelled in the UI | Pending | Visible "Synthetic demo data" badge |
| D049 | Demo resilience | Pending | Live calls + pre-seeded demo company fallback |
| D050 | Feature prioritisation / cut line among F1–F15 | Pending | — |
| D051 | AWS services restricted to S3, Lambda, DynamoDB | **APPROVED — see Decision Log** | — |
| D052 | Supabase and Vercel added to the stack | **APPROVED — see Decision Log** (exact roles in D053) | — |
| D053 | **Responsibility split between AWS and Supabase** (where business data, files and auth live) | Pending | See Section 13.3 — options A/B/C |
| D054 | **GenAI provider** (replacing Bedrock) | Pending | External LLM API called from Vercel server routes (e.g., Anthropic Claude API — small/fast model); or drop GenAI and use template text. Cost is outside AWS credits |
| D055 | **Invoice extraction method** (replacing Textract) | Pending | Digital-PDF text extraction + parsing in a Python Lambda; optional LLM structured extraction via D054 for messy layouts; scanned images out of scope for MVP |
| D056 | **How Vercel calls Lambda** | Pending | Vercel server routes invoke Lambda via AWS SDK with a least-privilege IAM user; alternative: Lambda Function URLs with IAM auth |
| D057 | **Implicit AWS dependencies** (IAM, CloudWatch Logs, billing alerts) | Pending | Allow IAM (mandatory to use AWS at all) and minimal CloudWatch Logs with 1-day retention (Lambda writes there by default); see C12 |
| D058 | Supabase & Vercel plan tiers and account ownership | Pending | Free tiers (Supabase Free, Vercel Hobby) — verify limits listed in Section 14.2 |
| D059 | Where application logs/audit trail live | Pending | DynamoDB table for important backend actions (keeps DynamoDB meaningful) |
| D060 | Where trained model artefacts and approved compliance context are stored | Pending | S3 (private bucket) |
| D061 | Synthetic invoice generation spec (count, layouts, variety, rendering tool, scanned-look images or not) | Pending | See Section 43.6 |
| D062 | Exact Three.js components (what each shows, where, performance budget) | Pending | T1 hero "Material Orbit" + T2 scan-result material viewer; see Section 45.8 |
| D063 | Exact green palette tokens replacing orange/gold | Pending | See Section 45.2 option table |
| D064 | Owner-supplied EPR guide as domain reference | **APPROVED — see Decision Log** | — |
| D065 | Three.js helper dependencies (@react-three/fiber, @react-three/drei) vs plain three | Pending | R3F + drei (idiomatic in React; not a "minor" dependency, so needs approval) |
| D066 | Semantic status colours for risk (high/medium/low) in a green-branded UI | Pending | Red for high, amber for medium, green for low — amber is orange-adjacent, so needs explicit approval (C18) |
| D067 | Lambda CPU architecture (arm64 vs x86_64) | Pending | arm64 (lower price per GB-second) if all wheels (onnxruntime, sklearn) are available for it |
| D068 | Plastic EPR obligation-estimation formula used for "gap" factors | Pending | Simplified formula in Section 41.6 — must be approved and labelled as an estimate |
| D069 | Real-world packaging hold-out test set (team-photographed Indian product packaging) | Pending | ~100 photos, test-only, never used for training; see Section 42.6 |
| D070 | Material-flow digital twin as principal proposed product narrative | Pending | Treat as evidence-backed aggregation, not a physical real-time sensor twin; Section 46 |
| D071 | Material flow ledger schema, accounting boundaries and reconciliation identities | Pending | Separate purchase, production, market placement, returns, collection, processing and fulfilment; Section 47 |
| D072 | Cross-document evidence graph and field-level provenance | Pending | Stable source/line/field references, matching confidence, review states; Section 48 |
| D073 | Packaging optimizer objective, constraints and scenario formulas | Pending | Start with weight-reduction comparison; no unsourced savings claims; Section 49 |
| D074 | Which additions fit within existing F1–F15 versus scope expansion | Pending | Map ledger to F8/F14 and optimizer to F13; explicit approval for new product functionality |
| D075 | Material flow interpretation: sold vs placed-on-market, exports, returns, imports and opening/closing inventories | Pending | Adopt transparent accounting definitions with counterexample tests |
| D076 | Invoice matching precedence, duplicate rules, tolerances and human correction workflow | Pending | Preserve originals; approvals and overrides are explicit |
| D077 | Evaluation and release gates for reconciliation, ledger accuracy, uncertainty, and optimization | Pending | Run synthetic-ground-truth tests plus manually checked samples, with no real-world generalisation claim |
| D078 | Digital twin visualization vs decorative Three.js scope | Pending | Accessible schematic and meaningful material-flow visualization; avoid unapproved hero replacement |
| D079 | Cross-team contracts, schema ownership, fixture versioning and integration cut line | Pending | Shared versioned JSON schema for all four work packages |
| D080 | Regulatory-rule versioning, official-source verification and unknown-status handling | Pending | Handbook is secondary reference; date and provenance on every rule |
| D081 | Business positioning and pricing claims for proposed reconciliation/optimizer scope | Pending | Validate customer value; no quantified savings promises without evidence |

## 8. Functional Requirements

Detailed behaviour of each is **PENDING** the decisions referenced. Only the confirmed intent is recorded here.

| ID | Requirement | Status |
|---|---|---|
| FR1 | User can create a company profile. | [CONFIRMED intent]; fields PENDING D016/D025 |
| FR2 | User can describe the business in natural language; AI extracts structured attributes; user can review/correct them. | [CONFIRMED intent]; "user can correct" is [PROPOSED]; provider PENDING D054 |
| FR3 | Deterministic rules determine *likely* EPR applicability from structured attributes. | [CONFIRMED]; rules PENDING D030 |
| FR4 | User uploads a product/packaging image; system returns probable material class + confidence. Never presented as official legal category. | [CONFIRMED] |
| FR5 | User uploads CSV transaction data; server-side validation. | [CONFIRMED intent]; schema PENDING D025 |
| FR6 | User uploads invoices; extraction returns fields with confidence and source reference. | [CONFIRMED]; method PENDING D055 |
| FR7 | Extracted invoice data is normalised then compared against internal records; mismatches flagged. | [CONFIRMED] |
| FR8 | Anomaly detection returns anomaly score, flag and (where rule-identifiable) suspected anomaly type. | [CONFIRMED intent] |
| FR9 | ML forecasts future packaging/waste quantity. | [CONFIRMED intent]; target PENDING D004 |
| FR10 | Dashboard shows an EPR Risk Score (0–100 proposed) with factor breakdown. | [PROPOSED]; PENDING D007/D031 |
| FR11 | GenAI explains why the score is high/low and suggests corrective actions, grounded in approved context. | [CONFIRMED intent]; PENDING D054/D022 |
| FR12 | What-If simulator recomputes projected material and risk impact deterministically. | [CONFIRMED intent]; scenarios PENDING D032 |
| FR13 | Basic pricing presentation. | [CONFIRMED intent]; PENDING D039/D040 |

## 9. Non-Functional Requirements

**[CONFIRMED]**
- AWS usage limited to S3, Lambda, DynamoDB (D051).
- AWS total spend ≤ ~USD 25; avoid always-on infrastructure.
- Functional MVP over placeholder complexity; any mock behaviour must be explicitly labelled.
- Business rules separated from AI outputs; LLM never sole authority on compliance.
- Reproducible ML (seeds, versioned data, documented experiments).
- Centralised configuration; no secrets in frontend; environment variables for config (Vercel environment variables for the web app; Lambda environment variables for functions).
- TypeScript strict mode where practical.
- API input validation; logging of important backend actions (location PENDING D059).
- Minimal dependencies.
- No fabricated metrics, no fabricated regulatory certainty.

**[PROPOSED — not yet approved]**
- Performance targets (e.g., image classification < 5 s warm, invoice extraction < 30 s) — [TBD]. Must respect Vercel function duration limits (D058).
- Accessibility baseline — [TBD].
- Responsive down to tablet/mobile width — [TBD].

## 10. User Experience

### 10.1 Current conceptual flow **[PROPOSED — NOT FINAL; PENDING D011]**
1. Create company profile.
2. Describe business in natural language.
3. AI extracts structured attributes.
4. Rules determine likely EPR applicability.
5. Upload product/packaging image.
6. DL model classifies broad material/waste type.
7. Upload CSV / transaction data.
8. Upload invoices.
9. Document AI extracts invoice information.
10. Compare extracted data against internal records.
11. Anomaly detection flags suspicious quantities/patterns.
12. ML forecasts future packaging/waste quantities.
13. Dashboard calculates EPR Risk Score.
14. GenAI explains the score.
15. User runs a What-If simulation.
16. Dashboard shows estimated material reduction and risk impact.

### 10.2 UI direction **[CONFIRMED]**
- Modern B2B sustainability and risk-intelligence feel.
- Avoid: generic hackathon styling, excessive gradients, excessive animation, overcomplicated 3D, government-portal aesthetics, too many dashboard cards, fake enterprise complexity.

### 10.3 Candidate pages **[PROPOSED — PENDING D001]**
Landing, Company onboarding, Dashboard, Packaging scan, Data upload, Invoice intelligence, Forecasting, Risk analysis, What-If simulator, Settings. **Do not create all of these.** A minimum set must be proposed and approved.

### 10.4 Dashboard concept **[PROPOSED — PENDING D001/D036]**
- Candidate metrics: EPR Risk Score, current packaging volume, forecast year-end packaging, recycling recorded, estimated gap, number of anomalies, unresolved issues.
- Candidate charts: monthly packaging trend, forecast curve, material composition, risk factor breakdown. Chart types not chosen.

## 11. Frontend Stack

**[CONFIRMED — intended stack]** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Three.js.

**Hosting:** Vercel **[PROPOSED — PENDING D018 confirmation; Amplify excluded by D051]**. Vercel is the native host for Next.js and supports server route handlers, which can act as the API layer (D013).

**Supabase client:** `@supabase/supabase-js` (and `@supabase/ssr` if Supabase Auth is chosen) **[PROPOSED — depends on D053/D006]**.

- Additional dependencies require approval unless minor supporting packages. A chart library is **not** minor → PENDING D036. The AWS SDK for JavaScript (Lambda client, possibly S3 client for pre-signed URLs) is needed if D056 = SDK invoke → treated as part of D056.
- Next.js App Router proposed (mechanical, but ties to D013/D018).
- shadcn/ui components likely needed: Card, Dialog, Sheet, Table, Tabs, Progress, Badge, Tooltip, Select, Input, file upload, charts. **[PROPOSED]**

**Three.js [CONFIRMED constraint]:** only where it meaningfully improves the experience; any component must be described (exactly what it shows) and approved first → PENDING D035. Candidate ideas: circular-economy visual, packaging lifecycle, waste flow animation, EPR "digital twin".

[ASSISTANT NOTE — C3] If D035 resolves to "no Three.js", it should be removed from the stack.

## 12. Backend Architecture

**[CONFIRMED preferences]** Serverless where possible; TypeScript or Python per function; AWS Lambda. API Gateway is **no longer available** (D051). **Final structure not chosen — PENDING D013/D014/D056.**

**[PROPOSED — options for D013]**
- **A. Vercel server routes as the API layer + AWS Lambda for compute-heavy / Python work** (image inference, anomaly detection, forecasting, invoice parsing, rules & risk scoring). Vercel routes authenticate the user, validate input, then invoke Lambda. Keeps AWS central and visible; Lambdas stay private.
- **B. Lambda Function URLs as the public API** (browser calls Lambda directly); Vercel serves only the frontend. More AWS-visible; harder to secure (auth must be implemented inside every Lambda); CORS management.
- **C. Vercel server routes for almost everything; Lambda only for DL image inference.** Simplest; AWS role becomes thin — risks failing the "meaningfully use AWS" requirement (C11).

Assistant recommendation: **A** — not approved.

Async processing (e.g., S3 upload → Lambda trigger via S3 event notification, which is an S3 feature) vs synchronous invocation is part of D017.

## 13. Cloud Architecture

### 13.1 AWS services **[CONFIRMED — D051: only these three]**

| Service | Candidate role | Cost exposure | Status |
|---|---|---|---|
| Amazon S3 | Uploads (images, CSV, invoices), model artefacts, approved compliance-context files, static assets | Low | **Approved service**; exact role PENDING D053/D060 |
| AWS Lambda | Inference (DL, anomaly, forecast), rules engine, validation, risk scoring, What-If, invoice extraction normalisation | Low | **Approved service**; exact functions PENDING D013 |
| Amazon DynamoDB (on-demand) | Companies, records, results — exact scope PENDING D053 | Low | **Approved service**; data model PENDING D016/D053 |

### 13.2 Removed AWS services **[SUPERSEDED by D051]**
| Service | Was proposed for | Replacement |
|---|---|---|
| Amazon Textract | Invoice extraction | D055 (Lambda-based parsing and/or LLM) |
| Amazon Bedrock | GenAI | D054 (external LLM provider) |
| Amazon API Gateway | Public API | Vercel route handlers or Lambda Function URLs (D013/D056) |
| AWS Amplify | Frontend hosting | Vercel (D018) |
| Amazon CloudWatch | Logs/metrics | DynamoDB or Supabase logging (D059); see C12 on implicit CloudWatch Logs |
| Amazon ECR | Lambda container images | Lambda zip package/layers (D019) |
| AWS Budgets | Spend alerts | See D044/D057 |
| AWS CloudFormation (via SAM/CDK) | IaC | AWS CLI scripts / Terraform / console (D043) |

### 13.3 Supabase and Vercel **[CONFIRMED as platforms — D052; roles PENDING D053]**

| Platform | Candidate roles |
|---|---|
| **Vercel** | Next.js hosting (D018); server route handlers as API layer (D013); environment variables / secrets for the web tier; preview deployments from Git |
| **Supabase** | Candidate: Auth (D006); candidate: Postgres for relational business data; candidate: Storage (overlaps S3); candidate: Row-Level Security for tenant isolation |

**Options for D053 — responsibility split [PROPOSED]:**

| Option | Business data (companies, transactions, invoices) | Files | Auth | Analysis results / logs | Consequence |
|---|---|---|---|---|---|
| **A** | Supabase Postgres | S3 | Supabase Auth | DynamoDB | Best fit for tabular/time-series queries and aggregations; DynamoDB used for results and audit log; two databases to manage |
| **B** | DynamoDB | S3 | Supabase Auth | DynamoDB | AWS most visible; Supabase only for auth; aggregations (monthly totals, trends) must be pre-computed in Lambda because DynamoDB has no ad-hoc SQL |
| **C** | Supabase Postgres | Supabase Storage | Supabase Auth | Supabase | Simplest single platform; AWS shrinks to Lambda compute + model artefacts in S3; DynamoDB effectively unused — conflicts with D051 intent and "meaningfully use AWS" (C11) |

Assistant recommendation: **A or B** — not approved. A is easier to build; B is stronger for the AWS story.

### 13.4 Architecture diagram
[TBD] — to be produced after D013, D015, D053 and D056 are approved.

## 14. Cost Constraints

### 14.1 AWS **[CONFIRMED]**
- Budget ≈ USD 25 total; only S3, Lambda, DynamoDB.
- Before enabling any service with meaningful cost: (1) why required, (2) estimated usage, (3) cost risk, (4) cheaper alternative, (5) wait for approval.
- Train ML locally or in Colab; deploy cheaply (S3 + Lambda).

**[PROPOSED guardrails — PENDING D044]**
- DynamoDB on-demand mode.
- S3 lifecycle expiry on upload prefixes; block public access on all buckets.
- Lambda reserved concurrency caps per function to bound runaway invocation cost.
- Cache results by file hash to avoid repeated inference/extraction.
- Tear-down checklist after the hackathon.

[ASSISTANT NOTE] With Textract and Bedrock removed, expected AWS spend for a hackathon workload on S3/Lambda/DynamoDB is likely very low; exact estimate [TBD] against current pricing pages.

### 14.2 Non-AWS costs **[PENDING D054, D058]**
- **LLM API (D054):** not covered by AWS credits. Budget for it is unknown → Open Question Q11.
- **Supabase:** free tier proposed. [ASSISTANT NOTE] Free-tier projects may be paused after a period of inactivity — must be checked before the demo date. Limits to verify at decision time.
- **Vercel:** Hobby tier proposed. [ASSISTANT NOTE] Hobby tier terms restrict commercial use and impose serverless function duration limits; verify current limits at decision time (matters for invoice extraction and any synchronous Lambda call chains).

Cost figures must cite current pricing pages at the time of the request; none are fixed here.

## 15. Data Strategy

**[CONFIRMED]** Hybrid strategy because real company-level EPR operational datasets are not publicly available:
- **Real public data** — primarily for perception tasks (image classification; possibly invoice extraction testing).
- **Synthetic data** — for EPR-specific entities (companies, products, packaging, transactions, invoices, recycling records, anomalies).

**[CONFIRMED]** Synthetic data must be labelled as such wherever shown (method PENDING D048).

[ASSISTANT NOTE — C7] Forecasting and anomaly models trained and evaluated on synthetic data largely learn the generator's own equations. Metrics demonstrate pipeline correctness, **not** real-world accuracy.

## 16. Public Datasets

**[CONFIRMED rule]** No dataset may be downloaded or combined until the owner has seen: name, source, size, classes, licence, usefulness, limitations, overlap.

Candidate types:
- Kaggle waste / garbage classification image datasets **[PROPOSED]**.
- ~~Public invoice OCR datasets~~ **[EXCLUDED by owner — D024]**. Invoices are generated synthetically (Section 43.6).

Candidate classes **[PROPOSED]**: Plastic, Paper, Cardboard, Metal, Glass, Battery, Trash/Other. Label normalisation required (D009).

Dataset register: **see Section 42.2** (detailed candidate cards, nothing downloaded).

[ASSISTANT NOTE — C2] Most public garbage datasets show discarded waste items, not product packaging as sold. Domain mismatch should be expected and evaluated.

## 17. Synthetic Data Strategy

**[CONFIRMED requirements]**
- Not random noise; must encode realistic relationships:
  - company size → transaction volume,
  - product sales → packaging generated,
  - packaging weight × units = material volume,
  - seasonality affects monthly sales,
  - recycling normally ≤ generated material,
  - different growth patterns across companies,
  - industry-specific packaging profiles.
- Controlled random noise.
- Injected anomalies with known ground truth. Candidate types: decimal errors, extra-zero errors, wrong material classification, duplicate invoices, missing fields, unusual monthly spikes, implausible quantities, invoice-vs-transaction mismatch.
- **Before generation** present: dataset size, distributions, assumptions, equations, anomaly ratio, anomaly types, train/val/test methodology → wait for approval (D005, D025, D026).

**Candidate schemas [PROPOSED — NOT LOCKED]**

*Company:* company_id, company_name, industry, turnover_cr, manufacturer, importer, brand_owner, annual_units, states_operated, epr_registered, waste_stream

*Packaging transaction:* transaction_id, company_id, date, product_id, units_sold, packaging_material, packaging_category, weight_per_unit_g, total_packaging_kg, supplier_id, state

*Recycling:* company_id, month, waste_generated_kg, waste_collected_kg, waste_recycled_kg, recycler_id, recycler_registered

*Invoice validation:* invoice_id, company_id, supplier_id, material, invoice_quantity_kg, recorded_quantity_kg, invoice_date, invoice_amount, is_anomaly, anomaly_type

*Other candidate entities:* products, recyclers, recycling-fulfilment records.

[ASSISTANT NOTE] A "products" schema is referenced (product_id) but not defined; needs proposal under D025. Storage location of synthetic data depends on D053 (Postgres vs DynamoDB).

**Detailed generator design, equations, anomaly mechanics, synthetic invoices and splits: see Section 43.** Additional EPR-grounded fields suggested by the domain guide (registered vs unregistered buyer, plastic category I–IV, pre/post-consumer, recycled content %, exports, MSME flag) are proposed in Section 43.3.

## 18. ML Pipeline (Tabular)

### 18.1 Forecasting **[PROPOSED]**
- Problem: predict future packaging/waste quantity per company.
- Candidate target: next-month or year-end packaging quantity (D004).
- Candidate features: historical packaging quantity (lags), units sold, sales growth, month, seasonality, packaging weight, industry.
- Candidate models to compare: Linear Regression, Random Forest Regressor, XGBoost Regressor.
- Metrics: MAE, RMSE, R² (D028). Baselines [PROPOSED]: naive last-value, seasonal-naive.
- **Final model not selected until comparison results are shown (D027).**
- Results: **[TBD — no training performed]**.

[ASSISTANT NOTE] All inference must fit in Lambda **zip** packages/layers (no ECR). scikit-learn + numpy + scipy is already large; XGBoost adds more. Package size must be checked before D027 is finalised, or models exported to ONNX to share one runtime with the DL model.

### 18.2 Experiment documentation template **[CONFIRMED — required for every model]**
Problem statement · Dataset · Input features · Target · Preprocessing · Model · Hyperparameters · Training split · Validation strategy · Metrics · Baseline · Result · Limitation · Deployment method.
Unexecuted metrics must be labelled **TBD**.

### 18.3 Model deployment **[PROPOSED]**
Train locally/Colab → export artefacts → store in private S3 (D060) → load in Lambda at cold start. Serialisation **not chosen** until model and runtime are known (D020).

## 19. DL Pipeline (Image Classification)

**[PROPOSED]**
- Task: classify product/packaging image into a broad probable material class.
- Candidate architectures: MobileNetV3 or EfficientNet-B0 via transfer learning (D003).
- Output: predicted class + confidence score (top-k optional — [TBD]).
- **[CONFIRMED constraint]** Never claim the image determines the official/legal EPR category.
- Metrics [PROPOSED]: accuracy, macro-F1, per-class precision/recall, confusion matrix; baseline = majority class.
- Results: **[TBD]**.

**Serving under D051 [PROPOSED — PENDING D019/D020]:** Container images need ECR (excluded). PyTorch cannot fit the Lambda zip limit. Realistic path: export to **ONNX**, run with **ONNX Runtime** + Pillow + numpy in a Python Lambda zip/layer, model file loaded from S3 into `/tmp` at cold start. Package size must be measured before committing (see C13). Cold starts of several seconds likely.

[ASSISTANT NOTE — C1] A broad "plastic vs paper vs metal" classifier cannot determine plastic packaging EPR categories (rigid, flexible, multi-layered, compostable). UI must present it as an aid, with user confirmation.

## 20. Anomaly Detection Pipeline

**[PROPOSED]**
- Candidate model: Isolation Forest (runs in Lambda).
- Candidate inputs: invoice quantity, transaction quantity, monthly volume, packaging weight, supplier behaviour, historical quantity distribution.
- Outputs: anomaly score, anomaly flag, suspected anomaly type (rule-based where possible).
- **[CONFIRMED]** Compare ML detection with deterministic validation rules where appropriate.
- Evaluation [PROPOSED]: precision, recall, F1 against injected ground truth, per anomaly type; threshold PENDING D029.
- Results: **[TBD]**.

[ASSISTANT NOTE] Duplicate invoices, missing fields and decimal/extra-zero errors are naturally caught by rules; Isolation Forest adds most value for distributional outliers. Proposed design: rules first, ML second, both reported.

## 21. Document Intelligence

**Amazon Textract — [SUPERSEDED by D051].** Replacement method **PENDING D055**.

**[PROPOSED options for D055]**
- **A. Digital-PDF text extraction + rule-based parsing in a Python Lambda** (e.g., a PDF text library). Cheap, deterministic, AWS-hosted; works only for text-based PDFs with predictable layouts; no scanned images.
- **B. LLM structured extraction** (provider from D054) from PDF text or image. Handles varied layouts; external cost; confidence is not natively provided and must be approximated (e.g., cross-checks).
- **C. Open-source OCR (e.g., Tesseract) in Lambda.** Handles scans; binary packaging into a Lambda layer is fiddly and size-constrained; accuracy on invoices is modest.
- **D. A + B fallback.** Parse in Lambda first; call LLM only when parsing fails.

Assistant recommendation: **A** for MVP (with synthetic digital invoices, D024), **D** if time allows — not approved.

**[CONFIRMED regardless of method]**
- Candidate extracted fields: invoice number, date, vendor, quantity, description, amount.
- Normalise extracted data before validation (units, number formats, dates).
- Do not assume extraction is correct. For each field store: extracted value, confidence (or confidence proxy — method TBD), original source (file + location), validation result.
- Example: invoice 5,000 kg vs internal record 500 kg → high-risk mismatch.
- Mismatch tolerance thresholds: [TBD — part of D029/D030].
- Supported file types and max size: [TBD].

## 22. Generative AI

**Amazon Bedrock — [SUPERSEDED by D051].** Provider **PENDING D054**.

**[PROPOSED options for D054]**
- **A. External LLM API** (e.g., Anthropic Claude API) called from Vercel server routes or a Lambda. Good quality; small per-token cost billed outside AWS credits; API key stored server-side only.
- **B. Vercel AI SDK / AI Gateway** routing to an external model. Convenient in Next.js; still an external paid model; adds a dependency.
- **C. No LLM — templated explanations** generated deterministically from score factors. Zero cost, no hallucination risk; loses "GenAI" in the story; F2 (NL profile extraction) would become a structured form.
- **D. Small open-source model inside Lambda.** Unrealistic within Lambda zip size/memory limits for useful quality.

Assistant recommendation: **A** with a small/fast model, plus **C** as fallback template — not approved.

Candidate uses **[CONFIRMED intent]**:
- Convert business description → structured attributes (output validated against a schema; rules engine, not LLM, decides applicability).
- Explain EPR risk score.
- Summarise anomalies.
- Explain recommended corrective actions.

**[CONFIRMED constraints]**
- LLM must not fabricate regulations.
- Use retrieved or owner-approved compliance context only (method PENDING D022; context file stored in S3 or repo — D060).
- LLM is never the sole authority on compliance decisions.

[PROPOSED] Prompts receive only computed facts + approved context and are instructed to cite only that context. Prompt templates version-controlled.

## 23. EPR Rules Engine

**[CONFIRMED]** Deterministic rules for: EPR applicability, obvious validation errors, impossible values, risk score components.
**[PROPOSED]** Rules execute in AWS Lambda; rule definitions stored as versioned config (repo or S3).

**[PENDING D008, D030]** Which regulations and which rules. Rules must reference owner-approved sources.

**Domain basis:** Section 41 (summarised from the owner-supplied guide, D064). Key points for the rules engine:
- Five EPR regimes currently: plastic packaging, e-waste, batteries, tyres, used oil — each with its own CPCB portal.
- Glass/metal packaging, non-ferrous metals, ELV, C&D waste and (per the guide's preface) paper packaging are described as **under development**, not yet active EPR regimes.
- Plastic applicability roles: Producer (incl. MSME), Importer (products), Importer (raw material), Brand Owner (turnover > ₹50 Cr per the guide), Manufacturer, Seller/Trader, PWP. Multiple roles → separate registrations.
- The guide's self-assessment questionnaire (Sections A–F) is a ready template for F2/F3 attribute extraction and applicability rules (Section 41.3).

[ASSISTANT NOTE] The guide is a secondary source (a consultancy handbook, content current to ~Dec 2024). Thresholds, fees and targets should be cross-checked against official CPCB/MoEFCC notifications before being presented as rules (Q6 remains partially open).

Rule format [PROPOSED]: id, description, inputs, condition, output, severity, source reference, version.

## 24. Risk Scoring

**[PROPOSED]** EPR Risk Score 0–100, computed deterministically in Lambda.

Candidate factors **[PROPOSED]**: registration completeness, classification quality, invoice consistency, missing data, recycling gap, suspicious anomalies, forecasted fulfilment gap.

**[CONFIRMED]**
- Do not finalise weights (D007) or bands (D031) without approval.
- Do not train an ML model to reproduce manually created risk labels.
- Prefer deterministic scoring if more logical.

[PROPOSED] Fully explainable: each factor's raw value, normalised value, weight, contribution.

[ASSISTANT NOTE] Higher score = higher risk (proposed). "Recycling gap" and "forecasted fulfilment gap" need an obligation target source (Q6, C6).

## 25. What-If Simulator

**[CONFIRMED]** Derived values calculated deterministically unless ML is justified.

Candidate scenarios **[PROPOSED — PENDING D032]**: reduce packaging weight by X%, increase recycled content, increase recycling quantity, change packaging material, reduce packaging per unit.

**[CONFIRMED example]** Current projected 52.8 t; reduce unit packaging 15% → 44.9 t; reduction 7.9 t.
(Check: 52.8 × 0.85 = 44.88 ≈ 44.9; 52.8 − 44.88 = 7.92 ≈ 7.9 ✓)

Outputs [PROPOSED]: new projected quantity, material reduction, recalculated risk score and factor deltas. Computation location (Lambda vs Vercel route vs client) — part of D013.

## 26. Database / Data Model

**[PENDING D016, D025, D053]** No schema locked.

Candidate entities **[PROPOSED]**: Company, Product, PackagingTransaction, Invoice (+ ExtractedField), RecyclingRecord, Recycler, AnalysisRun (scores, forecasts, anomalies, explanations), Upload (S3 key, type, status), AuditLog.

Placement depends on D053:
- Option A: relational entities in Supabase Postgres; AnalysisRun + AuditLog in DynamoDB.
- Option B: everything in DynamoDB (single-table vs multi-table design to be presented).
- Option C: everything in Supabase Postgres.

## 27. API Design

**[PENDING D017, D013, D056]** No endpoints defined.

[PROPOSED shape for discussion] REST JSON via Next.js route handlers on Vercel; route handlers invoke Lambda (D056); uploads via S3 pre-signed URLs generated server-side; input validation on every endpoint (validation library choice requires approval if not minor). Candidate resources: companies, profile-extraction, applicability, image-classification, uploads, invoices/extract, validation, anomalies, forecast, risk-score, explanation, what-if.

## 28. Security

**[CONFIRMED minimum considerations]**
- Private S3 buckets (block public access).
- Least-privilege IAM (see D057 — IAM is required to use any AWS service).
- Upload restrictions (type, size).
- Server-side validation.
- Secure API endpoints.
- No secrets in frontend; environment variables (Vercel env vars server-side only; never `NEXT_PUBLIC_` for secrets). Supabase **service-role key** must never reach the browser; only the anon/publishable key may be client-side, and only with Row-Level Security enabled.
- Basic rate limiting if appropriate (D046).

**[PENDING D033]** Storage & retention policy — must ask owner.

Sensitive data: invoices, sales volume, suppliers, packaging quantities, company details. [PROPOSED] Demo uses synthetic data only (Q9).

### Authentication **[PENDING D006]**
| Option | Pros | Cons |
|---|---|---|
| No auth | Fastest; zero cost | Public endpoints can be abused → Lambda/LLM spend risk; no data separation |
| Simple demo login (shared credential / signed cookie) | Fast; blocks casual abuse | Not production-grade |
| **Supabase Auth** | Already in stack (D052); integrates with RLS; free tier | Must bridge identity to AWS calls (Vercel route verifies Supabase session before invoking Lambda) |
| Clerk | Polished UI | Extra vendor beyond approved stack |
| Auth.js | Open-source, flexible | Setup time; needs adapter |
| ~~Amazon Cognito~~ | — | **Excluded by D051** |

Assistant recommendation: Supabase Auth (email magic link or password) or simple demo login — not approved.

### User roles **[PENDING D034]**

## 29. Deployment

**[PENDING D013, D018, D043, D056]**

[PROPOSED]
- **Frontend + API layer:** Vercel, deployed from Git (requires D042).
- **Lambda functions:** deployed as zip packages/layers via AWS CLI scripts or Terraform (D043; CloudFormation-based tools excluded).
- **Models & context files:** private S3 bucket (D060).
- **Supabase:** project created via dashboard; schema managed via SQL migrations in repo (if Postgres used, D053).
- **DynamoDB tables:** created via the same tooling as Lambda (D043).

**Expected project structure [PROPOSED — do not create until approved, D041]:**
```
/
  context.md
  README.md
  docs/
  frontend/            # Next.js app (deployed to Vercel)
  backend/
    lambdas/           # AWS Lambda functions (Python / TS)
  ml/
    datasets/
    notebooks/
    models/
    scripts/
    evaluation/
  infrastructure/      # AWS CLI / Terraform scripts, IAM policies
  supabase/            # SQL migrations, RLS policies (if D053 uses Postgres)
  synthetic-data/
  tests/
```
[ASSISTANT NOTE] Possible refinements: keep raw datasets out of git; add `config/` for centralised configuration.

## 30. Testing

**[CONFIRMED]** After coding: run relevant tests, type checks, linting, build verification; report failures accurately; never claim something works unless tested.

**[PENDING D047]** Tooling and scope. [PROPOSED] Unit tests for rules engine, risk score and What-If math; schema-invariant tests for synthetic data (e.g., recycled ≤ generated); local invocation tests for each Lambda; Lambda package-size check; one end-to-end demo-path check against the Vercel preview deployment.

## 31. Evaluation Metrics

| Component | Proposed metrics | Baseline | Result |
|---|---|---|---|
| Image classifier | Accuracy, macro-F1, per-class P/R, confusion matrix | Majority class | TBD |
| Forecasting | MAE, RMSE, R² | Naive last-value, seasonal-naive | TBD |
| Anomaly detection | Precision, recall, F1 per anomaly type | Rules-only | TBD |
| Invoice extraction (D055) | Field-level exact-match on labelled sample invoices | — | TBD |
| Profile extraction (LLM, D054) | Field-level accuracy on a small hand-labelled set | — | TBD |
| Risk score | Not an ML metric; sanity tests on known scenarios | — | TBD |

All metrics **[PROPOSED]**; final selection PENDING D028/D029. **No fabricated metrics.**

## 32. Business Model

**[PROPOSED]** B2B SaaS.
- Candidate segments: SMEs, mid-sized producers, EPR consultants, sustainability teams, compliance firms.
- Candidate revenue streams: SaaS subscription; consultant dashboard; enterprise API; compliance reports; later marketplace/partner integrations.

## 33. Pricing Assumptions

**[PROPOSED — PLACEHOLDERS ONLY; PENDING D039]**

| Tier | Placeholder price | Notes |
|---|---|---|
| Starter | ₹2,999 / month / company | |
| Professional | ₹9,999 / month / company | |
| Consultant | ₹29,999 / month, multiple clients | Implies multi-client capability (D034) |
| Enterprise | Custom + API access | |

[ASSISTANT NOTE] Presenting a Consultant tier implies multi-client support the MVP may not implement; the pitch should state which tiers are roadmap.

## 34. Demo Strategy

**[CONFIRMED]** The demo must tell one continuous story. Final flow PENDING D012; implementation must not be optimised around it until approved.

**Candidate demo flow [PROPOSED]** (service names updated for D051):
1. Create demo company
2. Describe business
3. AI extracts company attributes (LLM — D054)
4. Upload packaging image (stored in S3)
5. DL classifies material (Lambda)
6. Upload invoice (stored in S3)
7. Invoice data extracted (D055 — previously "Textract")
8. System detects anomaly (Lambda)
9. Dashboard shows risk score (Lambda)
10. ML forecasts future packaging (Lambda)
11. GenAI explains the risk (D054 — previously "Bedrock")
12. User runs What-If simulation
13. New projected result displayed
14. Show architecture (AWS S3 / Lambda / DynamoDB + Supabase + Vercel)
15. Show business model

[ASSISTANT NOTE — C5] See contradictions in Section 39.

## 35. Hackathon Constraints

**[CONFIRMED]** Short build window; AWS ≈ USD 25 and only S3/Lambda/DynamoDB; must visibly use AWS; functional MVP; no silent scope expansion.
**[TBD]** Deadline, team size, judging criteria, submission format → Open Questions Q1–Q3.

## 36. Known Limitations

**[PROPOSED — to be confirmed as the project matures]**
- No real company-level EPR operational data; tabular models trained on synthetic data.
- Image classification gives probable material only; cannot determine legal EPR category.
- Public waste images may not resemble retail packaging photos.
- Invoice extraction (D055) may be wrong; requires confidence/validation display and user review. If D055 = A, only digital PDFs with known layouts are supported.
- GenAI depends on an external provider outside AWS (D054).
- Lambda zip-size limits constrain model choice and libraries (no container images).
- Lambda cold starts for ML inference.
- Free-tier limits on Supabase / Vercel (D058).
- Rules engine encodes a simplified, owner-approved subset of regulations; not legal advice.
- Not a substitute for the CPCB portal or any regulatory process.

## 37. Future Scope

**[PROPOSED — not in MVP]** Consultant multi-client workspace; enterprise API; compliance report generation; marketplace/partner integrations; additional EPR regimes; real-data pilots; ERP integrations; recycler data verification; scanned-invoice OCR.

## 38. Decision Log

Format (append-only; never overwrite):

```
Decision ID:
Date:
Topic:
Options considered:
Decision:
Reason:
Approved by:
Impact:
Revisit condition:
```

---

```
Decision ID: D051
Date: 2026-10-08
Topic: AWS service selection
Options considered: S3, Lambda, DynamoDB, API Gateway, Amplify, Textract, Bedrock, CloudWatch (as listed in context.md v0.1)
Decision: Use ONLY Amazon S3, AWS Lambda and Amazon DynamoDB (on-demand).
Reason: Owner instruction ("Use only these 3 services of aws").
Approved by: Project owner
Impact: Textract, Bedrock, API Gateway, Amplify, CloudWatch, ECR, AWS Budgets and CloudFormation-based IaC removed.
        D021 and D023 superseded. New decisions opened: D053 (AWS/Supabase split), D054 (GenAI provider),
        D055 (invoice extraction method), D056 (Vercel→Lambda invocation), D057 (implicit AWS dependencies).
        D013, D018, D019, D043, D044, D046 options changed.
Revisit condition: Owner explicitly approves an additional AWS service; or an unavoidable implicit
        dependency (IAM, CloudWatch Logs) requires a ruling (D057).
```

```
Decision ID: D052
Date: 2026-10-08
Topic: Additional platforms
Options considered: Not presented as options; owner instruction.
Decision: Add Supabase and Vercel to the stack "wherever required".
Reason: Owner instruction.
Approved by: Project owner
Impact: Vercel becomes the candidate frontend host and API layer (D018, D013).
        Supabase becomes a candidate for auth, relational data and/or storage.
        Exact responsibilities are NOT decided — see D053, D006, D018.
Revisit condition: Owner changes platform choice, or free-tier limits (D058) prove insufficient.
```

```
Decision ID: D024
Date: 2026-10-08
Topic: Invoice sample source
Options considered: Public/Kaggle invoice OCR datasets; synthetic generated invoices
Decision: Do NOT use any Kaggle/public invoice image dataset. Fabricate synthetic invoices with a larger
        variety of layouts and formats; document them under ML/DL with Synthetic Data.
Reason: Owner instruction.
Approved by: Project owner
Impact: Section 16 updated; synthetic invoice spec added (Section 43.6), detailed spec PENDING D061.
        Invoices must be clearly fictitious (no real GSTINs, company names or addresses).
Revisit condition: Owner requests real-world invoice testing.
```

```
Decision ID: D035
Date: 2026-10-08
Topic: Three.js usage
Options considered: No Three.js; one small visual; waste-material aesthetic components
Decision: Use Three.js components depicting garbage / waste materials, for aesthetics.
Reason: Owner instruction ("we need three js components for garbage waste materials for aesthetics").
Approved by: Project owner
Impact: Three.js stays in the stack. Each specific component (what it shows, where, performance budget)
        still requires approval — tracked as D062. Helper libraries tracked as D065.
Revisit condition: Performance problems on demo hardware, or owner changes direction.
```

```
Decision ID: D037
Date: 2026-10-08
Topic: Visual design system
Options considered: Not presented as options; owner supplied a design system.
Decision: Adopt the owner-supplied "Bitcoin DeFi" design system (true-void dark UI, glass morphism,
        glow, grid textures, Space Grotesk / Inter / JetBrains Mono, pill buttons, cva components),
        with the orange accent family replaced by green shades.
Reason: Owner instruction.
Approved by: Project owner
Impact: Section 45 written. Exact green tokens PENDING D063; treatment of the gold tertiary colour and
        semantic risk colours PENDING D063/D066. Conflicts with the earlier "avoid excessive gradients /
        animation" direction recorded as C16 — owner must say which wins.
Revisit condition: Accessibility failures, or owner changes direction.
```

```
Decision ID: D064
Date: 2026-10-08
Topic: EPR domain reference
Options considered: Not presented as options; owner supplied the document.
Decision: Use "Decoding Extended Producer Responsibility (EPR) in India — A Business Leader's Handbook"
        (ed. Santanu Goswami, TrackEPR; file V3_ebook-A Simple Guide to EPR.pdf) as the domain reference
        for EPR obligations and understanding.
Reason: Owner instruction ("For epr obligations and understanding about the topic understand the pdf properly").
Approved by: Project owner
Impact: Section 41 written; Section 23 and C1 updated.
Revisit condition: Official CPCB/MoEFCC sources contradict the guide, or the guide is outdated.
```

```
Decision ID: DS-01 … DS-25 (synthetic data & dummy entities)
Date: 2026-10-09
Topic: Synthetic data specification, dummy entity master, invoice PDF tooling
Options considered: As listed in syntheticml/docs/DECISIONS-REQUIRED.md
Decision: All recommended options approved, including: Apr 2023–Mar 2026 window; plastic-only EPR relevance with
        non-plastic components flagged; 200 companies / 120 suppliers / 150 buyers / 50 recyclers (8 unregistered);
        exactly 1,000 PDFs (600 routine / 280 anomalous / 120 legitimate-hard) + 1,000 JSON; ~5 % anomaly rate;
        ReportLab for PDFs (DS-18); Python 3.12 (DS-19).
        Safeguards: form-based plastic category is a synthetic modelling convention only (synthetic_category +
        legal_verification_status = TBD); MLP → Cat III is a configurable default, TBD; generated→collected→recycled
        are synthetic test relationships, not obligations; prices/GST/HSN are illustrative; brand_owner kept separate
        from applicability logic; GSTIN-like values deliberately invalid; only city/state names real; the seven test
        roles are fixtures, not the production authorization model (D034 still open); gst_registered and
        epr_registered kept separate.
Reason: Owner instruction ("APPROVED — GENERATE FULL ENTITY MASTER", 2026-10-09).
Approved by: Project owner
Impact: Full dummy entity master generated (syntheticml/synthetic-data/masters). Resolves the detail of D025 (entity part),
        D061 (count, layouts, renderer). D005/D026 settled for synthetic data as DS-07/DS-08. Full transaction/invoice/PDF
        generation still requires "APPROVED — GENERATE FULL SYNTHETIC DATASET".
Revisit condition: Official regulatory sources contradict a convention; owner changes scope.
```

```
Decision ID: D027 / D028 / D029 (synthetic MVP)
Date: 2026-10-09
Topic: Forecasting model, forecasting metrics/baselines, anomaly features and threshold
Options considered: last value, seasonal naive, Linear Regression, Random Forest, XGBoost; rules only, Isolation Forest only,
        rules + Isolation Forest (syntheticml/ml/evaluation/experiment_log.csv)
Decision: Per the owner's ML-phase instruction (validation-only tuning, single test evaluation): forecast-v1 = XGBoost on
        scale-free features predicting log(next/current) (best validation MAE); metrics MAE/RMSE/R2 vs last-value and
        seasonal-naive baselines. anomaly-v1 = deterministic rules (tolerance 0.01 kg / 0.05 %) OR Isolation Forest
        score >= 0.5387 (threshold chosen on validation under FPR <= 0.10).
Reason: Owner instruction ("SYNTHETIC ML TRAINING PHASE"); selection by validation results.
Approved by: Project owner (phase authorisation); individual choices made by the documented automatic procedure.
Impact: AWS artifacts in syntheticml/ml/artifacts/*/v1; report syntheticml/docs/ml-model-report.md. Synthetic-only metrics.
Revisit condition: Real data becomes available; AN09 recall improvement; Lambda package-size issues.
```

## 39. Open Questions

### 39.1 Contradictions / tensions identified

| ID | Issue | Why it matters | Linked decision |
|---|---|---|---|
| C1 | **EPR regime scope undefined.** Per the guide (Section 41), packaging EPR currently covers **plastic only**; glass/metal (and paper) packaging EPR is under development; batteries are a separate regime (BWM Rules 2022). Image classes Paper, Cardboard, Metal, Glass therefore carry no current packaging-EPR obligation; Battery maps to a different regime. | Drives rules, risk meaning, synthetic data. | D008, D009, D030 |
| C2 | "Product/packaging image" use case vs waste/garbage training images. | Domain mismatch in demo. | D002, D009 |
| C3 | Three.js in stack but use is conditional. | Possible unused dependency. | D035 |
| C4 | GenAI must use "retrieved" context. Bedrock KB removed by D051; a Supabase pgvector RAG would be possible but adds scope. | Grounding method vs scope. | D022, D054 |
| C5 | Demo flow: CSV upload absent though invoice comparison needs internal records; risk score shown before forecast though "forecasted fulfilment gap" is a factor. | Story consistency. | D011, D012 |
| C6 | Recycling/fulfilment gap needs an approved obligation-target source. | Factors can't be computed honestly. | D030, D007 |
| C7 | Tabular models trained only on synthetic data. | Metrics ≠ real-world evidence. | D025, D026 |
| C8 | Consultant pricing tier vs undecided multi-client roles. | Pitch vs product. | D034, D039 |
| C9 | ~~Next.js SSR on Amplify + separate API Gateway duplicates backend~~ | **Resolved by D051** (both removed); replaced by C14. | — |
| C10 | ~~ECR and AWS Budgets not in owner's list~~ | **Resolved by D051** (both excluded); consequence captured in C13 and D044. | — |
| C11 | **"Must visibly and meaningfully use AWS" vs Supabase/Vercel taking major roles.** If Supabase holds data and Vercel holds the API, AWS could shrink to one Lambda. | Hackathon requirement risk. | D013, D053 |
| C12 | **"Only 3 AWS services" vs implicit dependencies.** IAM is required to use any AWS service. Lambda writes logs to CloudWatch Logs by default (avoidable only by denying log permissions, which removes debugging). Billing alerts would need AWS Budgets/CloudWatch. | Literal compliance with D051. | D057 |
| C13 | **No ECR → DL model must fit a Lambda zip package/layer.** ONNX Runtime + numpy + Pillow + model may approach the size limit; adding scikit-learn/XGBoost for other models in the same function may exceed it. | May force separate functions, lighter models, or ONNX for all models. | D003, D019, D020, D027 |
| C14 | Vercel route handlers calling Lambda need AWS credentials stored in Vercel (long-lived IAM user access keys), or public Lambda Function URLs. | Security vs simplicity. | D056, D057 |
| C15 | Textract/Bedrock were the main "AWS AI" showcase. Their removal means AI capabilities shown in the demo run on Lambda (own models) or an external LLM. | Pitch narrative about AWS AI usage. | D012, D054, D055 |
| C16 | **Design system vs earlier UI direction.** The original brief says avoid excessive gradients, excessive animation and overcomplicated 3D. The adopted design system mandates gradient buttons/text, glows, spinning orbitals, bouncing cards, pulsing badges, plus Three.js. | Which instruction wins where they conflict? | D037, D062 |
| C17 | **Crypto visual language vs compliance-trust positioning.** "Digital gold / Bitcoin" metaphors may read as fintech/crypto to compliance buyers. Proposed mitigation: keep the visual mechanics, replace crypto metaphors with circular-economy / compliance-ledger metaphors (Section 45.1). | Brand perception. | D037, D038 |
| C18 | **Green brand vs risk semantics.** In a risk product, green conventionally means "safe". If green is the brand accent everywhere, a high-risk score may look "good". Also, amber (usual "medium risk") is orange-adjacent, and the owner asked to replace orange. | Readability of risk states. | D063, D066 |
| C19 | **Accessibility: white text on bright green fails contrast.** White on #22C55E ≈ 2.3:1 (fails WCAG AA). The design system specifies white button text. | Accessibility vs literal spec. | D063 |
| C20 | **Design system's CSS orbital-ring hero vs Three.js hero.** Both target the same hero slot. | Duplication. | D062 |
| C21 | **Material-flow quantities conflated.** Purchasing, packaging used, goods sold, placed-on-market, waste collected, recycling and regulatory fulfilment are different measures. | A twin that sums them indiscriminately is misleading. | D071, D075 |
| C22 | **Synthetic data can validate pipeline without validating real-business accuracy.** | False claims of production-ready AI. | D077 |
| C23 | **A predicted material class cannot establish plastic EPR legal category.** | Wrong classifications can propagate into risk/optimization. | D009, D030, D080 |
| C24 | **Audit findings need reproducible source evidence and human edits without losing originals.** | Trust, disputes, security. | D072, D076 |
| C25 | **Packaging optimization may improve measured material consumption but does not itself prove recovered waste or compliance savings.** | Environmental-impact and financial claims may be overstated. | D073, D081 |
| C26 | **Revised runbooks expand product functionality beyond confirmed F1–F15 ceiling.** | Owner approval required before implementing net-new features. | D050, D074, D079 |

### 39.2 Missing information

| ID | Question |
|---|---|
| Q1 | Hackathon deadline and time remaining? |
| Q2 | Team size and responsibilities? |
| Q3 | Judging criteria and submission format? |
| Q4 | Is the AWS account new (free-tier eligible)? Are the USD 25 credits restricted to certain services? |
| Q5 | ~~Bedrock model access~~ (superseded by D051). Preferred AWS region? |
| Q6 | Which official regulatory documents are the approved source for rules and GenAI context? |
| Q7 | Initialise git? Host on GitHub (needed for Vercel Git deployments)? |
| Q8 | Local environment: Node.js, Python, AWS CLI installed? Colab/GPU for DL training? |
| Q9 | Accept real user files in the demo, or synthetic/sample files only? |
| Q10 | UI language(s)? |
| Q11 | **Is there any budget for a non-AWS LLM API (D054)?** If zero, GenAI features must use templates (D054 option C). |
| Q12 | Do Supabase and Vercel accounts/projects already exist? Which team/org should be used? |

## 40. Development Protocol

### 40.1 Decision-making rules **[CONFIRMED]**
The assistant must **not** independently decide when multiple reasonable options exist in any of: product scope, feature prioritisation, UI/UX behaviour, page structure, database schema, API design, cloud/AWS service selection, ML model choice, DL architecture, dataset selection, synthetic data logic, training strategy, evaluation metrics, thresholds, risk score calculation, EPR business rules, pricing, business model, deployment architecture, authentication, user roles, branding, copywriting, visual design, demo flow, and any cost/quality/speed/accuracy/complexity/scope tradeoff.

Purely mechanical details that do not affect behaviour, architecture, UX, cost or maintainability may proceed without asking.

Never: silently expand scope; implement a feature because it "sounds useful"; replace an approved technology; change an approved decision without asking; **use any AWS service beyond S3, Lambda and DynamoDB (D051)**. If requirements conflict, surface the conflict and ask.

### 40.2 Phase workflow **[CONFIRMED]**
1. **Clarify** — state exactly what is being built.
2. **Identify Decisions** — list decisions needing approval.
3. **Present Options** — concise options with tradeoffs.
4. **Recommendation** — preferred option, not executed.
5. **Approval** — wait for explicit owner response.
6. **Implement** — approved scope only.
7. **Verify** — tests, type checks, lint, build.
8. **Report** — what changed, files changed, tests run, results, remaining issues, next decision required.

Do not automatically begin the next major phase.

### 40.3 Question format **[CONFIRMED]**
```
DECISION REQUIRED

Topic:
<decision>

Why it matters:
<short explanation>

Options:

A. <option>
Impact:
<impact>

B. <option>
Impact:
<impact>

C. <option>
Impact:
<impact>

Recommendation:
<recommendation and reason>

Awaiting:
My explicit selection.
```
Ask only questions that materially affect the project.

### 40.4 Coding behaviour **[CONFIRMED]**
- Before substantial changes: list files to create/modify, explain architecture impact, ask when a decision is involved.
- After coding: run tests, type checks, linting, build; report failures accurately; never claim untested functionality works.
- On errors: diagnose, explain cause, propose fix; ask only if the fix changes architecture or product behaviour; otherwise fix mechanical defects directly.

### 40.5 Git behaviour **[CONFIRMED]**
- Never delete history, force push, squash without instruction, commit secrets, or modify unrelated files.
- Suggest commit messages at meaningful checkpoints; do not commit unless instructed.

### 40.6 Cost protocol **[CONFIRMED]**
Before enabling any AWS service with meaningful cost: why required → estimated usage → cost risk → cheaper alternative → wait for approval. **[PROPOSED]** Apply the same protocol to paid Supabase/Vercel features and any external LLM API.

### 40.7 Dataset protocol **[CONFIRMED]**
Before downloading/combining any dataset: name, source, size, classes, licence, usefulness, limitations, overlap → wait for approval.

### 40.8 Context maintenance
- Update this file after every approved decision and every completed phase.
- Bump the version, "Last updated" date and Change log at the top.
- Append to Decision Log; move items out of Pending Decisions only when approved.

---

## 41. EPR Domain Knowledge (from owner-supplied guide — D064)

> **Source:** *Decoding Extended Producer Responsibility (EPR) in India — From Registration to Compliance: A Business Leader's Handbook*, ed. Santanu Goswami (TrackEPR / TrackBee Data Solutions). Local file: `V3_ebook-A Simple Guide to EPR.pdf` (59 pages). Content reflects the position as of ~December 2024.
> **Status:** Summarised and paraphrased for product design. This is a secondary source. Numeric thresholds, fees and targets are **[TO VERIFY]** against official CPCB/MoEFCC notifications before the rules engine presents them as rules. Nothing here is legal advice.

### 41.1 What EPR is
- EPR makes the business that **places products or packaging on the Indian market** responsible for managing them after use ("cradle-to-grave").
- Common principles across regimes: (1) register with the authority, (2) meet collection/recycling targets, (3) report regularly, (4) work only with authorised/registered recyclers, (5) keep proper records.
- Compliance is usually met by buying **EPR certificates/credits** from registered recyclers/processors and closing targets in an **Annual Return**, due **30 June** after the financial year (FY Apr–Mar).

### 41.2 The five active regimes and their portals

| Regime | Rules (as named in guide) | Who is obligated (summary) | CPCB portal |
|---|---|---|---|
| Plastic packaging | Plastic Waste Management Rules + EPR guidelines | PIBOs (Producers, Importers, Brand Owners), SIMP (Seller/Importer/Manufacturer of raw plastic), PWPs | eprplastic.cpcb.gov.in |
| E-waste | E-Waste Management Rules 2022 | Manufacturers, producers, refurbishers, recyclers/dismantlers of listed EEE | eprewastecpcb.in |
| Batteries | Battery Waste Management Rules 2022 | Producers (incl. batteries inside equipment, importers), recyclers (R1–R4), refurbishers | eprbatterycpcb.in |
| Tyres | Hazardous & Other Wastes (Mgmt & Transboundary Movement) Amendment Rules 2022 | Producers (incl. importers of vehicles with fitted tyres), recyclers, retreaders | eprtyrescpcb.in |
| Used oil | (Used-oil EPR under the same hazardous-waste framework, Rule 26 cited) | Producers (P1–P9), collection agents, recyclers, used-oil importers | eprusedoil.cpcb.gov.in |

**Under development (not yet active per the guide):** non-ferrous metals, end-of-life vehicles, glass and metal packaging, construction & demolition waste, wastewater; the preface also mentions paper packaging.

**Implication for EPRLens [ASSISTANT NOTE]:** For packaging, only **plastic** currently creates an EPR obligation. This strongly supports scoping the MVP to **plastic packaging EPR** (D008), with other materials shown as "no current packaging-EPR obligation — regime under development" and batteries flagged as "separate regime".

### 41.3 Applicability — the guide's self-assessment (basis for F2/F3)
The guide offers a questionnaire that maps cleanly to structured attributes the LLM (F2) can extract and the rules engine (F3) can evaluate:

| Section | Attributes to capture | Rule outcome |
|---|---|---|
| A. General | Legal structure; annual turnover (> ₹50 Cr?); activities (manufacture / import / own-brand distribution / raw materials / processing-recycling); single vs multi-state; export vs domestic | Context for all regimes |
| B. Plastic | Produces plastic packaging? Imports plastic-packaged products? Imports plastic raw material? Sells own-brand products in plastic packaging with turnover > ₹50 Cr? Manufactures/sells raw plastic? Processes plastic waste? | Producer / Importer / Brand Owner / SIMP / PWP — **one registration per role** |
| C. E-waste | Manufactures/imports/sells listed EEE (incl. parts/spares)? Refurbishes/dismantles? Exemptions: only batteries/plastic packaging, micro-enterprise, radioactive | Producer / refurbisher / recycler, or documented exemption |
| D. Battery | Manufactures/sells/imports batteries (standalone or in equipment)? Refurbished? For self-use? | Battery producer category |
| E. Tyres | Manufactures/brands/imports tyres or vehicles with tyres? Recycles? Retreads? | Separate registration per activity |
| F. Used oil | Handles base oil (HS 2710 1971), lube oil (HS 2710 1972–2710 1990), other oils (HS 2710 9100 / 2710 9900)? Processes or imports used oil? | Used-oil EPR |

The guide's worked example: an importer of calculators with built-in batteries, packaged in plastic, may need Battery EPR, Plastic EPR (importer), e-waste EPR, and possibly Brand Owner registration. **[PROPOSED]** Use this as a rules-engine test case.

### 41.4 Plastic packaging — details that matter for EPRLens

**Plastic packaging categories (Appendix of guide):**
| Cat | Description |
|---|---|
| I | Rigid plastic packaging (incl. thermocol / expanded polystyrene) |
| II | Flexible plastic packaging — single/multi-layer plastic, sheets, covers, carry bags, sachets, pouches |
| III | Multi-material packaging with ≥1 plastic layer and ≥1 non-plastic layer |
| IV | Compostable plastic packaging and carry bags |

**Registration data (Part C) that sets targets:**
- Plastic consumption for the **previous two years** — the portal uses this to compute **next year's category-wise targets**.
- Category-wise breakdown (e.g., Cat I 40%, Cat II 30% …).
- **State-wise** distribution of plastic introduced into the market.
- Sources of raw material (registered vs unregistered suppliers); plastic sold to other entities.

**Registration fee (PIBO, by plastic waste generation):** < 1,000 TPA ₹10,000; 1,000–10,000 TPA ₹20,000; > 10,000 TPA ₹50,000; annual processing fee = 25% of application fee **[TO VERIFY]**.

**Ongoing compliance (invoice-level reporting):**
- Compliance can be done monthly, quarterly or yearly, but must be complete before **30 June** of the following FY.
- **Every invoice is reported on the portal.** An invoice covering several plastic categories is reported once **per category** with the quantity for each.
- Per the guide, **up to 5 invoices may share the same invoice number** → EPRLens duplicate detection must not rely on invoice number alone.
- **Brand Owner:** purchases from registered vendors auto-reflect as BO procurement; BO reports unregistered procurement itself; category-wise sales reported **state-wise**.
- **Producer (incl. MSME):** reports all sales and purchases invoice-wise. Sales to **registered** entities **shift the liability** to the buyer; sales to **unregistered** entities stay the producer's liability. For an MSME producer, liability on unregistered sales sits with the manufacturer/importer of the virgin granules.
- **Importer (raw material, SIMP module):** obligation = raw material imported − raw material sold to registered entities (excluding MSME producers).
- **Importer (packaging):** reports plastic packaging quantity per consignment; reports sales if sold.
- **PWP:** uploads GST sales invoices; portal validates via QR code; **100% match** required before certificate credit is generated; PWP sales entries are **non-editable** after submission.

**Annual Return (BO / Producer / Importer):**
- Annual consumption = **pre-consumer + post-consumer** plastic packaging.
- Report sales with the **exact recycled-content percentage**.
- Close **category-wise targets** by adding EPR credits.
- **Exports** are deducted from the **next year's** target; supporting Excel + zipped invoices attached.
- Pay annual processing fee, then submit.

### 41.5 Real-world failure modes cited by the guide (directly relevant to EPRLens)
| Failure | Guide's example | EPRLens capability that addresses it |
|---|---|---|
| Category misclassification | Registered under Cat I while operations were Cat II → targets computed on wrong category | Image + rule cross-check; "wrong material/category" anomaly type |
| Data-entry magnitude error | Import reported as **500 MT instead of 0.5 MT** (×1000) | Decimal / extra-zero anomaly detection; invoice-vs-record validation |
| Packaging vs product confusion | Gloves importer cut liability ~95% by correctly separating plastic packaging from plastic items | Applicability rules + explanation (GenAI) |
| Annual Return reporting errors | Auto-parts maker saved ~₹51 lakh on next year's target after corrections | Pre-submission validation dashboard |
| Unauthorised liability transfers | Large liability wrongly transferred to a cement brand, resolved quickly | Registered vs unregistered transfer checks (future scope unless approved) |

**[ASSISTANT NOTE]** These are the strongest real-world anchors for the demo story (D012) — e.g., the demo anomaly could mirror the 500 MT vs 0.5 MT error. Case-study figures are the guide author's claims and should be attributed as such if shown.

### 41.6 Proposed obligation estimate for "gap" risk factors — **[PROPOSED, PENDING D068]**
The guide does not state plastic target percentages per category/year. Therefore EPRLens can compute an **estimated liability base**, not an official target:

```
For company c, plastic category k, financial year y:
placed[k]        = Σ packaging_kg of category k introduced into the Indian market
transferred[k]   = Σ quantity sold to REGISTERED entities (producer role only; liability shifts)
exported[k]      = Σ quantity exported (reduces NEXT year's target per guide)
liability_base[k] = placed[k] − transferred[k] − exported_adjustment[k]
coverage[k]      = credits_procured[k] / liability_base[k]
estimated_gap[k] = liability_base[k] × target_pct[k,y] − credits_procured[k]   ← only if target_pct is sourced (Q6)
```
If `target_pct` is not sourced from an official document, the UI must show `liability_base` and `coverage` only, labelled "estimate".

### 41.7 Other regimes — reference facts (for future scope / applicability rules)
- **E-waste:** EEE grouped into ITEW, CEEW, LSEEW, EETW, TLSEW, MDW, LIW, each item with an EEE code and **average life** (e.g., smartphones ITEW15 5 yrs; refrigerators CEEW2 10 yrs). Established producers report FY sales by weight for a period equal to average life. Micro enterprises exempt. Quarterly returns (by end of month after quarter) and Annual Return by 30 June. Certificates valid 5 years.
- **Batteries:** categories Portable, Automotive, EV, Industrial. Producers must ensure recycling/refurbishment incl. for self-use. Collection targets (from 2026-27): ≥70% of batteries placed on market five years earlier; 100% recycling of collected; 60% carry-forward; compliance cycles of 7/10/14 years by battery type. Registration fee by turnover (< ₹5 Cr ₹10k; ₹5–50 Cr ₹20k; > ₹50 Cr ₹40k), valid 5 years. Recyclers R1–R4. EPR registration number on batteries by 31 Mar 2025. **[TO VERIFY]**
- **Tyres:** five recognised end products (reclaimed rubber, crumb rubber, CRMB, recovered carbon black, pyrolysis oil/char). Certificate price band ₹2.52–₹8.40/kg per the guide. Import of waste tyres for pyrolysis is banned.
- **Used oil:** producer types P1–P9; fee by sales volume (₹25k for < 5,000 MTPA up to ₹10 lakh for > 100,000 MTPA); registered entities may deal only with registered entities; false information can lead to revocation up to five years.

### 41.8 How the guide informs each EPRLens component
| Component | Guide-derived input |
|---|---|
| F2 profile extraction | Section 41.3 attribute list (roles, turnover > ₹50 Cr, import/manufacture/brand, states, exports) |
| F3 applicability rules | 41.3 questionnaire logic; multi-role → multi-registration |
| F4 image classification | Material → regime mapping (41.2); plastic → Cat I–IV needs user confirmation |
| F7/F8 invoice validation | Invoice-level reporting, per-category split, up-to-5-shared-invoice-numbers rule, registered vs unregistered buyers |
| F9 anomaly detection | ×1000 data-entry errors; category misclassification |
| F10 forecasting | Targets derive from prior two years' consumption → forecasting next-year consumption has real planning value |
| F11 risk score | Coverage ratio, unregistered-sales share, category mix consistency, missing state-wise data, recycled-content reporting |
| F13 What-If | Circular-design levers from the guide: reduce packaging weight/size, recyclability, recycled content |
| Synthetic data | Fields in 43.3 |

---

## 42. ML / DL with Real Data (Kaggle)

> **Status:** **[PROPOSED]** — nothing downloaded. Dataset choice PENDING D002; taxonomy PENDING D009; architecture PENDING D003. **No invoice datasets** (D024).

### 42.1 Scope
Real public data is used **only for the image model** (F4: probable material of a packaging/waste item). All tabular EPR data is synthetic (Section 43).

### 42.2 Candidate dataset cards (verified via web search on 2026-10-08; items marked **[VERIFY]** could not be confirmed from the primary page)

| # | Dataset | Source | Size | Classes | Licence | Why useful | Limitations | Overlap |
|---|---|---|---|---|---|---|---|---|
| R1 | **TrashNet** (Yang & Thung, Stanford CS229) | github.com/garythung/trashnet (Kaggle mirrors exist) | 2,527 images (glass 501, paper 594, cardboard 403, plastic 482, metal 410, trash 137); 512×384 | 6 | **MIT** per repository metadata **[VERIFY LICENSE file]** | Clean, well-known baseline; licence permissive | Small; single objects on white posterboard → large domain gap; "trash" class tiny | Commonly re-included inside larger Kaggle garbage datasets **[VERIFY]** |
| R2 | **Garbage Classification (12 classes)** — Mostafa Mohamed | kaggle.com/datasets/mostafaabla/garbage-classification | ~15,150 images **[VERIFY — a derivative reports 15,870]** | paper, cardboard, biological, metal, plastic, green-glass, brown-glass, white-glass, clothes, shoes, batteries, trash | **[VERIFY — not confirmed]** | Larger; includes **batteries**; glass split by colour | Web-sourced images, mixed quality; class imbalance (clothes heavy); clothes/shoes irrelevant to packaging | Likely overlaps with R1 and is reused in R3 **[VERIFY]** |
| R3 | **Garbage Classification V2** — Suman Kunwar (sumn2u) | kaggle.com/datasets/sumn2u/garbage-classification-v2 | **[VERIFY]** — paper reports 12,259 images; a mirror reports 19,762 | metal, glass, biological, paper, battery, trash, cardboard, shoes, clothes, plastic | **[VERIFY — not confirmed; associated paper is CC BY 4.0 but that covers the paper]** | Largest candidate; includes battery; partly mobile-app photos (more realistic) | Version/count ambiguity; mixed sources | Probably overlaps with R2 **[VERIFY]** |
| R4 (non-Kaggle, optional) | **RealWaste** | UCI ML Repository #908 / IEEE DataPort | 4,752 images, 524×524 (Cardboard 461, Food Organics 411, Glass 420, Metal 790, Misc Trash 495, Paper 500, Plastic 921, Textile 318, Vegetation 436) | 9 | **CC BY-NC-SA 4.0** per IEEE DataPort (non-commercial, share-alike) | Real landfill photos → better robustness | Non-commercial licence conflicts with a commercial SaaS; no battery class; not Kaggle (owner asked for Kaggle) | Independent of R1–R3 |

**Excluded:** TACO (detection/segmentation, not classification); binary Organic/Recyclable datasets (too coarse); any invoice OCR dataset (D024).

**Before download (dataset protocol):** owner reviews this table; each [VERIFY] item is checked on the dataset page; licence screenshots saved to `ml/datasets/LICENSES.md`.

### 42.3 Label normalisation — options for D009

| Source label | Option A (7 classes, as briefed) | Option B (EPR-oriented, 5 classes) | EPR meaning shown to user |
|---|---|---|---|
| plastic | plastic | plastic | Plastic packaging EPR applies — confirm Cat I–IV |
| paper | paper | fibre | No current packaging EPR (paper EPR under development) |
| cardboard | cardboard | fibre | Same as paper |
| metal | metal | metal_glass | No current packaging EPR (under development) |
| glass / green- / brown- / white-glass | glass | metal_glass | Same |
| battery / batteries | battery | battery | Separate regime — Battery Waste Management Rules |
| trash, biological, food organics, vegetation | trash_other | other | Not a packaging material |
| clothes, shoes, textile | **drop** (or trash_other) | **drop** | — |

Recommendation: **Option A** for model training (finer classes help the model), with the Option B mapping applied in the UI/rules layer. Not approved.

### 42.4 Data preparation pipeline [PROPOSED]
1. Download approved datasets into `ml/datasets/raw/` (git-ignored).
2. Map labels via a versioned mapping file (`ml/datasets/label_map.yaml`).
3. **De-duplicate across datasets** with perceptual hashing (e.g., pHash, Hamming distance threshold TBD) **before** splitting, to prevent train/test leakage between overlapping datasets.
4. Remove corrupt/tiny images; record counts per class before/after.
5. Stratified split **70 / 15 / 15** (train/val/test), seed fixed.
6. Address imbalance with class-weighted loss (preferred) or capped oversampling.
7. Augmentation (train only): random resized crop, horizontal flip, ±15° rotation, colour jitter, light blur; background variety.
8. Input 224×224, ImageNet normalisation.

### 42.5 Model & training plan [PROPOSED — PENDING D003]
| Item | Proposal |
|---|---|
| Candidates | MobileNetV3-Large (~5.4M params), EfficientNet-B0 (~5.3M params) — ImageNet-pretrained (param counts approximate) |
| Environment | Google Colab GPU; PyTorch + torchvision |
| Phase 1 | Freeze backbone, train classifier head (≈5 epochs, lr 1e-3, AdamW) |
| Phase 2 | Unfreeze last blocks, fine-tune (≈10 epochs, lr 1e-4, cosine decay), early stopping on val macro-F1 |
| Batch size | 32–64 |
| Loss | Cross-entropy with class weights; label smoothing 0.1 |
| Calibration | Temperature scaling on val set so displayed confidence is meaningful |
| Low-confidence rule | If max prob < threshold (TBD, D029-style decision) → "Uncertain — please confirm material" |
| Export | ONNX (opset TBD); optional INT8 dynamic quantisation if accuracy drop ≤ agreed tolerance |
| Deployment | ONNX Runtime in Python Lambda zip (D019, Section 44.6) |

All hyperparameters are starting points, not results.

### 42.6 Evaluation [PROPOSED]
- Metrics: accuracy, **macro-F1** (primary), per-class precision/recall, confusion matrix, expected calibration error.
- Baselines: (1) majority class; (2) frozen-backbone embeddings + logistic regression.
- **Domain-gap test (D069):** ~100 team-photographed images of real Indian product packaging (bottles, pouches, cartons, cans, jars, cells), labelled by hand, **test-only**. Report separately from the in-distribution test set.
- Results: **TBD** — no training performed.

### 42.7 Experiment card (to be filled per run)
| Field | Value |
|---|---|
| Problem statement | Probable material class of a packaging/waste image |
| Dataset | TBD (D002) |
| Input features | RGB image 224×224 |
| Target | Material class (D009) |
| Preprocessing | 42.4 |
| Model | TBD (D003) |
| Hyperparameters | 42.5 starting points |
| Training split | 70/15/15 stratified, post-dedup |
| Validation strategy | Hold-out val; early stopping on macro-F1 |
| Metrics | 42.6 |
| Baseline | Majority class; linear probe |
| Result | **TBD** |
| Limitation | Waste photos ≠ retail packaging; cannot infer Cat I–IV or legal category |
| Deployment method | ONNX → S3 → Lambda |

### 42.8 Other "real data" (not proposed for now)
Public aggregate statistics (e.g., CPCB annual reports on plastic waste) could calibrate synthetic distributions. This would be a new dataset and needs approval under the dataset protocol.

---

## 43. ML / DL with Synthetic Data

> **Status:** **[PROPOSED]** — nothing generated. Requires approval of D005, D025, D026, D061 before generation. All numbers below are **design proposals and assumptions, not facts**.

### 43.1 Purpose
Synthetic data powers: (a) forecasting model (F10), (b) anomaly detection (F9) with known ground truth, (c) invoice extraction testing (F7, D055) via synthetic invoice documents, (d) profile-extraction evaluation (F2) via synthetic business descriptions, (e) the demo company shown in the app.

### 43.2 Generator architecture [PROPOSED]
Single Python package `synthetic-data/` driven by one config file (`config.yaml`) and one global seed. Hierarchical generation:

```
Companies → Products → Monthly sales per product → Packaging placed (by category, state, buyer type)
          → Invoices (purchase & sales) → Recycling / EPR credit procurement
          → Anomaly injection (with ground-truth labels) → Exports (CSV/Parquet + JSON for invoices)
          → Synthetic invoice documents (PDF/PNG) + NL business descriptions
```
Training data stays in files (CSV/Parquet) for Colab/local training. Only a handful of demo companies are loaded into the app database (D053).

### 43.3 Proposed schemas (extends Section 17; **not locked**, D025)
New fields grounded in the guide (Section 41.4) are marked ★.

*Company:* company_id, company_name (fictitious), industry, turnover_cr, manufacturer, importer, brand_owner, ★msme_flag, ★pibo_roles[], annual_units, states_operated, epr_registered, waste_stream, ★registration_category_declared (I–IV mix)

*Product:* product_id, company_id, product_name, ★plastic_category (I/II/III/IV/none), packaging_material, weight_per_unit_g, ★recycled_content_pct, launch_month

*Packaging transaction (monthly, per product × state × buyer type):* transaction_id, company_id, date, product_id, units_sold, packaging_material, packaging_category, weight_per_unit_g, total_packaging_kg, supplier_id, state, ★buyer_registered (bool), ★is_export (bool), ★consumer_stage (pre/post)

*Invoice:* invoice_id, ★invoice_number (may be shared by up to 5 invoices), company_id, supplier_id/buyer_id, material, ★plastic_category, invoice_quantity_kg, recorded_quantity_kg, invoice_date, invoice_amount, ★gstin_supplier (fake-format), ★hsn_code, is_anomaly, anomaly_type

*Recycling / credits:* company_id, month, waste_generated_kg, waste_collected_kg, waste_recycled_kg, recycler_id, recycler_registered, ★credits_procured_kg, ★plastic_category

### 43.4 Proposed sizes & distributions (PENDING D025)
| Item | Proposal |
|---|---|
| Companies | 200 |
| Period | 36 months, FY 2022-23 → FY 2024-25 (Apr–Mar aligned to EPR financial year) |
| Products per company | 3–15 (uniform integer) |
| States per company | 1–12, weighted to large consumer states |
| Turnover (₹ Cr) | Log-normal, median ≈ 40, long tail to ~2,000 → roughly 40% above ₹50 Cr (affects Brand Owner applicability) |
| MSME share | ~35% of producers |
| Approx. rows | ~50–60k product-months; ~150–250k transaction rows after state/buyer split |
| Invoices (tabular) | ~30–50k |
| Synthetic invoice documents | 500 (D061) |
| NL business descriptions | 150 with ground-truth attributes |

**Industry profiles [ASSUMPTION — illustrative, not sourced; to be approved]:**
| Industry | Dominant packaging | Cat mix (I/II/III/IV %) | Weight/unit (g) | Seasonality |
|---|---|---|---|---|
| Packaged foods & snacks | Pouches, sachets, laminates | 10/60/30/0 | 5–25 | Festive peak Oct–Nov |
| Beverages | PET bottles, shrink wrap | 85/15/0/0 | 15–40 | Summer peak Mar–Jun |
| Personal care | Bottles, tubes, sachets | 70/25/5/0 | 10–60 | Mild |
| Pharma | Bottles, blister packs | 40/20/40/0 | 2–20 | Monsoon bump Jul–Sep |
| Consumer electronics (importer) | EPS (thermocol), films | 50/50/0/0 | 50–400 | Festive peak |
| E-commerce / D2C apparel | Courier bags, poly mailers | 10/88/0/2 | 20–80 | Sale-season spikes |
| Auto parts | Films, rigid trays | 30/70/0/0 | 20–300 | Flat |

### 43.5 Generating equations [PROPOSED]
```
Company scale:        turnover_c ~ LogNormal(μ, σ);  base_units_c = k_ind × turnover_c^β   (β≈0.9)
Growth:               g_c ~ Normal(μ_g,ind, σ_g)  (annual), different per company
Seasonality:          s(m) = 1 + A_ind·sin(2π(m − φ_ind)/12) + festival_bump_ind(m)
Units sold:           u_{p,t} = base_units_p × (1+g_c)^(t/12) × s(month_t) × (1 + ε),  ε ~ N(0, σ_noise≈0.08)
Packaging placed:     pkg_kg_{p,t} = u_{p,t} × w_p / 1000                       (w_p = weight_per_unit_g)
Category split:       by product's plastic_category (Section 43.4 mix)
State split:          Dirichlet(α_states) shares per company
Buyer split:          share_registered_c ~ Beta(a,b); exports_c ~ Beta (most companies ~0)
Liability base:       Section 41.6 formula
Pre/post-consumer:    pre_consumer_frac ~ Beta(small) for producers; 0 for pure brand owners
Recycling chain:      collected = generated × c,  c ~ Beta(·) ≤ 1
                      recycled  = collected × r,  r ~ Beta(·) ≤ 1     ⇒ recycled ≤ collected ≤ generated
Credits procured:     credits_c = liability_base × coverage_c,  coverage_c ~ Beta (some < 1 → gap)
Invoice qty:          invoice_qty = recorded_qty × (1 + δ),  δ ~ N(0, 0.01) rounding noise
Invoice amount:       invoice_qty × price_per_kg_material × (1 + GST) with GST rate per HSN (illustrative)
```
All parameter values to be presented in a table for approval before generation (D025).

### 43.6 Synthetic invoices (D024 approved; spec PENDING D061)
**Goal:** a varied, realistic, clearly fictitious invoice corpus with exact ground truth, for testing invoice extraction (D055) and invoice-vs-record validation.

| Dimension | Proposed variety |
|---|---|
| Count | 500 documents (≈300 clean, ≈200 carrying injected anomalies) |
| Layouts | ≥ 8 templates: classic GST tax invoice, modern minimal, table-heavy, two-column header, landscape, multi-page with carried-forward totals, handwritten-style font sections, e-commerce style |
| Formats | Digital PDF (all); optional rasterised PNG/JPG "scanned" variants with rotation (±3°), blur, JPEG noise, shadows — useful only if D055 includes OCR/LLM |
| Fields | Invoice number, date, seller/buyer names (fictitious), fake-format GSTIN, addresses (fictitious), place of supply, HSN code, line items, material, plastic category, quantity, unit, rate, taxable value, CGST/SGST or IGST, total |
| Quantity units | kg, g, MT/tonnes, pieces-with-weight-per-piece |
| Number formats | Indian grouping (1,00,000.00), western grouping (100,000.00), no grouping |
| Date formats | DD/MM/YYYY, DD-MMM-YYYY, YYYY-MM-DD |
| Line items | 1–12; some invoices span several plastic categories (guide: report once per category) |
| Shared invoice numbers | Some legitimate groups of ≤ 5 invoices share a number (guide rule) — tests duplicate logic |
| Languages | English; optional Hindi labels on a subset **[needs approval]** |
| Ground truth | One JSON per document (all fields, line items, anomaly label/type, linked recorded_quantity) |
| Rendering tools | Python + Jinja2 HTML templates → PDF (WeasyPrint or Playwright) — **dependency approval needed**; rasterisation via PyMuPDF + Pillow |
| Safety | No real company names, GSTINs, addresses or logos; watermark/footer "SYNTHETIC — EPRLens demo" |

Evaluation: field-level exact match / normalised match per field, line-item recall, quantity-in-kg accuracy after normalisation.

### 43.7 Anomaly injection (ratio PENDING D005; types grounded in Section 41.5)
| Type | Mechanism | Ground-truth label | Expected detector |
|---|---|---|---|
| Decimal error | value ÷ 10, ÷ 100 or ÷ 1000 | `decimal_shift` | Rules (ratio vs history/invoice) + IF |
| Extra-zero error | value × 10 / × 1000 (guide: 500 MT vs 0.5 MT) | `magnitude_x10n` | Rules + IF |
| Wrong category | Cat I ↔ Cat II etc. vs product master | `category_mismatch` | Rules |
| Wrong material | material label inconsistent with product | `material_mismatch` | Rules (+ image cross-check in demo) |
| Duplicate invoice | same number + supplier + date + amount (beyond the legitimate ≤5 shared-number case) | `duplicate_invoice` | Rules |
| Missing fields | null quantity/date/category/state | `missing_field` | Rules |
| Monthly spike | month × 3–6 without matching sales | `volume_spike` | IF + seasonal z-score |
| Implausible quantity | weight/unit outside industry range | `implausible_weight` | Rules + IF |
| Invoice vs record mismatch | invoice_qty ≠ recorded_qty beyond tolerance | `qty_mismatch` | Rules |
| Recycling > generated | recycled > collected or > generated | `recycling_exceeds_generation` | Rules |
| Unregistered recycler | credits from recycler_registered = false | `unregistered_recycler` | Rules |
| Unregistered-sales liability shift | sale to unregistered buyer marked as transferred | `invalid_liability_transfer` | Rules |

Proposed overall ratio: **3–5%** of rows, stratified across types; multiple anomalies per row allowed but rare. Labels stored in separate ground-truth tables so detectors never see them.

### 43.8 Models trained on synthetic data
**A. Forecasting (F10) — PENDING D004/D027/D028**
- Target (proposed): next-month total plastic packaging kg per company (and per category); year-end projection via recursive monthly forecasts.
- Features: lags 1/2/3/12, rolling means (3/6/12), month-of-year (sin/cos), festival flags, units sold, growth rate, weight per unit, industry one-hot, category mix.
- Models: Linear Regression, Random Forest, XGBoost; baselines: naive last value, seasonal naive (same month last year).
- Metrics: MAE, RMSE, R² (+ MAPE optional) on the time-based test window.

**B. Anomaly detection (F9) — PENDING D029**
- Isolation Forest on engineered features: log quantity, invoice/record ratio, deviation from company rolling median, seasonal z-score, weight-per-unit z-score within industry, supplier history stats.
- Rules engine runs first; both outputs reported.
- Metrics: precision, recall, F1 per anomaly type and overall; PR-AUC for the IF score; comparison table rules-only vs IF-only vs combined.

**C. Profile extraction evaluation (F2) — depends on D054**
- 150 synthetic NL descriptions generated from company attributes (template + paraphrase), ground truth = the attributes. Metric: field-level accuracy. (Generation via LLM would add cost → needs approval; templates are free.)

**D. Image model:** not trained on synthetic data (Section 42).

### 43.9 Train / validation / test methodology (PENDING D026)
| Model | Split |
|---|---|
| Forecasting | **Time-based:** train Apr 2022–Mar 2024 (24 months), validate Apr–Sep 2024, test Oct 2024–Mar 2025. Additionally hold out **20% of companies** entirely to test generalisation to unseen companies. |
| Anomaly | Split **by company** 60/20/20; fit IF on train (contamination param from D005); tune threshold on val; report on test. |
| Invoice extraction | No training; evaluate on all 500 documents, broken down by template and format. |
| Profile extraction | Evaluation only (150 descriptions). |

Leakage controls: features computed only from past data; no ground-truth columns in feature sets; company-level splits for anomaly models.

### 43.10 Honesty & reproducibility
- Every synthetic artefact carries `is_synthetic=true`; UI badge (D048).
- Metrics on synthetic data are reported as "pipeline validation on synthetic data", never as real-world accuracy (C7).
- Generator version + seed + config hash stored with each dataset and model card.

---

## 44. AWS Engineer Runbook (S3 · Lambda · DynamoDB only)

> **Status:** **[PROPOSED — DO NOT EXECUTE]** until D015 (region), D043 (tooling), D053 (data split), D056 (invocation), D057 (IAM/logs), D067 (architecture) and D033 (retention) are approved. Commands below are illustrative placeholders using the AWS CLI.

### 44.1 Prerequisites
1. AWS account access confirmed; root user has MFA; root not used day to day.
2. Region fixed (D015; proposed `ap-south-1`).
3. Engineer IAM identity with admin rights for setup only (D057 — IAM is mandatory).
4. AWS CLI v2 installed and configured with a named profile (`--profile eprlens`).
5. Agreed naming: `eprlens-<env>-<resource>`; tags on every resource: `Project=EPRLens`, `Env=<dev|demo>`, `Owner=<name>`.
6. All infrastructure scripts and IAM policy JSON live in `infrastructure/` in git (no secrets).

### 44.2 Cost guardrails (without AWS Budgets — see D044/D057)
- Check the Billing console daily during the hackathon (if D057 permits).
- DynamoDB **on-demand** only; no provisioned capacity; no global tables; no streams unless approved.
- S3 lifecycle expiry on upload prefixes; no versioning on uploads bucket.
- Lambda: modest memory, short timeouts, concurrency limits where the account quota allows (new accounts may have a low concurrency quota that prevents reserving concurrency — check first; fallback is rate limiting in Vercel).
- No S3 public access, no S3 Transfer Acceleration, no cross-region replication.

### 44.3 S3 setup
| Bucket (proposed) | Purpose | Settings |
|---|---|---|
| `eprlens-<env>-uploads-<acct>` | User uploads: images, CSV, invoices | Block Public Access ON; SSE-S3 default encryption; lifecycle: expire `uploads/` after N days (D033); CORS allowing PUT from the Vercel domain only (for pre-signed uploads); bucket policy denying non-TLS requests |
| `eprlens-<env>-models-<acct>` | ONNX/joblib model artefacts, label maps, approved compliance-context files (D060) | Block Public Access ON; SSE-S3; **versioning ON**; read-only for Lambda roles |

Prefix convention: `uploads/<company_id>/<type>/<uuid>.<ext>`, `models/<model_name>/<version>/`, `context/<version>/`.

Illustrative:
```bash
aws s3api create-bucket --bucket eprlens-demo-uploads-<acct> --region ap-south-1 --create-bucket-configuration LocationConstraint=ap-south-1 --profile eprlens
aws s3api put-public-access-block --bucket eprlens-demo-uploads-<acct> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true --profile eprlens
```

### 44.4 DynamoDB setup (tables depend on D053)
- Mode: `PAY_PER_REQUEST`. Encryption: AWS-owned key (default, free).
- Proposed tables if D053 = A: `eprlens-<env>-analysis-runs` (PK `company_id`, SK `run_ts`), `eprlens-<env>-audit-log` (PK `company_id`, SK `event_ts#event_id`, TTL attribute `expires_at`).
- If D053 = B: a single-table design (PK/SK patterns for Company, Product, Transaction, Invoice, Run) will be proposed separately for approval.
- Point-in-time recovery: off by default (cost); owner may enable.

Illustrative:
```bash
aws dynamodb create-table --table-name eprlens-demo-analysis-runs --attribute-definitions AttributeName=company_id,AttributeType=S AttributeName=run_ts,AttributeType=S --key-schema AttributeName=company_id,KeyType=HASH AttributeName=run_ts,KeyType=RANGE --billing-mode PAY_PER_REQUEST --profile eprlens
```

### 44.5 IAM (least privilege — D057)
| Principal | Allowed actions (scoped to exact ARNs) |
|---|---|
| Lambda role per function | `s3:GetObject` on `models/*` (and `uploads/*` only for functions that read uploads); `dynamodb:PutItem/GetItem/Query/UpdateItem` on the specific tables it uses; CloudWatch Logs write **only if D057 allows** |
| Vercel invoker (IAM user or role) | `lambda:InvokeFunction` on the named functions only; `s3:PutObject` on `uploads/*` (to sign pre-signed URLs); nothing else |
| Engineer | Admin during setup; downgrade after |

- Vercel credentials stored only as Vercel server-side env vars; rotated after the hackathon; never in the repo or client bundle.
- No wildcard `*` resources except where AWS requires it.

### 44.6 Lambda functions (proposed set — final list PENDING D013)
| Function | Runtime | Purpose | Key deps | Memory / timeout (start) |
|---|---|---|---|---|
| `classify-image` | Python 3.12 | ONNX image inference (F4) | onnxruntime, numpy, Pillow | 1536 MB / 30 s |
| `validate-and-detect` | Python 3.12 | Rules validation + Isolation Forest (F8, F9) | scikit-learn, numpy | 1024 MB / 60 s |
| `forecast` | Python 3.12 | Packaging forecast (F10) | scikit-learn (or xgboost / onnxruntime) | 1024 MB / 30 s |
| `parse-invoice` | Python 3.12 | Invoice text extraction + normalisation (F7, D055) | PDF text library (TBD) | 1024 MB / 60 s |
| `rules-and-risk` | Python 3.12 or Node 20 | Applicability rules, risk score, What-If (F3, F11, F13) | none / minimal | 512 MB / 15 s |

**Packaging procedure (no containers — D051):**
1. Build dependencies for Amazon Linux on the chosen architecture (D067), e.g. `pip install --platform manylinux2014_x86_64 (or manylinux2014_aarch64) --only-binary=:all: --target build/ -r requirements.txt`.
2. Strip tests/caches (`__pycache__`, `*.dist-info` extras) to reduce size.
3. Put heavy shared deps (numpy, scikit-learn) in a **Lambda layer**; function code in its own zip.
4. **Check limits:** ≤ 250 MB unzipped (function + all layers), ≤ 50 MB zipped for direct upload (larger zips via S3), ≤ 5 layers. If exceeded → raise C13 with the owner (options: split functions, ONNX for all models, lighter libraries).
5. Models are **not** bundled; they download from S3 to `/tmp` on cold start and are cached in a module-level variable for warm invocations.
6. Environment variables: bucket names, table names, model version, region — no secrets.

Illustrative:
```bash
aws lambda create-function --function-name eprlens-demo-classify-image --runtime python3.12 --architectures arm64 --handler handler.main --role arn:aws:iam::<acct>:role/eprlens-demo-classify-image-role --zip-file fileb://classify-image.zip --layers <layer-arn> --memory-size 1536 --timeout 30 --environment "Variables={MODEL_BUCKET=...,MODEL_KEY=...}" --profile eprlens
```

### 44.7 Invocation path (D056)
- **Option SDK invoke (recommended):** Vercel route handler → `@aws-sdk/client-lambda` `Invoke` (RequestResponse) with the least-privilege IAM user.
- **Option Function URL:** `AuthType=AWS_IAM` (signed requests from Vercel); never `NONE` for data-bearing functions.
- Uploads: Vercel route generates a **pre-signed PUT URL** (short expiry, content-type and size constrained) → browser uploads directly to S3 → Vercel invokes the processing Lambda with the S3 key.
- Optional async: S3 event notification → Lambda (S3 feature, allowed) — only if D017 chooses async.

### 44.8 Testing & verification checklist
- [ ] `aws lambda invoke` each function with saved test events in `infrastructure/test-events/`; compare outputs to expected JSON.
- [ ] Cold-start and warm latency recorded for `classify-image`.
- [ ] Package sizes recorded against limits.
- [ ] IAM: confirm a function cannot read another table/bucket (negative test).
- [ ] S3: confirm public access is blocked and pre-signed URL expiry works.
- [ ] DynamoDB: write/read round trip; TTL attribute set.

### 44.9 Handover to the web team
Provide (via a non-committed secure channel): region, bucket names, table names, function names/ARNs, Vercel invoker credentials. Commit only non-secret names to `infrastructure/outputs.example.json`.

### 44.10 Teardown (after judging)
Empty and delete buckets, delete tables, delete functions/layers, delete IAM users/roles/keys, delete any log groups (if created), confirm in Billing that charges have stopped.

---

## 45. Frontend Design Specification

> **Status:** Design system **APPROVED in principle (D037)**, orange → green. Token values PENDING D063; Three.js components PENDING D062/D065; conflicts C16–C20 open. **Do not implement before D001 (pages) and D063 are approved.**

### 45.1 Design philosophy (adapted)
The owner's system is a deep "true void" dark UI where interactive elements emit coloured light, with ultra-thin borders, monospace data, glass layers, grid textures and coloured glows. For EPRLens the same mechanics are kept, with the **orange/gold energy replaced by green**, and crypto metaphors re-mapped to the EPR domain (C17 mitigation — proposed):

| Original metaphor | EPRLens metaphor (proposed) |
|---|---|
| Bitcoin orange "energy" | Regenerative green "material recovery" energy |
| Blockchain grid | Material-flow / circular-economy network grid |
| "Timeline as blockchain" | **Compliance ledger** — every invoice is a ledger entry (mirrors the guide: every invoice is reported to the portal) |
| "Digital gold / value" | Recovered material value, certificate coverage |
| "Your assets are safe" | "Your EPR data is validated before submission" |

Vibe: **Precise, Trustworthy, Regenerative.** Dark mode only (per design system).

### 45.2 Colour tokens — options for D063
| Token | Original | Option A — Green / Lime (recommended) | Option B — Green / keep Gold | Option C — Emerald / Mint |
|---|---|---|---|---|
| `--background` | #030304 | #030304 | #030304 | #030304 |
| `--surface` | #0F1115 | #0F1115 | #0F1115 | #0F1115 |
| `--foreground` | #FFFFFF | #FFFFFF | #FFFFFF | #FFFFFF |
| `--muted` | #94A3B8 | #94A3B8 | #94A3B8 | #94A3B8 |
| `--border` | #1E293B | #1E293B | #1E293B | #1E293B |
| `--primary` (was #F7931A) | Bitcoin Orange | **#22C55E** | #22C55E | #10B981 |
| `--secondary` (was #EA580C) | Burnt Orange | **#15803D** | #15803D | #047857 |
| `--tertiary` (was #FFD600) | Digital Gold | **#A3E635** (lime) | #FFD600 (gold kept) | #6EE7B7 (mint) |
| Button gradient | #EA580C → #F7931A | #15803D → #22C55E | #15803D → #22C55E | #047857 → #10B981 |
| Text gradient | #F7931A → #FFD600 | #22C55E → #A3E635 | #22C55E → #FFD600 | #10B981 → #6EE7B7 |
| Primary glow | rgba(247,147,26,·) | rgba(34,197,94,0.5) | same | rgba(16,185,129,0.5) |

**Contrast (computed, WCAG relative luminance):** #22C55E on #030304 ≈ 9.0:1 (AAA) ✓. **White on #22C55E ≈ 2.3:1 ✗**; white on #15803D ≈ 5.0:1 ✓; white on #16A34A ≈ 3.3:1 (large text only). → Proposed fix for C19: primary buttons use **void text (#030304) on green** (≈ 9:1), or a darker gradient with white text. Needs approval.

**Semantic risk colours (D066, C18):** proposed High = #EF4444 (red), Medium = #F59E0B (amber), Low = #22C55E (green), Info = #94A3B8. Risk states always carry a text label + icon, never colour alone.

### 45.3 Typography
- Headings: **Space Grotesk** 400–700 (`font-heading`); body: **Inter** 400–600 (`font-body`); data/labels/nav: **JetBrains Mono** 400–500 (`font-mono`).
- Loaded via `next/font/google` (self-hosted at build — no runtime Google request).
- Scale: hero `text-4xl sm:text-5xl md:text-7xl`, section titles `text-2xl md:text-4xl`, body `text-base md:text-lg`; headings `leading-tight`, body `leading-relaxed`; uppercase mono with `tracking-wider/widest`.
- All quantities, scores, kg/tonnes, invoice numbers and dates render in JetBrains Mono with tabular figures.

### 45.4 Radius, borders, shadows, textures
- Cards `rounded-2xl`/`rounded-xl`; buttons `rounded-full`; inputs `rounded-lg` or bottom-border; badges `rounded-full`.
- Borders 1px: rest `border-white/10`, hover `border-primary/50`, focus `border-primary`.
- **All shadows are green-tinted** (no black shadows): primary glow `0 0 20px -5px rgba(21,128,61,0.5)` / hover `0 0 30px -5px rgba(34,197,94,0.6)`; tertiary glow `0 0 20px rgba(163,230,53,0.3)` (Option A); card elevation `0 0 50px -10px rgba(34,197,94,0.1)`.
- Glass: `backdrop-blur-lg` + `bg-white/5` or `bg-black/40`.
- Grid pattern (hero): 50px grid of `rgba(30,41,59,0.5)` lines with radial mask fade.
- Radial ambient blobs: `bg-primary opacity-10 blur-[120px]`.
- Noise texture: **inline SVG/CSS noise** instead of the external transparenttextures.com URL (avoids an external asset dependency) — mechanical, but noted.

### 45.5 Components (shadcn/ui + cva, green variants)
| Component | Spec |
|---|---|
| Button / primary | Green gradient, pill, uppercase `tracking-wider`, min-h 44px, glow; hover `scale-105` + stronger glow; text colour per C19 decision |
| Button / outline | `border-2 border-white/20`, hover `border-white bg-white/10` |
| Button / ghost | hover `bg-white/10 text-primary` |
| Button / link | `text-primary`, underline on hover |
| Card / standard ("block") | `bg-surface border-white/10 rounded-2xl p-8`; hover lift `-translate-y-1`, `border-primary/50`, soft green glow; `transition-all duration-300` |
| Card / glass | `bg-black/40 backdrop-blur-lg border-white/10` |
| Card / pricing | Highlighted tier `scale-105 border-primary` + glow; others `opacity-80` (no scale on mobile) |
| Input | `bg-black/50`, bottom border `border-white/20`, h-12, focus `border-primary` + green under-glow, placeholder `white/30` |
| Badge / status | Mono, uppercase; "live" pulsing dot (`animate-ping`) for processing states |
| Icon container | `bg-secondary/20 border-secondary/50 rounded-lg p-3` "holographic node"; lucide-react icons (Recycle, Leaf, ScanLine, FileText, ShieldCheck, TrendingUp, AlertTriangle, Layers) |
| Table | Mono numerics, right-aligned quantities, row hover `bg-white/5`, anomaly rows tagged with semantic badge |
| Risk gauge | 0–100 arc, semantic colour by band (D031/D066), mono score, factor breakdown list |

`lucide-react` and `class-variance-authority` are standard shadcn/ui dependencies (treated as minor).

### 45.6 Layout & spacing
- Container `max-w-7xl`; section padding `py-24`; grid gaps `gap-8`/`gap-12`.
- No `<hr>`; sections separated by spacing and alternating `background` / `surface`.
- Grids: 1 col → `md:grid-cols-2/3` → `lg:grid-cols-4` for features; pricing `md:grid-cols-3`.
- **In-app pages (dashboard, uploads, results):** same tokens, but **reduced glow and motion** for data density and legibility (proposed — part of C16 resolution).

### 45.7 Motion
- Float (8s ease-in-out) for hero 3D group; spinning rings replaced by the Three.js orbit (C20); staggered bounce on floating stat cards; `animate-ping` for live badges.
- Interaction speed 200–300 ms.
- **`prefers-reduced-motion`:** disable float/spin/bounce, freeze the Three.js scene to a static frame.

### 45.8 Three.js components (D035 approved in principle; specifics PENDING D062)
**T1 — "Material Orbit" (landing hero) [PROPOSED]**
- **Shows:** a central translucent, faceted "recovery core" sphere with a soft green inner glow. Around it, **7 low-poly stylised waste/packaging items** orbit on two tilted rings: PET bottle (Cat I rigid plastic), flexible sachet/pouch (Cat II), multilayer carton (Cat III), crushed aluminium can (metal), glass jar (glass), cardboard box (fibre), battery cell (battery).
- **Motion:** outer ring rotates slowly clockwise, inner ring counter-clockwise (replacing the design system's CSS orbital rings); whole group floats (8s); subtle pointer parallax (±5°).
- **Optional (needs separate approval — functional addition):** hovering an item shows a glass tooltip with its material and EPR meaning (e.g., "Flexible plastic — Cat II — plastic EPR applies").
- Glass stat cards float around the scene (HTML overlay), showing only **sourced or clearly-labelled illustrative** numbers.

**T2 — "Specimen Viewer" (packaging scan result) [PROPOSED]**
- **Shows:** after the image model returns, the 3D model matching the predicted class rotates on a pedestal, encircled by a ring that fills to the confidence %. Below threshold → ring turns neutral and the UI asks the user to confirm the material.
- Links aesthetics to the actual model output (no fake data).

**T3 — "Circular Loop" (How It Works) [PROPOSED, lowest priority / optional]**
- **Shows:** small material particles travelling a closed loop Producer → Market → Consumer → Collection → Recycler → back to Producer, matching the compliance-ledger timeline.

**Technical rules [PROPOSED]:**
- Geometry is **procedural** (Lathe, Cylinder, Box, deformed Plane primitives) — no external 3D model files, so no licence checks. External CC0 GLTF models would need approval.
- Materials: `MeshPhysicalMaterial` (transmission for glass/core), emissive green rim accents; no shadow maps; glow via emissive + additive sprites (no post-processing library unless approved).
- Libraries: `three` (approved stack) + `@react-three/fiber` + `@react-three/drei` → **D065**.
- Performance: load via `next/dynamic` with `ssr:false`; DPR capped at 1.5; total < ~30k triangles; render loop paused when off-screen (IntersectionObserver) and on hidden tab; reduced item count on mobile (`h-[300px] md:h-[450px]`).
- Fallbacks: static poster image when WebGL is unavailable, reduced motion is set, or low-power devices are detected.
- Accessibility: canvas is `aria-hidden`; any meaning it conveys is also present as text.

### 45.9 Landing page structure (proposed, PENDING D001)
1. Nav (logo, mono nav links, primary CTA; mobile shows CTA only)
2. Hero — headline with gradient on final words (copy PENDING D038), subcopy, CTAs, **T1 Material Orbit** on grid + radial-blob background
3. Stats ticker (`border-y`, mono) — only sourced figures (e.g., the guide's "3.4 million tonnes of plastic waste annually", attributed) or labelled illustrative
4. Problem → capabilities: feature cards with watermark icons (scan, validate, detect, forecast, explain, simulate)
5. How it works — **compliance ledger** timeline with numbered nodes (optionally T3)
6. Disclaimer band — "Pre-compliance intelligence. Not a CPCB portal, not legal advice."
7. Pricing (asymmetric scale; placeholder prices labelled, D039)
8. Final CTA; footer

### 45.10 App pages (structure PENDING D001)
App shell: top bar + left rail (desktop), bottom/sheet nav (mobile). Dashboard uses the risk gauge, factor breakdown, trend/forecast charts (library PENDING D036; series colours drawn from tokens), anomaly table, GenAI explanation panel (glass card with "grounded in approved context" note), What-If panel with sliders and before/after mono figures.

### 45.11 Accessibility & responsiveness
- WCAG AA minimum; focus ring `focus-visible:ring-2 ring-primary`; semantic HTML; alt text; full keyboard navigation; 44px touch targets; colour never the only signal.
- Mobile-first; breakpoints sm 640 / md 768 / lg 1024 / xl 1280; keep grids, glows and gradients on mobile but lighter.

### 45.12 Proposed implementation files (after approvals; mechanical layout)
```
frontend/
  src/app/layout.tsx              # fonts via next/font, dark theme
  src/app/globals.css             # CSS variables (tokens), grid/noise utilities, keyframes, reduced-motion rules
  tailwind config / @theme        # map tokens → Tailwind (heading/body/mono fonts, colours, shadows)
  src/components/ui/              # shadcn primitives restyled via cva (button, card, input, badge, table…)
  src/components/three/           # MaterialOrbit, SpecimenViewer, (CircularLoop), shared procedural geometries
  src/components/marketing/       # hero, stats ticker, features, ledger timeline, pricing
  src/lib/design-tokens.ts        # token constants for charts / Three.js materials (single source)
```

---

## Current State & Next Step

- **State:** context.md v0.4 (proposal-only additions in Sections 46–52). Recorded owner decisions: D051, D052, D024, D035 (in principle), D037 (in principle), D064. Document as a whole still awaiting owner approval.
- **Most urgent open decisions:** D074/D070, D071/D072/D073, D008 (plastic-only scope — strongly supported by Section 41), D057, D053, D054, D055, D018, D063 (green tokens), C16 (design-system vs "avoid excess animation" — which wins).
- **Then (proposed order):** D002/D009 (datasets & taxonomy — verify [VERIFY] items first) → D025/D005/D026/D061 (synthetic spec) → D010 → D050 → D001/D011/D012 → D013/D015/D056 → D062/D065.


---

## 46. v0.4 Proposed Product Narrative — Evidence-to-Decision Material Digital Twin

**[PROPOSED — D070, D074; NOT APPROVED]** EPRLens AI may centre on a packaging-material digital twin that links documents, reconciled transactions, material quantities and improvement scenarios. This is a **data-derived operational model**, not a live physical IoT twin or a verified government compliance ledger.

**Proposed narrative:** **Collect evidence → extract and reconcile → reconstruct material flows → investigate anomalies → compare packaging redesign scenarios → export reviewable findings.** The existing confirmed F1–F15 remain the scope ceiling. Proposed additions should be folded into F8 (validation), F13 (What-If), and F14 (dashboard) where possible; true new features require D074 approval.

**Distinct questions:** (1) What materials and quantities are supported by available evidence? (2) What records conflict or remain unknown? (3) Under explicit assumptions, what packaging redesign could reduce future material use?

**Outcomes must never imply** that a corrected invoice caused physical waste reduction, that visual identification proves legal category, that an EPR credit was certified, or that forecasted tonnage equals regulatory liability.

**[CONFIRMED preserved constraints]** AWS services only S3 / Lambda / DynamoDB (D051), Supabase and Vercel where decided (D052/D053), Next.js / TypeScript / Tailwind / shadcn/ui / Three.js, circa USD 25 AWS budget, owner-only approval, synthetic invoice policy D024, no CPCB submission or legal compliance guarantee.

### 46.1 Proposed prioritization, not a scope approval

| Tier | Capability | Relation to existing features | Status |
|---|---|---|---|
| P0 | CSV + digital invoice ingestion with unit normalization | F5–F8 | Existing intent; detailed choices pending |
| P0 | Traceable quantity mismatch, decimal shift and category inconsistency | F8–F9 | Existing intent; evidence schema D072 pending |
| P0 | Packaging material-flow summary with unknown and unverified quantities visible | F14 | Digital twin interpretation D070/D071 pending |
| P0 | Deterministic weight-reduction What-If with explicit assumptions | F13 | Scenarios D032/D073 pending |
| P1 | ML anomaly scores and optional forecast, shown separately from rule findings | F9–F10 | D027–D029 pending |
| P1 | Packaging photo assistant with confidence and review | F4 | D002/D003/D009 pending |
| P1 | 3D material-flow visual and case-specific evidence viewer | F14 + Three.js | D062/D078 pending |
| P2 | Source-verified regulatory knowledge graph, supplier verification, advanced optimizing, client portfolio | Would expand scope | Requires explicit D074 approval |

## 47. Proposed Material Accounting and Digital Twin Data Model

**[PROPOSED — D071, D075, D016/D025]** Never use one field such as `waste_generated_kg` to mean packaging purchased, sold or recovered. Represent physical events and evidence separately. Keep primary quantities in kg, retain the original magnitude/unit, conversion factor and provenance.

### 47.1 Candidate entities and fields

| Entity | Core proposed fields |
|---|---|
| Company | company_id, role(s), industry, declared registration status, scope source |
| Product / PackagingSpec | product_id, material_id, component_id, verified weight_g_per_unit, category_claim, category_status, recycled_content_pct, effective_from |
| MaterialEvent | event_id, company_id, product_id, event_type, event_date, quantity_kg, original_value, original_unit, direction, counterparty_id, transaction_id, source_ref, verification_status |
| Document | document_id, file_hash, S3_key, type, uploaded_at, owner_company_id, synthetic_flag |
| EvidenceField | document_id, page, line_or_bbox, field_name, raw_text, normalized_value, unit, extraction_method, confidence_proxy, reviewer_status |
| ReconciliationFinding | finding_id, linked_record_ids, linked_evidence, rule_id, observed_value, expected_value, unit, severity, status, explanation |
| ReviewAction | action_id, finding_id, actor, timestamp, original_value, proposed_value, reason, accepted_or_rejected |
| AnalysisRun | run_id, company_id, period, rules_version, dataset_version, model_version, results_hash, created_at |
| Scenario | scenario_id, baseline_run_id, assumptions, constraints, before_after_kg, outputs, disclaimer |

**[PROPOSED]** Enumerate `event_type` values: `PURCHASED`, `PRODUCED`, `USED_IN_PACKAGING`, `PLACED_ON_MARKET`, `RETURNED`, `EXPORTED`, `COLLECTED`, `RECYCLED`, `EPR_FULFILMENT_EVIDENCE`. The last item is *evidence of a claimed fulfilment transaction*, not a verified regulatory settlement.

### 47.2 Non-negotiable accounting separation

- `sold_units * verified_packaging_weight_g / 1000` is an *estimated packaging mass associated with sold units*, only when the weight applies for that date and SKU. It is not automatically a legal EPR target.
- For a bounded inventory, `opening_inventory + inflows - outflows = closing_inventory + adjustment`, with independently defined events; verify signs and prevent double-counting. Do not infer physical waste from unobserved activity.
- Returns, exports, supplier transfers and stock movements must be treated separately. Their exact impact on EPR obligations remains D030/D068 and requires authoritative sources.
- `recycled_kg <= collected_kg <= waste_generated_kg` is an applicable **synthetic test invariant only for a narrowly defined matched cohort/period**; it is not a universal rule across different reporting systems or inventories.
- Show `unknown`, `estimated`, `declared`, `document-supported`, and `reviewed` statuses explicitly. Never replace missing data with zero.
- Synthetic demo records must preserve consistent source identifiers and hashes across PDFs, CSVs, APIs and frontend views.

### 47.3 Example linked case

**[PROPOSED — synthetic demonstration]** Invoice line says `0.5 MT`, corresponding internal transaction says `500 MT`. Normalization yields 500 kg versus 500,000 kg; discrepancy 499,500 kg. The output links both source values and records the mismatch without silently changing the material ledger. A reviewer may propose a correction; the original remains immutable. No automatic claim of a 499.5 tonne decrease in actual physical waste.

## 48. Proposed Reconciliation, Provenance and Regulatory Guardrails

**[PROPOSED — D072, D076, D080]**

1. Parse digital PDFs and CSVs; capture source document ID, page/line, raw field, normalized field and extraction status.
2. Match invoices to transactions by a configured composite identity (company/counterparty/invoice/date/line/product), **not invoice number alone**; test allowed repeated invoice numbers and valid split categories.
3. Run deterministic rules first for unit conversion, completeness, duplicated line identity, product specification version, numerical tolerances, impossible balances and inconsistent attributes.
4. Run optional anomaly models separately. `model_anomaly_score` must not be labelled `probability_of_noncompliance`.
5. Display each finding with reason, value differences, supporting documents, rule/version, uncertainty and human review state.
6. A reviewer can accept/reject suggested correction; preserve original, correction rationale, actor and timestamp in append-only audit history.
7. LLM may explain grounded evidence and rules but cannot invent legal obligations or approve corrections automatically.
8. Regulatory sources need authority, citation/url, issue date, effective date, jurisdiction, rule version and human verification. The supplied handbook is a secondary educational source, not guaranteed current law.

### 48.1 Example shared JSON response [PROPOSED — NOT FINAL API]

```json
{
  "schema_version": "0.4-proposal",
  "analysis_id": "demo-run-001",
  "synthetic": true,
  "finding_id": "demo-finding-001",
  "finding_type": "quantity_mismatch",
  "severity": "high",
  "review_status": "open",
  "expected": {"value": 500, "unit": "kg", "source_ref": "pdf-demo-12:p1:line3"},
  "observed": {"value": 500000, "unit": "kg", "source_ref": "csv-demo:row67"},
  "difference_kg": 499500,
  "rule_id": "QTY_MATCH_V1",
  "rule_version": "proposal",
  "legal_determination": false
}
```

## 49. Proposed Packaging Reduction and Decision Simulator

**[PROPOSED — D073, D032, D068]** Start with an evidence-backed packaging-weight scenario, not an unsourced EPR liability calculator.

- Baseline `material_kg = units * verified_g_per_unit / 1000`.
- Scenario for `reduction_pct`: `scenario_weight_g = baseline_weight_g * (1 - reduction_pct/100)`.
- At unchanged units, `avoided_material_kg = baseline_material_kg - scenario_material_kg`.
- Distinguish *hypothetical future material avoided* from measured waste reduced; account for design feasibility, safety and functionality limitations.
- Optional constraints for later review: packaging integrity, costs/unit, lead time, supplier capacity, recycled-content qualification and recyclability — no optimizer may assume undocumented feasibility.
- If unit price data are supplied and valid, show estimated packaging material spending difference; omit legal penalty/credit savings absent approved regulation and source data.
- Forecasts must carry data vintage, model version, baseline comparator, uncertainty range and `synthetic_only` limitations when trained on synthetic datasets.

**Proposed example:** 100,000 products/month at 25 g plastic each = 2,500 kg/month. A 20% weight reduction would imply 2,000 kg/month and **500 kg/month potential material reduction**, assuming unchanged sales and valid redesigned packaging.

## 50. Four Work Packages — Proposed v0.4 Handoff Contract

The four `*_REVISED.pdf` documents are aligned proposal artifacts, not owner-approved overrides. Each developer must keep earlier repo requirements and no secrets in Git.

| Work package | Core responsibility | Mandatory proposed repo artifacts | Acceptance evidence |
|---|---|---|---|
| WP1 — Real Public Data ML/DL | Packaging image material assistant; document dataset licences/domain gap; export inference and calibrated uncertainty; human correction integration | `ml/datasets/DATASET_REGISTER.md`, `ml/datasets/LICENSES.md`, `ml/datasets/label_map.yaml`, `ml/scripts/prepare_images.py`, `ml/scripts/train_image_classifier.py`, `ml/scripts/evaluate_image_classifier.py`, `ml/scripts/export_onnx.py`, `ml/evaluation/`, `ml/models/README.md`, `tests/ml/` | Real-image holdout and confusion matrix; Lambda-compatible model and response; unsupported legal category never inferred |
| WP2 — Synthetic Data + 1,000 Invoices | Deterministic material-flow data factory, invoices/ground truth, injected anomalies and reconciliation/what-if fixtures, ML comparisons | `synthetic-data/config.yaml`, `synthetic-data/generate.py`, `synthetic-data/generators/`, `synthetic-data/templates/invoices/`, `synthetic-data/schemas/`, `synthetic-data/MANIFEST.example.json`, `ml/scripts/train_forecast.py`, `ml/scripts/train_anomaly.py`, `tests/synthetic/` | Exactly 1,000 fictitious digital PDFs + 1,000 ground-truth JSONs; 10+ templates; reproducible hashes/seed; explicit material-flow invariants and counterexamples |
| WP3 — AWS Engineer | Private S3 uploads/models; Lambda invoice extraction/reconciliation/ledger/scenario; DynamoDB results/audit per approved split; secure Vercel invocation | `infrastructure/README.md`, `infrastructure/scripts/`, `infrastructure/iam/`, `infrastructure/test-events/`, `backend/lambdas/`, `backend/shared/contracts/`, `.env.example` | Reproducible deployment; local Lambda invocation tests, versioned contracts, private files, no browser AWS credentials, resource teardown |
| WP4 — Frontend Developer | Unified upload → evidence findings → material-flow digital twin → forecast/scenario view; Three.js only per D062/D078 | `frontend/README.md`, `frontend/src/app/`, `frontend/src/components/`, `frontend/src/lib/contracts.ts`, `frontend/src/lib/mocks/`, `frontend/tests/`, `docs/demo-flow.md` | Fresh clone mock mode; live mode against schemas; visual distinction between material events; accessible 3D fallback; clear synthetic/legal disclaimers |

**Shared integration precedence [PROPOSED — D079]:** contracts/schema first → synthetic fixture and source references → AWS local handlers → frontend mocks → live integration → reproducible end-to-end acceptance run. Developers may work independently while responses conform to the same versioned contract. Large datasets and PDFs should be regenerated/downloaded by manifest, not committed blindly.

### 50.1 Candidate GitHub layout changes [PROPOSED — D041/D079]

```text
backend/shared/contracts/             # JSON Schemas, examples, status enums
backend/shared/accounting/            # proposed common unit conversions/flow rules
synthetic-data/schemas/               # generator-ground truth and traceable events
synthetic-data/outputs/sample/        # a few tiny committed demo samples only
ml/evaluation/                        # actual measurements, never invented
infrastructure/test-events/           # local and cloud invocation events
frontend/src/lib/mocks/               # contract-identical fixtures
docs/source-of-truth/                 # dated references and rules versions
docs/demo-flow.md                     # consistent 3-minute narrative
docs/integration-checklist.md         # exact acceptance matrix
```

## 51. Proposed Evaluation / Acceptance Matrix

**[PROPOSED — D077]** No metric may be asserted as achieved until tests run; all results remain TBD.

| Layer | Checks | Claim limitation |
|---|---|---|
| Invoice extraction | normalized exact-field accuracy, line-item recall, document reference fidelity, unit conversions | Synthetic PDF test performance only |
| Reconciliation | rule-wise precision/recall, false positives on legitimate shared invoice identifiers, human override audit | Synthetic cases do not prove real-world regulatory correctness |
| Material ledger | opening/inflow/outflow/closing identity under documented boundary; no conflation across events; missing-data states | Estimated packaging sold is not necessarily generated waste |
| Image assistant | macro-F1, calibration, class confusion, team-photographed packaging holdout, uncertainty | Image class is not official legal category |
| Forecast/anomaly ML | time-based and held-out-company tests, naive baselines, model-vs-rules precision/recall | Synthetic generator leakage and domain gaps must be stated |
| Scenarios | zero-change invariance, monotonic reduction for fixed units, multiple-SKU aggregate checks, unsupported assumptions | Hypothetical avoided material is not verified pollution reduction |
| Infrastructure | clean-clone local mocks, Lambda package/build tests, S3 privacy, IAM negative tests, cost review, end-to-end contract | Only services approved under D051, with D057 dependency ruling |
| UI | inspect source evidence, accept/reject correction, separate supported/estimated/unknown, reduced-motion fallback | No compliance certification, regulatory filing or invented cost savings |

## 52. v0.4 Pending Scope Approvals and Next Actions

**Document update approved by user request; product decisions remain pending.** No entry has been added to Section 38 because the instruction to update documentation is not an explicit approval of individual architecture, scope or regulatory choices.

**Decision sequence [PROPOSED]:** D074/D070 (scope and narrative) → D008/D030/D080 (plastic-only regulatory scope and authoritative references) → D071/D075 (flow semantics) → D072/D076 (reconciliation and review) → D073/D032 (optimization) → D079/D041/D017 (shared contracts/repo/API) → D053/D056/D057 (cloud security and data split) → D077 (tests) → D062/D078 (3D role) → D050 (final feature cut line).

**Source precedence:** owner decisions and existing approved constraints → official verified regulations for legal rules → signed shared contracts and synthetic data manifest → revised work-package proposals → display copy. The ebook remains a valuable educational guide; it is not sufficient evidence for current portal URLs, effective thresholds or EPR savings calculations.

**Current build status:** No claim of implemented code, trained models, populated databases, completed tests or production readiness has been made.
