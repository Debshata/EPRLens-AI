import { describe, expect, it } from "vitest";
import { assessApplicability } from "@/lib/applicability";

describe("assessApplicability", () => {
  it("never concludes compliance and never makes a legal determination", () => {
    const r = assessApplicability({ company_name: "X Ltd", roles: ["producer"], industry: "Beverages", turnover_cr: 180, packaging_types: ["PET bottles"], states_operated: ["Delhi"] });
    expect(r.status).toBe("potentially_applicable");
    expect(r.statement).toMatch(/requires verification/i);
    expect(r.statement).not.toMatch(/compliant/i);
    expect(r.legal_determination).toBe(false);
  });
  it("asks for more information when roles or turnover are unknown", () => {
    const r = assessApplicability({ company_name: "X Ltd", roles: [], roles_unknown: true, industry: "Beverages", turnover_cr: null, turnover_unknown: true });
    expect(r.status).toBe("needs_more_information");
    expect(r.missing.length).toBeGreaterThan(0);
  });
});
