/** Live adapter: calls the Next.js /api/* route handlers (which hold AWS credentials server-side). */
import type { EprlensApi } from "./api-client";
import {
  CompanyBundle,
  CsvSummary,
  DashboardSummary,
  ForecastResponse,
  ImageResult,
  Invoice,
  ReconciliationResponse,
  ScenarioResult,
  SimulatorFixture,
} from "./contracts";
import { ApiClientError, errorFromResponse, toApiClientError } from "./errors";
import { sha256Hex } from "./hash";
import { z } from "zod";

async function request<T>(schema: z.ZodType<T>, path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers: { "content-type": "application/json", ...(init?.headers ?? {}) } });
  } catch (e) {
    throw toApiClientError(
      Object.assign(new Error("Could not reach the server."), { cause: e }),
    );
  }
  if (!res.ok) throw await errorFromResponse(res);
  const parsed = schema.safeParse(await res.json());
  if (!parsed.success) {
    throw toApiClientError(new Error(`The server response did not match the expected contract (${path}).`));
  }
  return parsed.data;
}

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

let activeCompany: string | null = null;
/** file name → S3 key of what this session uploaded (the reconcile route needs the CSV's key). */
const uploadedKeys = new Map<string, string>();

function company(): string {
  if (!activeCompany) throw new ApiClientError("no_company", "No company is selected.", "Set up a company (or open the demo company) first.");
  return activeCompany;
}

/** Browser → S3 via a short-lived presigned URL minted by the server; returns the S3 key. */
async function uploadViaPresign(file: File, kind: "csv" | "invoice" | "image"): Promise<string> {
  const sha256 = await sha256Hex(await file.arrayBuffer());
  const presign = await request(
    z.object({ upload_url: z.string(), s3_key: z.string() }),
    "/api/uploads/presign",
    post({ company_id: company(), kind, name: file.name, size: file.size, mime: file.type, sha256 }),
  );
  const put = await fetch(presign.upload_url, { method: "PUT", body: file, headers: { "content-type": file.type } });
  if (!put.ok) throw await errorFromResponse(put);
  uploadedKeys.set(file.name, presign.s3_key);
  return presign.s3_key;
}

export const liveApi: EprlensApi = {
  mode: "live",
  setActiveCompany(id) {
    activeCompany = id;
  },
  getDemoCompany: () => request(CompanyBundle, "/api/company?demo=1"),
  createCompany: (input) => request(CompanyBundle, "/api/company", post(input)),
  async classifyImage(file) {
    return request(ImageResult, "/api/vision/classify", post({ company_id: company(), s3_key: await uploadViaPresign(file, "image") }));
  },
  async analyzeInvoice(file) {
    return request(Invoice, "/api/documents/analyze", post({ company_id: company(), s3_key: await uploadViaPresign(file, "invoice") }));
  },
  async analyzeCsv(file) {
    return request(CsvSummary, "/api/transactions/validate", post({ company_id: company(), s3_key: await uploadViaPresign(file, "csv") }));
  },
  reconcile: ({ invoice, csv }) => {
    const csvKey = uploadedKeys.get(csv.file_name);
    if (!csvKey) throw new ApiClientError("missing_upload", "The CSV is not uploaded in this session.", "Upload the CSV again, then run reconciliation.");
    return request(ReconciliationResponse, "/api/reconcile", post({ company_id: company(), document_id: invoice.document_id, csv_s3_key: csvKey }));
  },
  getDashboard: (companyId) => request(DashboardSummary, `/api/dashboard?company_id=${encodeURIComponent(companyId)}`),
  getForecast: (companyId) => request(ForecastResponse, `/api/forecast?company_id=${encodeURIComponent(companyId)}`),
  getSimulator: (companyId) => request(SimulatorFixture, `/api/simulator?company_id=${encodeURIComponent(companyId)}`),
  runScenario: (req) => request(ScenarioResult, "/api/scenario", post(req)),
};
