/** Mock adapter: bundled fixtures + real client-side logic (CSV parsing, unit normalisation, reconcile, scenario math). */
import type { EprlensApi } from "./api-client";
import {
  CompanyBundle,
  DashboardSummary,
  ForecastResponse,
  ImageResultFixture,
  InvoiceFixture,
  ReconciliationResponse,
  SimulatorFixture,
  type Finding,
} from "./contracts";
import { summarizeTransactionCsv } from "./csv";
import { ApiClientError } from "./errors";
import { computeScenario } from "./scenario-math";
import { DEFAULT_TOLERANCES, RULES_VERSION, reconcileInvoice, type RecordRow } from "./reconcile";
import { assessApplicability } from "./applicability";

import companyRaw from "./mocks/company.json";
import dashboardRaw from "./mocks/dashboard.json";
import forecastRaw from "./mocks/forecast.json";
import imageRaw from "./mocks/image-result.json";
import invoiceRaw from "./mocks/invoice.json";
import reconciliationRaw from "./mocks/reconciliation.json";
import simulatorRaw from "./mocks/simulator.json";

// Parsed once; a malformed fixture fails loudly at first use.
const company = CompanyBundle.parse(companyRaw);
const images = ImageResultFixture.parse(imageRaw);
const invoiceFixture = InvoiceFixture.parse(invoiceRaw);
const reconciliation = ReconciliationResponse.parse(reconciliationRaw);
const forecast = ForecastResponse.parse(forecastRaw);
const dashboard = DashboardSummary.parse(dashboardRaw);
const simulator = SimulatorFixture.parse(simulatorRaw);

/** Small delay so loading states are exercised; mock mode is labelled in the UI and never claims to be live. */
const tick = (ms = 250) => new Promise<void>((r) => setTimeout(r, ms));

const MOCK_HINT = "Mock mode only recognises the bundled sample files. Use a sample file, or switch to live mode (NEXT_PUBLIC_API_MODE=live) to process your own.";

export const mockApi: EprlensApi = {
  mode: "mock",

  setActiveCompany() {
    /* mock mode has a single in-memory fixture company */
  },

  async getDemoCompany() {
    await tick(100);
    return company;
  },

  async createCompany(input) {
    await tick(150);
    const applicability = assessApplicability(input);
    const id = `COMP_LOCAL_${Date.now().toString(36).toUpperCase()}`;
    return CompanyBundle.parse({
      _meta: { ...company._meta, note: "Company created locally in mock mode. It has no uploaded data yet." },
      company: {
        company_id: id,
        company_name: input.company_name,
        industry: input.industry,
        turnover_cr: input.turnover_cr ?? null,
        manufacturer: input.roles.includes("manufacturer"),
        importer: input.roles.includes("importer"),
        brand_owner: input.roles.includes("brand_owner"),
        states_operated: input.states_operated ?? [],
        epr_registered: input.registration_status === "registered" ? true : input.registration_status === "not_registered" ? false : null,
        registration_status: input.registration_status ?? "unknown",
        business_description: input.business_description ?? "",
        synthetic_flag: false,
      },
      roles: {
        producer: input.roles.includes("producer"),
        importer: input.roles.includes("importer"),
        brand_owner: input.roles.includes("brand_owner"),
        manufacturer: input.roles.includes("manufacturer"),
      },
      rules_version: applicability.rules_version,
    });
  },

  async classifyImage(file) {
    await tick();
    const hit = images.results[file.name];
    if (!hit) throw new ApiClientError("mock_unrecognised_image", `“${file.name}” is not one of the bundled sample images.`, MOCK_HINT);
    return hit;
  },

  async analyzeInvoice(file) {
    await tick(400);
    if (file.name !== invoiceFixture.invoice.source.file_name) {
      throw new ApiClientError("mock_unrecognised_invoice", `“${file.name}” is not the bundled sample invoice.`, MOCK_HINT);
    }
    return invoiceFixture.invoice;
  },

  async analyzeCsv(file) {
    await tick(150);
    const text = await file.text();
    return summarizeTransactionCsv(file.name, text);
  },

  async reconcile({ invoice, csv }) {
    await tick(350);
    if (csv.missing_required_columns.length) {
      throw new ApiClientError(
        "csv_missing_columns",
        `The CSV is missing required columns: ${csv.missing_required_columns.join(", ")}.`,
        "Download the CSV template (or the sample), add those columns and upload again.",
      );
    }
    const local = reconcileInvoice(invoice, csv.rows as unknown as RecordRow[], DEFAULT_TOLERANCES);
    // Enrich locally computed findings with the matching server-side finding (model score, wording).
    const enriched: Finding[] = local.map((f) => {
      const server = reconciliation.findings.find((s) => s.invoice_id === f.invoice_id && s.observed.source_ref === f.observed.source_ref);
      return server ?? f;
    });
    const seen = new Set(enriched.map((f) => f.finding_id));
    // Company-wide checks across history (what detect-anomaly returns beyond this one invoice).
    const companyWide = local.length ? reconciliation.findings.filter((f) => !seen.has(f.finding_id) && !enriched.some((e) => e.invoice_id === f.invoice_id)) : [];
    return ReconciliationResponse.parse({
      ...reconciliation,
      rules_version: RULES_VERSION,
      findings: [...enriched, ...companyWide],
    });
  },

  async getDashboard(companyId) {
    await tick(120);
    if (companyId !== company.company.company_id) {
      throw new ApiClientError("no_data", "This company has no processed data yet.", "Upload a transaction CSV and an invoice on the Workspace page first.");
    }
    return dashboard;
  },

  async getForecast(companyId) {
    await tick(150);
    if (companyId !== company.company.company_id) {
      throw new ApiClientError("no_history", "There is no packaging history for this company yet.", "Upload at least 12 months of transaction data to enable a forecast.");
    }
    return forecast;
  },

  async getSimulator() {
    await tick(80);
    return simulator;
  },

  async runScenario(req) {
    return computeScenario(req);
  },
};
