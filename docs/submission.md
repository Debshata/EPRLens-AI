# Submission pack — EPRLens AI

Everything needed for the hackathon form except the video (record tomorrow). Facts below match the repo; nothing here is a claim the code does not back.

## Form fields
| Field | Text |
|---|---|
| Project name | **EPRLens AI** |
| Track | **Waste and Energy** (recycling and packaging-waste accountability) |
| Tagline | Catch packaging-waste reporting mistakes before you file. |
| Repository | <https://github.com/Debshata/EPRLens-AI> (private; branch `feat/synthetic-entity-master`) — add the judges as collaborators if the form requires access |
| Live demo | <https://vnt7lqwiplspftmctdrlriejfa0jclzy.lambda-url.ap-south-1.on.aws/> (all on AWS) |
| Demo video | _paste after recording_ |
| Team | Vaibhav Jain (frontend, AWS backend and infrastructure) · Debshata Choudhury (synthetic data, forecast and anomaly models) · Ishani Jindal (packaging image classifier) — confirm roles before submitting |

### Short description (≈300 characters)
EPRLens AI is a pre-compliance check for Indian packaging EPR. Upload invoices, records and a packaging photo; it reconciles quantities in kg, flags mismatches like 0.5 MT vs 500 MT, forecasts next month's volume, and simulates lighter packaging — all on AWS Lambda, S3 and DynamoDB. Synthetic demo data.

### Full description
**Problem.** Under Extended Producer Responsibility, producers, importers and brand owners must report the plastic packaging they place on the Indian market. Reporting mistakes — a unit slip (0.5 MT entered as 500 MT is an example cited in the EPR handbook the team used), duplicate invoices, wrong categories — tend to surface only at filing time, when fixing them is slow and costly. Wrongly reported packaging also hides the real volume of waste that needs collecting and recycling.

**What we built.** A workspace where a company uploads a transaction CSV, a digital invoice PDF and a packaging photo, and gets: (1) invoice fields extracted with page/line sources and units normalised to kg; (2) invoice-vs-record findings with the rule that fired, side-by-side original values and a reviewer workflow whose audit trail never overwrites the original; (3) a next-month packaging forecast with its baseline and limits; (4) anomaly findings, with deterministic rules and statistical outliers shown separately; (5) a probable-material classification for a packaging photo (never an official EPR category); and (6) a what-if simulator for lighter packaging (hypothetical kg and tonnes).

**Who it is for.** Compliance and sustainability teams at producers/brand owners, and EPR consultants who review client data before it is filed.

**What changes for people.** Errors are caught before filing, every number links to its source, and unknown values stay unknown instead of being silently zeroed. The tool is explicit about being decision support, not a filing or a certificate.

## Built on AWS (judging criterion 2)
- **AWS Lambda ×8:** seven functions for the backend — `classify-image`, `parse-invoice`, `reconcile`, `forecast`, `detect-anomaly`, `scenario-engine`, `company-data` — plus one that hosts the Next.js app behind a public Function URL (Lambda Web Adapter).
- **Amazon S3:** private, encrypted, TLS-only buckets; browser uploads straight to S3 with 5-minute presigned URLs pinned to file type and size; ONNX/joblib model artifacts; 7-day expiry on uploads.
- **Amazon DynamoDB:** on-demand table for analysis results and the audit trail (model and rule versions, S3 keys — never raw files).
- **Security and cost:** least-privilege IAM role per function, no AWS keys in the browser or repo (the hosted app uses its own IAM role), no always-on resources, CloudWatch logs kept 3 days. Whole stack is created and removed with scripts in `infrastructure/scripts/`.

## What is novel / why it is credible
- Reads real digital PDFs with a parser measured on 1,000 synthetic invoices over 12 layouts: invoice number, date, vendor, total and line count 100%, line quantities 3,839/3,846, kg 3,846/3,846 (`backend/evaluation/invoice_parser_metrics.json`).
- Invoice number alone is never used to match or de-duplicate (the handbook allows several invoices to share a number); matching uses a composite identity.
- Honest AI: no invented confidence intervals, model scores are not probabilities of non-compliance, forecasts beyond month one are labelled "projected", every demo screen carries a "Synthetic demo data" badge.
- Works two ways from one codebase: mock mode (no AWS, for anyone to run) and live mode (real AWS), switched by configuration.

## Design and usability notes
Dark, green, data-dense UI; every error says what the user can do next; confirmed / declared / estimated / needs-review / unknown states look different (text + icon + border, never colour alone); keyboard-operable tables and drawers; works at phone width (390 px) and desktop; 3D material-flow is optional with a full 2D and table equivalent.

## Execution evidence
78 frontend unit/component tests, 6 end-to-end tests (desktop + mobile), 37 backend tests, an 8-function AWS smoke test, 11 live API checks (also run against the public URL) and a real-browser live-mode test that uploads to S3 and runs the Lambdas.

## Known limitations (say them before a judge does)
Synthetic data only; one pre-seeded demo company; no login on the public demo; review decisions live in the browser; image model trained on public waste photos so real-packaging accuracy will be lower; applicability hints come from a secondary handbook and say "requires verification".

---

## Demo video — 3:00 script (record tomorrow)
Use the **live URL** in a clean browser window (1280×800), zoom 100%, notifications off. Have these ready: `frontend/public/samples/DOC_000832.pdf`, `transactions_demo.csv`, and a **real photo of a plastic bottle** on your phone/desktop (the bundled drawings are not photos; the carton drawing works, the bottle drawing is called "other" by the model).

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Landing page | "Packaging EPR reporting in India is easy to get wrong and hard to fix late. EPRLens checks your evidence before you file — pre-compliance, not a filing tool. Everything you'll see is synthetic demo data." |
| 0:20–0:35 | Explore demo → create workspace | "A demo company, EcoFizz Beverages. Note the applicability hint says 'requires verification' — we never claim compliance." |
| 0:35–1:05 | Evidence: upload the **bottle photo**, then the **invoice PDF**, then the **CSV** | "The photo goes straight to S3 and a Lambda runs a MobileNet model: a probable material with its confidence, never an official category. The invoice is parsed on Lambda — page and line sources, original unit next to the kg value: 0.5 tonne is 500 kg." |
| 1:05–1:50 | Run reconciliation → open the finding | "The record says 500 tonnes. After converting to kg: 500 versus 500,000 — a 499,500 kg difference, exactly 1,000 times too big. The rule that fired is shown, with a plain explanation. Accept a correction with a reason: the original value stays visible and the audit history keeps it." |
| 1:50–2:20 | Dashboard | "Totals in kg and tonnes, a forecast from an XGBoost model on Lambda with its baseline and a clear 'interval unavailable' — we don't invent uncertainty — and rule findings kept apart from statistical outliers." |
| 2:20–2:40 | Simulator | "What if each bottle used 20 grams instead of 25? 100,000 units: 2,500 kg down to 2,000 kg — a hypothetical 500 kg, clearly labelled as not measured savings." |
| 2:40–3:00 | AWS console: Lambda functions list, S3 buckets, DynamoDB table (Mumbai) | "All of it runs on AWS: eight Lambda functions including the website itself, private S3 buckets with presigned uploads, and DynamoDB for results and the audit trail. No keys in the browser, nothing always-on. EPRLens AI — find the mistake before the regulator does." |

### Before recording
- Open the live URL once to warm the function (first load takes ~2 s). Reset demo state (sidebar → Reset demo).
- Do a dry run; keep the video ≤ 3:00. Do **not** show AWS account ids, access keys or the billing page.
- Upload the video, paste the link in the form and in `README.md`.

### Submission checklist
- [ ] AWS Builder Center student verification completed (required to compete).
- [ ] Registered/checked in on the hackathon page; team of ≤ 4 listed.
- [ ] Repo access for judges (private repo owned by Debshata) or a public mirror, as the form requires.
- [ ] Live URL opens in a private window; demo video link added.
- [ ] Optional: blog post on AWS Builder Center (top posts win prizes) — can reuse the sections above.
- [ ] After judging: `bash infrastructure/scripts/99-destroy.sh --yes`, then deactivate the `eprlens-admin` access key.
