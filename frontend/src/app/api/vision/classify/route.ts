import { z } from "zod";
import { ImageResult } from "@/lib/contracts";
import { serverEnv } from "@/lib/server/env";
import { invokeLambda } from "@/lib/server/lambda";
import { handle } from "@/lib/server/route-helpers";

export const runtime = "nodejs";

export function POST(req: Request) {
  return handle(req, {
    input: z.object({ company_id: z.string().min(1), s3_key: z.string().min(1) }),
    output: ImageResult,
    run: (i) => {
      const env = serverEnv();
      return invokeLambda(env.LAMBDA_CLASSIFY_IMAGE, { action: "classify_image", company_id: i.company_id, s3: { bucket: env.UPLOADS_BUCKET, key: i.s3_key } }, env.AWS_REGION);
    },
  });
}
