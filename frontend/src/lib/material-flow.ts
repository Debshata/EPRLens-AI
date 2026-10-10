/**
 * Evidence-derived flow: Company → Product → Packaging component → Material.
 * Basis: units sold in the period × declared weight per unit (an ESTIMATE, not measured and not "placed on market").
 * Geometry for the 3D view comes only from these values — no decorative data.
 */
import type { SimulatorFixture } from "./contracts";
import { round6 } from "./units";

export type FlowLevel = "company" | "product" | "component" | "material";

export interface FlowNode {
  id: string;
  level: FlowLevel;
  label: string;
  kg: number;
  share: number; // of company total, 0..1
}

export interface FlowLink {
  from: string;
  to: string;
  kg: number;
}

export interface FlowRow {
  product_id: string;
  product_name: string;
  component_id: string;
  component_name: string;
  material: string;
  weight_per_unit_g: number;
  units: number;
  kg: number;
  share: number;
}

export interface MaterialFlow {
  total_kg: number;
  nodes: FlowNode[];
  links: FlowLink[];
  rows: FlowRow[];
}

export function buildMaterialFlow(sim: SimulatorFixture, companyLabel: string): MaterialFlow {
  const rows: FlowRow[] = [];
  for (const p of sim.products) {
    for (const c of p.components) {
      rows.push({
        product_id: p.product_id,
        product_name: p.product_name,
        component_id: c.component_id,
        component_name: c.component_name,
        material: c.material,
        weight_per_unit_g: c.weight_per_unit_g,
        units: p.units_fy2025_26,
        kg: round6((p.units_fy2025_26 * c.weight_per_unit_g) / 1000),
        share: 0,
      });
    }
  }
  const total = round6(rows.reduce((s, r) => s + r.kg, 0));
  rows.forEach((r) => (r.share = total > 0 ? r.kg / total : 0));

  const nodes: FlowNode[] = [{ id: "company", level: "company", label: companyLabel, kg: total, share: 1 }];
  const links: FlowLink[] = [];
  const add = (id: string, level: FlowLevel, label: string, kg: number) => {
    const existing = nodes.find((n) => n.id === id);
    if (existing) existing.kg = round6(existing.kg + kg);
    else nodes.push({ id, level, label, kg, share: 0 });
  };
  const addLink = (from: string, to: string, kg: number) => {
    const l = links.find((x) => x.from === from && x.to === to);
    if (l) l.kg = round6(l.kg + kg);
    else links.push({ from, to, kg });
  };

  for (const r of rows) {
    add(`product:${r.product_id}`, "product", r.product_name, r.kg);
    add(`component:${r.component_id}`, "component", `${r.component_name} (${r.material})`, r.kg);
    add(`material:${r.material}`, "material", r.material, r.kg);
    addLink("company", `product:${r.product_id}`, r.kg);
    addLink(`product:${r.product_id}`, `component:${r.component_id}`, r.kg);
    addLink(`component:${r.component_id}`, `material:${r.material}`, r.kg);
  }
  nodes.forEach((n) => (n.share = total > 0 ? n.kg / total : 0));
  return { total_kg: total, nodes, links, rows };
}

/** Rows that belong to a node, so the detail panel shows exactly the same values as the table. */
export function rowsForNode(flow: MaterialFlow, nodeId: string): FlowRow[] {
  const [level, key] = nodeId.split(":");
  switch (level) {
    case "company":
      return flow.rows;
    case "product":
      return flow.rows.filter((r) => r.product_id === key);
    case "component":
      return flow.rows.filter((r) => r.component_id === key);
    case "material":
      return flow.rows.filter((r) => r.material === key);
    default:
      return [];
  }
}
