import "server-only";
import { NextResponse } from "next/server";
import type { z } from "zod";
import { apiError, liveGuard, toErrorResponse } from "./http";

/** Shared shell for every route: live guard → parse input → run → validate output → standard errors. */
export async function handle<I, O>(
  req: Request,
  opts: { input: z.ZodType<I>; output: z.ZodType<O>; run: (input: I) => Promise<unknown> | unknown },
  source: "json" | "query" = "json",
): Promise<NextResponse> {
  const blocked = liveGuard();
  if (blocked) return blocked;
  try {
    const raw = source === "json" ? await req.json().catch(() => null) : Object.fromEntries(new URL(req.url).searchParams);
    const parsed = opts.input.safeParse(raw);
    if (!parsed.success) {
      return apiError(400, "invalid_request", `The request is not valid: ${parsed.error.issues.map((i) => `${i.path.join(".") || "body"} ${i.message}`).join("; ")}.`, "Check the values you sent and try again.");
    }
    const result = opts.output.safeParse(await opts.run(parsed.data));
    if (!result.success) {
      return apiError(502, "contract_mismatch", "The backend response did not match the agreed contract.", "Ask the backend owner to align the response with docs/frontend-api-contracts.md, or switch to mock mode.");
    }
    return NextResponse.json(result.data);
  } catch (e) {
    return toErrorResponse(e);
  }
}
