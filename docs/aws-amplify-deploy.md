# Deploying the frontend on AWS Amplify Hosting

Result: a public HTTPS link (`https://<branch>.<app-id>.amplifyapp.com`), with the Next.js server code running on Amplify and **no AWS keys stored anywhere** — it uses the IAM role `eprlens-demo-amplify-ssr` (invoke `eprlens-demo-*` Lambdas, presign uploads).

Free-tier allowances (Amplify pricing page): 1,000 build minutes, 5 GB storage, 15 GB served, 500,000 SSR requests and 100 GB-hours of SSR compute per month. This demo stays inside them.

## One-time steps (you, in the console — ~5 minutes)
1. Open **AWS Amplify** in the console, region **Asia Pacific (Mumbai)** → **Create new app** → **GitHub** → authorize the AWS Amplify GitHub app.
2. Pick repository `Debshata/EPRLens-AI`, branch `feat/synthetic-entity-master`.
3. Tick **My app is a monorepo** and enter the root `frontend`. The build settings come from `frontend/amplify.yml`.
4. Accept the default build service role. Click **Save and deploy** (the first build may fail or show errors until step 5 — that is expected).
5. Copy the **App ID** from the app's page (looks like `d1abc2defg3`) and send it to Claude.

## Then (Claude, CLI)
```bash
bash infrastructure/scripts/85-amplify-config.sh <app-id>     # platform, compute role, env vars, start build
bash infrastructure/scripts/86-cors.sh <app-id>.amplifyapp.com # browser uploads from the Amplify domain
python3 infrastructure/scripts/65-live-api-check.py https://<branch>.<app-id>.amplifyapp.com
```
Every push to the branch triggers a new build automatically. To remove: delete the Amplify app in the console, then `bash infrastructure/scripts/99-destroy.sh --yes`.
