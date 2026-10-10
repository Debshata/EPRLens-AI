/**
 * One typed interface for everything the UI needs from a backend. `mock` reads bundled fixtures (no network);
 * `live` calls the /api/* route handlers, which proxy to Lambda server-side. Components only ever import `api`.
 */
import type {
  CompanyBundle,
  CompanyInput,
  CsvSummary,
  DashboardSummary,
  ForecastResponse,
  ImageResult,
  Invoice,
  ReconciliationResponse,
  ScenarioRequest,
  ScenarioResult,
  SimulatorFixture,
} from "./contracts";
import { API_MODE, type ApiMode } from "./config";
import { liveApi } from "./live-adapter";
import { mockApi } from "./mock-adapter";

export interface EprlensApi {
  readonly mode: ApiMode;
  /** Tells the adapter which company the current session works on (used for S3 prefixes and Lambda payloads). */
  setActiveCompany(companyId: string | null): void;
  getDemoCompany(): Promise<CompanyBundle>;
  createCompany(input: CompanyInput): Promise<CompanyBundle>;
  classifyImage(file: File): Promise<ImageResult>;
  analyzeInvoice(file: File): Promise<Invoice>;
  analyzeCsv(file: File): Promise<CsvSummary>;
  reconcile(input: { invoice: Invoice; csv: CsvSummary }): Promise<ReconciliationResponse>;
  getDashboard(companyId: string): Promise<DashboardSummary>;
  getForecast(companyId: string): Promise<ForecastResponse>;
  getSimulator(companyId: string): Promise<SimulatorFixture>;
  runScenario(req: ScenarioRequest): Promise<ScenarioResult>;
}

export const api: EprlensApi = API_MODE === "live" ? liveApi : mockApi;
