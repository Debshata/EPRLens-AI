import { ApiError } from "./contracts";

/** Every error carries a code, a plain message and what the user can do next. */
export class ApiClientError extends Error {
  readonly code: string;
  readonly next_step: string;
  constructor(code: string, message: string, next_step: string) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.next_step = next_step;
  }
}

export function toApiClientError(e: unknown): ApiClientError {
  if (e instanceof ApiClientError) return e;
  const message = e instanceof Error ? e.message : "Something went wrong.";
  return new ApiClientError("unexpected", message, "Try again. If it keeps failing, reload the page; your uploaded files and review actions are kept.");
}

export async function errorFromResponse(res: Response): Promise<ApiClientError> {
  try {
    const parsed = ApiError.safeParse(await res.json());
    if (parsed.success) return new ApiClientError(parsed.data.code, parsed.data.message, parsed.data.next_step);
  } catch {
    /* fall through */
  }
  return new ApiClientError(
    `http_${res.status}`,
    `The server returned an error (${res.status}).`,
    res.status >= 500 ? "Wait a moment and retry. If it persists, switch to mock mode to keep working." : "Check the file or values you sent and try again.",
  );
}
