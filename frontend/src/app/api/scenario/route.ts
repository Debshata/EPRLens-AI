import { z } from "zod";
import { ScenarioRequest, ScenarioResult } from "@/lib/contracts";
import { SCENARIO_DISCLAIMER, SCENARIO_FORMULA } from "@/lib/scenario-math";
import { serverEnv } from "@/lib/server/env";
import { invokeLambda } from "@/lib/server/lambda";
import { handle } from "@/lib/server/route-helpers";

export const runtime = "nodejs";

const Raw = z.object({ baseline_kg: z.number(), proposed_kg: z.number(), reduction_kg: z.number() });

/** Lambda contract (WP3): { units, current_g_per_unit, proposed_g_per_unit } → { baseline_kg, proposed_kg, reduction_kg }. */
export function POST(req: Request) {
  return handle(req, {
    input: ScenarioRequest,
    output: ScenarioResult,
    run: async (i) => {
      const env = serverEnv();
      const raw = Raw.parse(await invokeLambda(env.LAMBDA_SCENARIO_ENGINE, { action: "what_if", units: i.units, current_g_per_unit: i.baseline_g_per_unit, proposed_g_per_unit: i.proposed_g_per_unit }, env.AWS_REGION));
      return {
        ...raw,
        reduction_pct: raw.baseline_kg > 0 ? (raw.reduction_kg / raw.baseline_kg) * 100 : 0,
        formula: SCENARIO_FORMULA,
        hypothetical: true,
        disclaimer: SCENARIO_DISCLAIMER,
      };
    },
  });
}
