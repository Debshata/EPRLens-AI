import "server-only";
import { NextResponse } from "next/server";
import type { ApiError } from "../contracts";
import { MissingConfigError } from "./env";

export function apiError(status: number, code: string, message: string, next_step: string) {
  const body: ApiError = { code, message, next_step };
  return NextResponse.json(body, { status });
}

/** Maps any thrown value to the standard envelope, without leaking internals or secrets. */
export function toErrorResponse(e: unknown) {
  if (e instanceof MissingConfigError) {
    return apiError(503, "live_not_configured", e.message, "Set the missing variables in frontend/.env.local (see .env.example), or switch to mock mode with NEXT_PUBLIC_API_MODE=mock.");
  }
  if (e instanceof NotAvailableError) {
    return apiError(503, "not_available", `${e.feature} is not configured on the backend yet.`, "Set LAMBDA_COMPANY_DATA once the backend exposes it (see docs/frontend-api-contracts.md), or use mock mode.");
  }
  if (e instanceof LambdaError) return apiError(502, "backend_error", e.message, "Retry in a moment. If it persists, check the Lambda logs or switch to mock mode to keep working.");
  return apiError(500, "unexpected", "The server could not complete the request.", "Try again. If it keeps failing, switch to mock mode and report the time of the failure.");
}

export class LambdaError extends Error {}

export class NotAvailableError extends Error {
  readonly feature: string;
  constructor(feature: string) {
    super(feature);
    this.feature = feature;
  }
}

export function liveGuard() {
  if (process.env.NEXT_PUBLIC_API_MODE !== "live") {
    return apiError(503, "mock_mode", "The live API is disabled because the app is running in mock mode.", "Set NEXT_PUBLIC_API_MODE=live (and the server variables in .env.example) to use the backend.");
  }
  return null;
}
