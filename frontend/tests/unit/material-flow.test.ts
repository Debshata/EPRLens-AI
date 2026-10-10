import { describe, expect, it } from "vitest";
import simulator from "@/lib/mocks/simulator.json";
import dashboard from "@/lib/mocks/dashboard.json";
import { DashboardSummary, SimulatorFixture } from "@/lib/contracts";
import { buildMaterialFlow, rowsForNode } from "@/lib/material-flow";
import { fyMonths, sumFy } from "@/lib/period";

const sim = SimulatorFixture.parse(simulator);
const flow = buildMaterialFlow(sim, "EcoFizz");

describe("material flow", () => {
  it("every level conserves the company total", () => {
    for (const level of ["product", "component", "material"] as const) {
      const sum = flow.nodes.filter((n) => n.level === level).reduce((s, n) => s + n.kg, 0);
      expect(sum).toBeCloseTo(flow.total_kg, 3);
    }
  });
  it("links out of each node equal the node's kg", () => {
    for (const n of flow.nodes.filter((x) => x.level !== "material")) {
      const out = flow.links.filter((l) => l.from === n.id).reduce((s, l) => s + l.kg, 0);
      expect(out).toBeCloseTo(n.kg, 3);
    }
  });
  it("kg = units × g / 1000 per row, e.g. Cola 750 ml PET bottle", () => {
    const r = flow.rows.find((x) => x.component_id === "PKGCOMP_000002")!;
    expect(r.kg).toBeCloseTo((121547 * 25) / 1000, 3);
  });
  it("detail rows for a node sum to that node", () => {
    for (const n of flow.nodes) expect(rowsForNode(flow, n.id).reduce((s, r) => s + r.kg, 0)).toBeCloseTo(n.kg, 3);
  });
  it("matches the repo SCN_000001 baseline for the AquaPure PET bottle (22 g × 39,220,030 units)", () => {
    const r = flow.rows.find((x) => x.component_id === "PKGCOMP_000014")!;
    expect(r.kg).toBeCloseTo(862840.66, 1);
  });
});

describe("financial year helpers", () => {
  it("FY2025-26 = Apr 2025 … Mar 2026", () => expect(fyMonths("FY2025-26")).toEqual({ from: "2025-04", to: "2026-03" }));
  it("sums only that FY", () => {
    const d = DashboardSummary.parse(dashboard);
    const t = sumFy(d.monthly_placed_on_market, "FY2025-26", "total_packaging_kg");
    expect(t).toBeGreaterThan(0);
    expect(t).toBeLessThan(sumFy(d.monthly_placed_on_market, "FY2024-25", "total_packaging_kg") * 3);
    // material mix for the same FY is the same measure: totals must agree
    const mix = Object.values(d.material_mix_fy2025_26_kg).reduce((a, b) => a + b, 0);
    expect(Math.abs(mix - t) / t).toBeLessThan(0.001);
  });
});
