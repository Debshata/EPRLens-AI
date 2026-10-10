import { describe, expect, it } from "vitest";
import anomaly from "@/lib/mocks/anomaly.json";
import company from "@/lib/mocks/company.json";
import dashboard from "@/lib/mocks/dashboard.json";
import forecast from "@/lib/mocks/forecast.json";
import imageResult from "@/lib/mocks/image-result.json";
import invoice from "@/lib/mocks/invoice.json";
import reconciliation from "@/lib/mocks/reconciliation.json";
import simulator from "@/lib/mocks/simulator.json";
import { AnomalyFixture, CompanyBundle, DashboardSummary, ForecastResponse, ImageResultFixture, InvoiceFixture, ReconciliationResponse, SimulatorFixture } from "@/lib/contracts";

describe("every fixture satisfies its contract", () => {
  it.each([
    ["company", CompanyBundle, company],
    ["image-result", ImageResultFixture, imageResult],
    ["invoice", InvoiceFixture, invoice],
    ["reconciliation", ReconciliationResponse, reconciliation],
    ["anomaly", AnomalyFixture, anomaly],
    ["forecast", ForecastResponse, forecast],
    ["dashboard", DashboardSummary, dashboard],
    ["simulator", SimulatorFixture, simulator],
  ] as const)("%s", (_name, schema, data) => {
    const r = schema.safeParse(data);
    expect(r.success, r.success ? "" : JSON.stringify(r.error.issues.slice(0, 3))).toBe(true);
  });

  it("every fixture is labelled synthetic", () => {
    for (const d of [company, imageResult, invoice, reconciliation, anomaly, forecast, dashboard, simulator]) {
      expect((d as { _meta: { synthetic: boolean; watermark: string } })._meta.synthetic).toBe(true);
      expect((d as { _meta: { watermark: string } })._meta.watermark).toContain("SYNTHETIC");
    }
  });

  it("forecast never fabricates an uncertainty interval", () => {
    expect(ForecastResponse.parse(forecast).forecast.interval).toBeNull();
  });

  it("no finding claims a legal determination", () => {
    ReconciliationResponse.parse(reconciliation).findings.forEach((f) => expect(f.legal_determination).toBe(false));
  });
});
