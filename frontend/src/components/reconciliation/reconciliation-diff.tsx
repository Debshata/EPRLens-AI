import { ArrowRight, Equal } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Mass } from "@/components/data/metric-card";
import type { Finding, QuantityRef, ReviewAction } from "@/lib/contracts";
import { formatMass } from "@/lib/formatters";
import { cn } from "@/lib/utils";

function Side({ q, tone, testId }: { q: QuantityRef; tone: "doc" | "rec"; testId: string }) {
  return (
    <div data-testid={testId} className={cn("rounded-xl border p-4", tone === "doc" ? "border-brand/30 bg-brand/5" : "border-caution/30 bg-caution/5")}>
      <p className="font-mono text-[11px] uppercase tracking-wider text-muted">{q.label}</p>
      <p className="num mt-2 text-lg font-semibold">
        {q.raw_value}
        {q.raw_unit ? <span className="ml-1 text-muted">{q.raw_unit}</span> : null}
      </p>
      {q.value_kg != null ? (
        <p className="mt-1 text-sm">
          <span className="text-muted">= </span>
          <Mass kg={q.value_kg} />
        </p>
      ) : (
        <p className="mt-1 text-sm text-muted">No kg value (not a quantity)</p>
      )}
      <p className="num mt-2 break-all text-[11px] text-muted">{q.source_ref}</p>
    </div>
  );
}

/**
 * Side-by-side original values. The recorded (observed) value is never replaced — a reviewer's proposal is
 * shown next to it, not over it.
 */
export function ReconciliationDiff({ finding, accepted }: { finding: Finding; accepted?: ReviewAction | null }) {
  return (
    <Card variant="compact" className="space-y-4">
      <div className="grid items-center gap-3 sm:grid-cols-[1fr_auto_1fr]">
        <Side q={finding.expected} tone="doc" testId="diff-expected" />
        <div className="hidden justify-center text-muted sm:flex" aria-hidden>{finding.difference_kg === 0 ? <Equal className="size-5" /> : <ArrowRight className="size-5" />}</div>
        <Side q={finding.observed} tone="rec" testId="diff-observed" />
      </div>
      {finding.difference_kg != null && (
        <p className="flex flex-wrap items-baseline gap-x-2 rounded-lg bg-white/[0.04] px-3 py-2 text-sm" data-testid="diff-difference">
          <span className="text-muted">Difference</span>
          <span className="num text-base font-semibold text-danger">{formatMass(finding.difference_kg)}</span>
        </p>
      )}
      {accepted && (
        <div className="rounded-lg border border-brand/40 bg-brand/5 p-3 text-sm" data-testid="diff-accepted">
          <p className="font-medium text-brand-bright">Reviewer-proposed correction (original kept above)</p>
          <p className="num mt-1">{accepted.proposed_value_kg != null ? formatMass(accepted.proposed_value_kg) : "—"}</p>
          <p className="mt-1 text-muted">Reason: {accepted.reason}</p>
          <p className="mt-2 text-xs text-muted">A correction here does not change physical waste or any government filing.</p>
        </div>
      )}
    </Card>
  );
}
