import { z } from "zod";
import { ReconciliationResponse } from "@/lib/contracts";
import { serverEnv } from "@/lib/server/env";
import { invokeLambda } from "@/lib/server/lambda";
import { handle } from "@/lib/server/route-helpers";

export const runtime = "nodejs";

export function POST(req: Request) {
  return handle(req, {
    input: z.object({ company_id: z.string().min(1), document_id: z.string().min(1), csv_s3_key: z.string().min(1) }),
    output: ReconciliationResponse,
    run: (i) => {
      const env = serverEnv();
      return invokeLambda(env.LAMBDA_RECONCILE, { action: "reconcile", company_id: i.company_id, document_id: i.document_id, csv: { bucket: env.UPLOADS_BUCKET, key: i.csv_s3_key } }, env.AWS_REGION);
    },
  });
}
