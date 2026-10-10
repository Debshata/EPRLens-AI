import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ReviewStateBadge, SeverityBadge } from "@/components/data/status-badges";
import type { Finding, ReviewState } from "@/lib/contracts";
import { formatMass } from "@/lib/formatters";
import { ruleTitle } from "@/lib/rule-catalog";

/** Rule findings and statistical outliers are listed separately (a model score is not a violation). */
export function AnomalyTable({ findings, stateOf }: { findings: Finding[]; stateOf: (f: Finding) => ReviewState }) {
  const rule = findings.filter((f) => f.detected_by.includes("rule"));
  const outlierOnly = findings.filter((f) => !f.detected_by.includes("rule"));
  return (
    <Card variant="standard" className="space-y-5" data-testid="anomaly-table">
      <div>
        <CardTitle>Anomalies and findings</CardTitle>
        <CardDescription>Rule checks are deterministic. Outlier scores come from a statistical model trained on synthetic data and only suggest where to look.</CardDescription>
      </div>
      <section aria-labelledby="rule-h" className="space-y-2">
        <h4 id="rule-h" className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-muted">Rule-based <Badge variant="neutral">{rule.length}</Badge></h4>
        <Table aria-label="Rule-based findings">
          <THead><TR className="hover:bg-transparent"><TH>Finding</TH><TH>Rule</TH><TH className="text-right">Difference</TH><TH>Severity</TH><TH>Review</TH></TR></THead>
          <TBody>
            {rule.map((f) => (
              <TR key={f.finding_id}>
                <TD><Link className="font-medium underline-offset-4 hover:text-brand-bright hover:underline" href={`/app/review?selected=${f.finding_id}`}>{f.title}</Link></TD>
                <TD className="text-xs text-muted">{f.rule_ids.map(ruleTitle).join(", ")}</TD>
                <TD className="num whitespace-nowrap text-right">{f.difference_kg != null ? formatMass(f.difference_kg) : "n/a"}</TD>
                <TD><SeverityBadge severity={f.severity} /></TD>
                <TD><ReviewStateBadge state={stateOf(f)} /></TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </section>
      <section aria-labelledby="ml-h" className="space-y-2">
        <h4 id="ml-h" className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-muted">Statistical outliers only <Badge variant="neutral">{outlierOnly.length}</Badge></h4>
        {outlierOnly.length ? (
          <ul className="space-y-2">
            {outlierOnly.map((f) => (
              <li key={f.finding_id} className="rounded-xl border border-white/10 p-3 text-sm">
                <Link className="font-medium underline-offset-4 hover:text-brand-bright hover:underline" href={`/app/review?selected=${f.finding_id}`}>{f.title}</Link>
                <p className="mt-1 text-xs text-muted">{f.model_score != null ? `Outlier score ${f.model_score.toFixed(3)}` : "Outlier score not computed for this fixture"} — not a probability of non-compliance. Review: <ReviewStateBadge state={stateOf(f)} /></p>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-muted">None.</p>}
      </section>
    </Card>
  );
}
