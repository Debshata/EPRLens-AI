"use client";

import { useId } from "react";
import { FieldError, Input, Label, Select } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import type { SimulatorFixture } from "@/lib/contracts";
import type { FieldError as FE } from "@/lib/scenario-math";
import { EvidenceStatusBadge } from "@/components/data/status-badges";

export interface ScenarioForm {
  product_id: string;
  component_id: string;
  units: string;
  baseline: string;
  proposed: string;
}

export function ScenarioInputs({
  catalog,
  form,
  onChange,
  errors,
  reductionPct,
  onReduction,
  baselineStatus,
}: {
  catalog: SimulatorFixture;
  form: ScenarioForm;
  onChange: (patch: Partial<ScenarioForm>) => void;
  errors: FE[];
  reductionPct: number;
  onReduction: (pct: number) => void;
  baselineStatus: "declared" | "estimated";
}) {
  const uid = useId();
  const product = catalog.products.find((p) => p.product_id === form.product_id) ?? catalog.products[0];
  const err = (f: FE["field"]) => errors.find((e) => e.field === f);
  const msg = (f: FE["field"]) => { const e = err(f); return e ? <>{e.message} <span className="text-muted">{e.next_step}</span></> : null; };

  return (
    <div className="space-y-5">
      <div>
        <Label htmlFor={`${uid}-product`}>Product (SKU)</Label>
        <Select id={`${uid}-product`} value={form.product_id} onChange={(e) => {
          const p = catalog.products.find((x) => x.product_id === e.target.value)!;
          const c = p.components[0];
          onChange({ product_id: p.product_id, component_id: c.component_id, units: String(p.units_fy2025_26), baseline: String(c.weight_per_unit_g), proposed: String(c.weight_per_unit_g) });
        }}>
          {catalog.products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_name}</option>)}
        </Select>
      </div>
      <div>
        <Label htmlFor={`${uid}-component`}>Packaging component</Label>
        <Select id={`${uid}-component`} value={form.component_id} onChange={(e) => {
          const c = product.components.find((x) => x.component_id === e.target.value)!;
          onChange({ component_id: c.component_id, baseline: String(c.weight_per_unit_g), proposed: String(c.weight_per_unit_g) });
        }}>
          {product.components.map((c) => <option key={c.component_id} value={c.component_id}>{c.component_name} — {c.material} ({c.weight_per_unit_g} g)</option>)}
        </Select>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor={`${uid}-units`}>Units sold in the period</Label>
          <Input id={`${uid}-units`} inputMode="numeric" type="number" min={0} value={form.units} onChange={(e) => onChange({ units: e.target.value })} aria-invalid={!!err("units")} aria-describedby={err("units") ? `${uid}-units-e` : undefined} />
          <FieldError id={`${uid}-units-e`}>{msg("units")}</FieldError>
          <p className="mt-1 text-xs text-muted">Default: FY2025-26 units from the demo records.</p>
        </div>
        <div>
          <div className="flex items-center justify-between"><Label htmlFor={`${uid}-base`}>Current g / unit</Label><EvidenceStatusBadge status={baselineStatus} /></div>
          <Input id={`${uid}-base`} inputMode="decimal" type="number" min={0} step="any" value={form.baseline} onChange={(e) => onChange({ baseline: e.target.value })} aria-invalid={!!err("baseline_g_per_unit")} aria-describedby={err("baseline_g_per_unit") ? `${uid}-base-e` : undefined} />
          <FieldError id={`${uid}-base-e`}>{msg("baseline_g_per_unit")}</FieldError>
        </div>
      </div>
      <div>
        <Label htmlFor={`${uid}-prop`}>Proposed g / unit</Label>
        <Input id={`${uid}-prop`} inputMode="decimal" type="number" min={0} step="any" value={form.proposed} onChange={(e) => onChange({ proposed: e.target.value })} aria-invalid={!!err("proposed_g_per_unit")} aria-describedby={err("proposed_g_per_unit") ? `${uid}-prop-e` : undefined} />
        <FieldError id={`${uid}-prop-e`}>{msg("proposed_g_per_unit")}</FieldError>
      </div>
      <div>
        <div className="flex items-center justify-between">
          <Label htmlFor={`${uid}-slider`}>Weight reduction</Label>
          <span className="num text-sm text-brand-bright" data-testid="reduction-pct">{reductionPct.toFixed(1)}%</span>
        </div>
        <Slider id={`${uid}-slider`} aria-label="Weight reduction percent" min={0} max={50} step={0.5} value={[Math.min(50, Math.max(0, reductionPct))]} onValueChange={([v]) => onReduction(v)} />
        <p className="text-xs text-muted">Slider moves “Proposed g / unit”; range 0–50%.</p>
      </div>
    </div>
  );
}
