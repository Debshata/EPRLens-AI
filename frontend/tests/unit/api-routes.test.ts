// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server/lambda", () => ({ invokeLambda: vi.fn() }));
vi.mock("@/lib/server/presign", async (orig) => ({ ...(await orig<typeof import("@/lib/server/presign")>()), presignPut: vi.fn(async () => "https://example-bucket.s3.amazonaws.com/signed") }));

import { invokeLambda } from "@/lib/server/lambda";
import { LambdaUserError } from "@/lib/server/http";
import { POST as scenarioPOST } from "@/app/api/scenario/route";
import { POST as presignPOST } from "@/app/api/uploads/presign/route";
import { GET as forecastGET } from "@/app/api/forecast/route";
import { GET as dashboardGET } from "@/app/api/dashboard/route";
import { POST as classifyPOST } from "@/app/api/vision/classify/route";
import forecastFixture from "@/lib/mocks/forecast.json";

const ENV = {
  AWS_REGION: "ap-south-1", UPLOADS_BUCKET: "b", LAMBDA_PARSE_INVOICE: "pi", LAMBDA_RECONCILE: "rc", LAMBDA_CLASSIFY_IMAGE: "ci",
  LAMBDA_FORECAST: "fc", LAMBDA_DETECT_ANOMALY: "da", LAMBDA_SCENARIO_ENGINE: "se",
};
const json = (body: unknown) => new Request("http://x/api", { method: "POST", body: JSON.stringify(body), headers: { "content-type": "application/json" } });
const saved = { ...process.env };

describe("/api route handlers", () => {
  beforeEach(() => { vi.mocked(invokeLambda).mockReset(); });
  afterEach(() => { process.env = { ...saved }; });

  it("are disabled in mock mode with a next step", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "mock";
    const res = await scenarioPOST(json({ product_id: "p", component_id: "c", units: 1, baseline_g_per_unit: 2, proposed_g_per_unit: 1 }));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe("mock_mode");
    expect(body.next_step).toMatch(/NEXT_PUBLIC_API_MODE=live/);
  });

  it("report incomplete server config instead of crashing", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "live";
    for (const k of Object.keys(ENV)) delete process.env[k];
    const res = await scenarioPOST(json({ product_id: "p", component_id: "c", units: 1, baseline_g_per_unit: 2, proposed_g_per_unit: 1 }));
    expect(res.status).toBe(503);
    expect((await res.json()).code).toBe("live_not_configured");
  });

  describe("live", () => {
    beforeEach(() => { process.env.NEXT_PUBLIC_API_MODE = "live"; Object.assign(process.env, ENV); });

    it("scenario maps the WP3 Lambda contract into the UI contract", async () => {
      vi.mocked(invokeLambda).mockResolvedValue({ baseline_kg: 2500, proposed_kg: 2000, reduction_kg: 500 });
      const res = await scenarioPOST(json({ product_id: "p", component_id: "c", units: 100000, baseline_g_per_unit: 25, proposed_g_per_unit: 20 }));
      expect(res.status).toBe(200);
      expect(await res.json()).toMatchObject({ baseline_kg: 2500, proposed_kg: 2000, reduction_kg: 500, reduction_pct: 20, hypothetical: true });
      expect(invokeLambda).toHaveBeenCalledWith("se", { action: "what_if", units: 100000, current_g_per_unit: 25, proposed_g_per_unit: 20 }, "ap-south-1");
    });

    it("passes a Lambda's friendly error through with its status and next step", async () => {
      vi.mocked(invokeLambda).mockRejectedValue(new LambdaUserError(404, "invoice_not_found", "That invoice has not been analysed yet.", "Upload the invoice PDF first."));
      const res = await scenarioPOST(json({ product_id: "p", component_id: "c", units: 1, baseline_g_per_unit: 2, proposed_g_per_unit: 1 }));
      expect(res.status).toBe(404);
      expect(await res.json()).toEqual({ code: "invoice_not_found", message: "That invoice has not been analysed yet.", next_step: "Upload the invoice PDF first." });
    });

    it("rejects an invalid request with a next step", async () => {
      const res = await scenarioPOST(json({ units: -1 }));
      expect(res.status).toBe(400);
      expect((await res.json()).next_step).toBeTruthy();
      expect(invokeLambda).not.toHaveBeenCalled();
    });

    it("flags a backend response that breaks the contract", async () => {
      vi.mocked(invokeLambda).mockResolvedValue({ predicted_class: "unicorn" });
      const res = await classifyPOST(json({ company_id: "C", s3_key: "uploads/C/images/a.png" }));
      expect(res.status).toBe(502);
      expect((await res.json()).code).toBe("contract_mismatch");
    });

    it("passes a conforming classify response through unchanged", async () => {
      const out = { predicted_class: "plastic", confidence: 0.94, uncertain: false, model_version: "mobilenetv3-v1" };
      vi.mocked(invokeLambda).mockResolvedValue(out);
      const res = await classifyPOST(json({ company_id: "C", s3_key: "uploads/C/images/a.png" }));
      expect(await res.json()).toEqual(out);
    });

    it("returns a forecast that matches the contract", async () => {
      vi.mocked(invokeLambda).mockResolvedValue(forecastFixture);
      const res = await forecastGET(new Request("http://x/api/forecast?company_id=COMP_0001"));
      expect(res.status).toBe(200);
    });

    it("optional company-data endpoints say they are not available instead of failing obscurely", async () => {
      delete process.env.LAMBDA_COMPANY_DATA;
      const res = await dashboardGET(new Request("http://x/api/dashboard?company_id=COMP_0001"));
      expect(res.status).toBe(503);
      expect(await res.json()).toMatchObject({ code: "not_available" });
      expect(invokeLambda).not.toHaveBeenCalled();
    });

    it("presign refuses files the UI would also refuse, and never returns AWS credentials", async () => {
      const bad = await presignPOST(json({ company_id: "C", kind: "invoice", name: "a.exe", size: 10, mime: "application/x-msdownload", sha256: "a".repeat(64) }));
      expect(bad.status).toBe(400);
      const ok = await presignPOST(json({ company_id: "COMP_0001", kind: "invoice", name: "DOC.pdf", size: 4682, mime: "application/pdf", sha256: "a".repeat(64) }));
      expect(ok.status).toBe(200);
      const body = await ok.json();
      expect(body.s3_key).toMatch(/^uploads\/COMP_0001\/invoices\/[0-9a-f-]+\/DOC\.pdf$/);
      expect(JSON.stringify(body)).not.toMatch(/AWS_SECRET|AWS_ACCESS/);
    });
  });
});
