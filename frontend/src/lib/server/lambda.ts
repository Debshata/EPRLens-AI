import "server-only";
import { InvokeCommand, LambdaClient } from "@aws-sdk/client-lambda";
import { LambdaError, LambdaUserError } from "./http";

let client: LambdaClient | null = null;

/**
 * Invokes a Lambda (RequestResponse) and returns its parsed JSON payload. Accepts both a bare JSON result and an
 * API-style `{ statusCode, body }` envelope (envelope TBD with the AWS engineer — D056).
 */
export async function invokeLambda(functionName: string, payload: unknown, region: string): Promise<unknown> {
  client ??= new LambdaClient({ region });
  const out = await client.send(new InvokeCommand({ FunctionName: functionName, Payload: new TextEncoder().encode(JSON.stringify(payload)) }));
  if (out.FunctionError) throw new LambdaError(`Lambda ${functionName} reported an error (${out.FunctionError}).`);
  const text = out.Payload ? new TextDecoder().decode(out.Payload) : "";
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    throw new LambdaError(`Lambda ${functionName} returned a non-JSON response.`);
  }
  if (parsed && typeof parsed === "object" && "statusCode" in parsed && "body" in parsed) {
    const env = parsed as { statusCode: number; body: unknown };
    const body = typeof env.body === "string" ? JSON.parse(env.body) : env.body;
    if (env.statusCode >= 400) {
      const b = body as { code?: unknown; message?: unknown; next_step?: unknown } | null;
      if (b && typeof b.message === "string" && typeof b.next_step === "string") {
        throw new LambdaUserError(env.statusCode, typeof b.code === "string" ? b.code : "backend_error", b.message, b.next_step);
      }
      throw new LambdaError(`Lambda ${functionName} returned status ${env.statusCode}.`);
    }
    return body;
  }
  return parsed;
}
