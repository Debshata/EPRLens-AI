import "server-only";
import { z } from "zod";
import { NotAvailableError } from "./http";

/** Server-only configuration. Never imported by client code; values are never prefixed NEXT_PUBLIC_. */
const Env = z.object({
  AWS_REGION: z.string().default("ap-south-1"),
  UPLOADS_BUCKET: z.string().min(1),
  LAMBDA_PARSE_INVOICE: z.string().min(1),
  LAMBDA_RECONCILE: z.string().min(1),
  LAMBDA_CLASSIFY_IMAGE: z.string().min(1),
  LAMBDA_FORECAST: z.string().min(1),
  LAMBDA_DETECT_ANOMALY: z.string().min(1),
  LAMBDA_SCENARIO_ENGINE: z.string().min(1),
  /** Company profile / dashboard summary / simulator catalogue. Not in the WP3 function list yet — see docs/frontend-api-contracts.md. */
  LAMBDA_COMPANY_DATA: z.string().optional(),
});
export type ServerEnv = z.infer<typeof Env>;

export class MissingConfigError extends Error {
  readonly missing: string[];
  constructor(missing: string[]) {
    super(`Server configuration is incomplete: ${missing.join(", ")}.`);
    this.missing = missing;
  }
}

export function serverEnv(source: Record<string, string | undefined> = process.env): ServerEnv {
  const r = Env.safeParse(source);
  if (!r.success) throw new MissingConfigError(r.error.issues.map((i) => String(i.path[0])));
  return r.data;
}

/** Function that serves company profile / dashboard summary / simulator catalogue; optional until the backend defines it. */
export function companyDataFn(feature: string): { fn: string; region: string } {
  const env = serverEnv();
  if (!env.LAMBDA_COMPANY_DATA) throw new NotAvailableError(feature);
  return { fn: env.LAMBDA_COMPANY_DATA, region: env.AWS_REGION };
}
