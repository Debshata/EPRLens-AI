# AWS account setup (one time, ~20 minutes)

Hackathon: Environmental Hacks by WeMakeDevs × AWS — <https://www.wemakedevs.org/aws/env>. To be prize-eligible a project must use an AWS open-source tool or be deployed on AWS; student verification on AWS Builder Center is required to compete.

Never paste access keys into chat, GitHub or screenshots. They live only in `~/.aws/credentials`.

1. **Student verification** — <https://builder.aws.com>: create a free AWS Builder ID and complete student verification (same email as your hackathon registration).
2. **Create the account** — <https://bit.ly/wmd-aws-free> (→ <https://aws.amazon.com/free>) or <https://portal.aws.amazon.com/billing/signup>: root email + account name, email code, root password, **Personal**, contact details, payment method (debit/RuPay accepted, ≈ ₹2 verification), phone verification, choose the **Free plan**. New accounts get up to $200 credits. Sign in at <https://console.aws.amazon.com> as Root user once activated.
3. **Secure it** — root user: Security credentials → assign an MFA device. IAM → Users → create `eprlens-admin` with `AdministratorAccess` → Security credentials → create an access key (use case: CLI).
4. **Connect the CLI** — `aws configure --profile eprlens` (region `ap-south-1`, output `json`), then `aws sts get-caller-identity --profile eprlens` must print your account id and `user/eprlens-admin`. (Answer `n` if asked about AWS skills / MCP server.)
5. **Credits** — Console → Billing and Cost Management → Credits. Request the extra $25 hackathon code only after the free credits run out (team leader, one form per team).

The console region selector shows "Global" on IAM/Billing pages; switch it to **Asia Pacific (Mumbai)** when you want to look at S3, Lambda or DynamoDB resources created by `infrastructure/scripts/`.
