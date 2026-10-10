import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { ScenarioResult } from "@/lib/contracts";
import { formatKg, formatPct, formatTonnes } from "@/lib/formatters";

export function BeforeAfterSummary({ result }: { result: ScenarioResult }) {
  const pct = result.baseline_kg > 0 ? (result.reduction_kg / result.baseline_kg) * 100 : 0;
  return (
    <Card variant="glass" className="space-y-5" data-testid="before-after">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>Before and after</CardTitle>
        <Badge variant="estimated">Hypothetical</Badge>
      </div>
      <div className="grid items-center gap-3 sm:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-xl bg-white/[0.04] p-4">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted">Baseline</p>
          <p className="num mt-1 text-2xl font-semibold" data-testid="baseline-kg">{formatKg(result.baseline_kg)}</p>
          <p className="num text-sm text-muted">{formatTonnes(result.baseline_kg)}</p>
        </div>
        <ArrowRight className="mx-auto hidden size-5 text-muted sm:block" aria-hidden />
        <div className="rounded-xl border border-brand/40 bg-brand/5 p-4">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted">Scenario</p>
          <p className="num mt-1 text-2xl font-semibold text-brand-bright" data-testid="proposed-kg">{formatKg(result.proposed_kg)}</p>
          <p className="num text-sm text-muted">{formatTonnes(result.proposed_kg)}</p>
        </div>
      </div>
      <div className="rounded-xl border border-white/10 p-4">
        <p className="font-mono text-[11px] uppercase tracking-wider text-muted">{result.reduction_kg < 0 ? "Increase" : "Potential material reduction"}</p>
        <p className="num mt-1 text-3xl font-bold text-brand-bright" data-testid="reduction-kg">{formatKg(Math.abs(result.reduction_kg))}</p>
        <p className="num text-sm text-muted">{formatTonnes(Math.abs(result.reduction_kg))} · {formatPct(Math.abs(pct))} {result.reduction_kg < 0 ? "more" : "less"} material</p>
        {result.reduction_kg === 0 && <p className="mt-2 text-sm text-muted">No change in weight, so no change in projected material.</p>}
      </div>
      <details className="text-sm">
        <summary className="min-h-11 cursor-pointer py-2 text-brand-bright">View calculation</summary>
        <p className="num mt-2 rounded-lg bg-black/40 p-3 text-xs leading-relaxed">{result.formula}</p>
      </details>
      <p className="text-xs text-muted">{result.disclaimer}</p>
    </Card>
  );
}
