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
| – | `scripts/45-redeploy.sh <fn>` | Fast redeploy of one function after a code change |
| – | `scripts/65-live-api-check.py [url]` | Proves live mode end to end through the Next.js `/api/*` routes (real S3 + Lambda + DynamoDB) |
| 8 | `scripts/80-amplify-iam.sh` | IAM role the hosted Next.js server uses instead of keys (invoke `…-*` functions, presign `uploads/*`) |
| 9 | `scripts/85-amplify-config.sh <app-id>` | After the Amplify app is created in the console: WEB_COMPUTE platform, compute role, env var names, start a build |
| 10 | `scripts/86-cors.sh <amplify-domain>` | Allow browser uploads to presigned S3 URLs from the Amplify domain |
| – | `scripts/99-destroy.sh --yes` | Deletes everything above (also delete the Amplify app and `…-amplify-ssr` role) |

Browser check of live mode: `cd frontend && npm run build && npx next start -p 3000`, then `npx playwright test -c playwright.live.config.ts` (browser uploads straight to S3 with presigned URLs; CORS allows `localhost:3000/3100`).

Cost control: no always-on resources (no EC2, no provisioned capacity, no API Gateway/Textract/Bedrock/ECR/SageMaker). Lambda memory/timeouts are small (`scripts/config.sh`); uploads expire after 7 days; logs are kept 3 days. Lambda also writes to CloudWatch Logs — an implicit requirement.

IAM note: `eprlens-admin` (AdministratorAccess) is only needed while running these scripts. Afterwards you can detach it or deactivate its key.

## Public site (all-AWS)
<https://vnt7lqwiplspftmctdrlriejfa0jclzy.lambda-url.ap-south-1.on.aws/> — Next.js on Lambda (Function URL, `AuthType NONE`). Redeploy the UI after a change: `bash scripts/35-package-web.sh && bash scripts/80-web-deploy.sh`. Tear down with `99-destroy.sh --yes`.

Cost/abuse note: new AWS accounts allow 10 concurrent Lambda executions in total, so reserved concurrency cannot be set; that account-wide limit is also a hard ceiling on load. Worst case with all 10 slots busy 24/7 is on the order of $15/day (my estimate from public pricing), so delete the stack when judging is over.

## Status
Deployed and verified on 2026-10-10 in `ap-south-1`: `60-smoke.sh` (all 8 invocations), `65-live-api-check.py` (11 checks) and the live browser test pass. Run scripts with bash (`bash scripts/…`), not by sourcing them from zsh.
