import { z } from "zod";
import { ForecastResponse } from "@/lib/contracts";
import { serverEnv } from "@/lib/server/env";
import { invokeLambda } from "@/lib/server/lambda";
import { handle } from "@/lib/server/route-helpers";

export const runtime = "nodejs";

export function GET(req: Request) {
  return handle(
    req,
    {
      input: z.object({ company_id: z.string().min(1) }),
      output: ForecastResponse,
      run: (i) => {
        const env = serverEnv();
        return invokeLambda(env.LAMBDA_FORECAST, { action: "forecast", company_id: i.company_id }, env.AWS_REGION);
      },
    },
    "query",
  );
}
