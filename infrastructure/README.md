# EPRLens infrastructure (AWS: S3 · Lambda · DynamoDB only)

Scripts use the AWS CLI v2 and the `eprlens` profile in `ap-south-1` (override with `AWS_PROFILE`, `AWS_REGION`, `PREFIX`). They are idempotent and macOS bash 3.2 compatible. Account setup: [`../docs/aws-account-setup.md`](../docs/aws-account-setup.md).

| Step | Script | Creates / does |
|---|---|---|
| 1 | `scripts/10-storage.sh` | 2 private, encrypted, TLS-only S3 buckets (uploads: 7-day expiry + CORS for localhost; models) and DynamoDB table (PAY_PER_REQUEST) |
| 2 | `scripts/20-iam.sh` | One least-privilege execution role per Lambda; narrow IAM user `…-frontend` (invoke `…-*` functions, `s3:PutObject` on `uploads/*` for presigned URLs) |
| 3 | `scripts/30-package.sh` | Builds `build/<fn>.zip` for Linux x86_64 / Python 3.12 (no Docker) |
| 4 | `scripts/40-deploy.sh` | Uploads zips via S3 and creates/updates the 7 functions, 3-day log retention |
| 5 | `scripts/50-seed.sh` | Uploads models (`models/material-classifier|forecast|anomaly/v1/`) and demo reference data (`reference/`) |
| 6 | `scripts/60-smoke.sh` | Invokes every function once with the bundled samples; prints PASS/FAIL |
| 7 | `scripts/70-frontend-env.sh` | Writes git-ignored `frontend/.env.local` for live mode (secret never printed) |
| 8 | `scripts/35-package-web.sh` + `scripts/80-web-deploy.sh` | Builds the Next.js standalone server and runs it in a Lambda (Lambda Web Adapter layer) behind a public Function URL; the function uses its own IAM role, **no access keys stored anywhere** |
| – | `scripts/99-destroy.sh --yes` | Deletes everything this project created (functions incl. the web function, roles, frontend user, table, buckets, log groups) |
| – | `scripts/45-redeploy.sh <fn>` | Fast redeploy of one function after a code change |
| – | `scripts/65-live-api-check.py [url]` | Proves live mode end to end through the Next.js `/api/*` routes (real S3 + Lambda + DynamoDB) |

Browser check of live mode: `cd frontend && npm run build && npx next start -p 3000`, then `npx playwright test -c playwright.live.config.ts` (browser uploads straight to S3 with presigned URLs; CORS allows `localhost:3000/3100`).

Cost note: new AWS accounts allow 10 concurrent Lambda executions in total, so reserved concurrency cannot be set; that account-wide limit is also a hard ceiling on load (worst case, all slots busy 24/7, is on the order of $15/day — my estimate from public pricing). Delete the stack when judging is over.

Cost control: no always-on resources (no EC2, no provisioned capacity, no API Gateway/Textract/Bedrock/ECR/SageMaker). Lambda memory/timeouts are small (`scripts/config.sh`); uploads expire after 7 days; logs are kept 3 days. Lambda also writes to CloudWatch Logs — an implicit requirement.

IAM note: `eprlens-admin` (AdministratorAccess) is only needed while running these scripts; deactivate its key afterwards. The public site needs no keys (its own IAM role). `70-frontend-env.sh` is only for running the UI locally against AWS.

## Public site (all-AWS)
<https://vnt7lqwiplspftmctdrlriejfa0jclzy.lambda-url.ap-south-1.on.aws/> — Next.js on Lambda (Function URL, `AuthType NONE`). Redeploy the UI after a change: `bash scripts/35-package-web.sh && bash scripts/80-web-deploy.sh`. Tear down with `99-destroy.sh --yes`.


## Status
Deployed and verified on 2026-10-10 in `ap-south-1`: `60-smoke.sh` (all 8 invocations), `65-live-api-check.py` (11 checks) and the live browser test pass. Run scripts with bash (`bash scripts/…`), not by sourcing them from zsh.
