"use client";

import { formatKg, formatPct, formatTonnes } from "@/lib/formatters";
import type { FlowLevel, MaterialFlow } from "@/lib/material-flow";
import { MATERIAL_COLORS } from "@/lib/tokens";
import { cn } from "@/lib/utils";

const TITLES: Record<FlowLevel, string> = { company: "Company", product: "Products", component: "Packaging", material: "Materials" };

/** Full 2D equivalent of the 3D view: same nodes, same numbers, keyboard operable. */
export function MaterialFlow2D({ flow, selected, onSelect }: { flow: MaterialFlow; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <div className="grid gap-4 md:grid-cols-4" data-testid="material-flow-2d">
      {(["company", "product", "component", "material"] as const).map((lvl) => (
        <section key={lvl} aria-label={TITLES[lvl]}>
          <h4 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-muted">{TITLES[lvl]}</h4>
          <ul className="space-y-1.5">
            {flow.nodes.filter((n) => n.level === lvl).sort((a, b) => b.kg - a.kg).map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  aria-pressed={selected === n.id}
                  onClick={() => onSelect(n.id)}
                  className={cn("w-full rounded-xl border p-2.5 text-left transition-colors", selected === n.id ? "border-brand bg-brand/10" : "border-white/10 hover:border-white/30")}
                >
                  <span className="block truncate text-sm font-medium">{n.label}</span>
                  <span className="num block text-[11px] text-muted">{formatKg(n.kg)} · {formatTonnes(n.kg)} · {formatPct(n.share * 100)}</span>
                  <span className="mt-1.5 block h-1.5 rounded-full bg-white/10" aria-hidden>
                    <span className="block h-full rounded-full" style={{ width: `${Math.max(2, n.share * 100)}%`, background: (n.level === "material" && MATERIAL_COLORS[n.label]) || "#22c55e" }} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
