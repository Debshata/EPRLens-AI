import { z } from "zod";
import { DashboardSummary } from "@/lib/contracts";
import { companyDataFn } from "@/lib/server/env";
import { invokeLambda } from "@/lib/server/lambda";
import { handle } from "@/lib/server/route-helpers";

export const runtime = "nodejs";

export function GET(req: Request) {
  return handle(
    req,
    {
      input: z.object({ company_id: z.string().min(1) }),
      output: DashboardSummary,
      run: (i) => {
        const { fn, region } = companyDataFn("The dashboard summary");
        return invokeLambda(fn, { action: "dashboard_summary", company_id: i.company_id }, region);
      },
    },
    "query",
  );
}
