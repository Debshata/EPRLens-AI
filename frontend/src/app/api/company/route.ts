import { z } from "zod";
import { CompanyBundle, CompanyInput } from "@/lib/contracts";
import { companyDataFn } from "@/lib/server/env";
import { invokeLambda } from "@/lib/server/lambda";
import { handle } from "@/lib/server/route-helpers";

export const runtime = "nodejs";

export function GET(req: Request) {
  return handle(
    req,
    {
      input: z.object({ demo: z.string().optional(), company_id: z.string().optional() }),
      output: CompanyBundle,
      run: (i) => {
        const { fn, region } = companyDataFn("Company storage");
        return invokeLambda(fn, { action: "get_company_profile", company_id: i.company_id ?? (i.demo ? "COMP_0001" : undefined) }, region);
      },
    },
    "query",
  );
}

export function POST(req: Request) {
  return handle(req, {
    input: CompanyInput,
    output: CompanyBundle,
    run: (i) => {
      const { fn, region } = companyDataFn("Company storage");
      return invokeLambda(fn, { action: "create_company", company: i }, region);
    },
  });
}
