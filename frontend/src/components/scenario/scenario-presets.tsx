"use client";

import { Button } from "@/components/ui/button";
import { ScenarioPresetFixture, type SimulatorFixture } from "@/lib/contracts";
import presetsRaw from "@/lib/mocks/scenario.json";
import type { ScenarioForm } from "./scenario-inputs";

const presets = ScenarioPresetFixture.parse(presetsRaw);

/** One-click examples from the synthetic dataset (same SKU, 5 / 15 / 25 % lighter). Hypothetical, like every scenario here. */
export function ScenarioPresets({ catalog, onPick }: { catalog: SimulatorFixture; onPick: (form: ScenarioForm) => void }) {
  const usable = presets.scenarios.filter((s) => catalog.products.some((p) => p.product_id === s.product_id && p.components.some((c) => c.component_id === s.component_id)));
  if (!usable.length) return null;
  return (
    <div>
      <p className="mb-2 font-mono text-xs uppercase tracking-wider text-muted">Examples from the demo dataset</p>
      <div className="flex flex-wrap gap-2">
        {usable.map((s) => {
          const product = catalog.products.find((p) => p.product_id === s.product_id)!;
          const comp = product.components.find((c) => c.component_id === s.component_id)!;
          return (
            <Button
              key={s.scenario_id}
              type="button"
              variant="ghost"
              size="sm"
              className="h-auto whitespace-normal border border-white/10 py-2 text-left normal-case tracking-normal"
              onClick={() => onPick({ product_id: s.product_id, component_id: s.component_id, units: String(s.units), baseline: String(s.baseline_weight_g), proposed: String(s.proposed_weight_g) })}
            >
              {s.reduction_pct}% lighter · {product.product_name} ({comp.component_name.toLowerCase()})
            </Button>
          );
        })}
      </div>
    </div>
  );
}
