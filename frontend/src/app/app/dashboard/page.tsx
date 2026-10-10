"use client";

import { AlertTriangle, ClipboardCheck, Gauge, Package } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { AnomalyTable } from "@/components/dashboard/anomaly-table";
import { ForecastChart } from "@/components/dashboard/forecast-chart";
import { MaterialMix } from "@/components/dashboard/material-mix";
import { EmptyState, ErrorState, LoadingState } from "@/components/data/data-state";
import { Disclaimer } from "@/components/data/disclaimer";
import { MetricCard } from "@/components/data/metric-card";
import { PageHeader } from "@/components/data/page-header";
import { StatusLegend } from "@/components/data/status-badges";
import { MaterialTwin } from "@/components/three/material-twin";
import { WhyPanel } from "@/components/reconciliation/why-panel";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { useApp } from "@/lib/app-state";
import { ApiClientError, toApiClientError } from "@/lib/errors";
import { formatKg, formatMonth, formatTonnes } from "@/lib/formatters";
import { buildMaterialFlow } from "@/lib/material-flow";
import { sumFy } from "@/lib/period";
import { useAsync } from "@/lib/use-async";

const FY = "FY2025-26";

export default function DashboardPage() {
  const app = useApp();
  const id = app.company!.company.company_id; // AppShell guarantees a company
  const dash = useAsync(() => api.getDashboard(id), [id]);
  const fc = useAsync(() => api.getForecast(id), [id]);
  const sim = useAsync(() => api.getSimulator(id), [id]);

  const findings = app.reconciliation?.findings ?? [];
  const open = findings.filter((f) => ["open", "needs_review"].includes(app.stateOf(f)));
  const needsReview = findings.filter((f) => app.stateOf(f) === "needs_review");
  const topOpen = open.find((f) => f.severity === "high") ?? open[0];

  const flow = useMemo(() => (sim.data ? buildMaterialFlow(sim.data, app.company!.company.company_name) : null), [sim.data, app.company]);

  const noData = [dash.error, fc.error].some((e) => e && toApiClientError(e) instanceof ApiClientError && ["no_data", "no_history"].includes(toApiClientError(e).code));
  if (noData) {
    return (
      <>
        <PageHeader kicker="Dashboard" title="Packaging overview" synthetic={false} />
        <EmptyState title="No evidence uploaded" description="This company has no processed data yet, so no totals or forecast are shown — missing values are never displayed as zero." action={{ label: "Upload evidence", href: "/app/workspace" }} />
      </>
    );
  }

  const placed = dash.data ? sumFy(dash.data.monthly_placed_on_market, FY, "total_packaging_kg") : null;
  const lastMonth = dash.data?.monthly_placed_on_market.at(-1)?.month;
  const next = fc.data?.forecast.points[0];

  return (
    <>
      <PageHeader
        kicker="Dashboard"
        title="Packaging overview"
        description={`${app.company!.company.company_name} · ${FY}${lastMonth ? ` · data to ${formatMonth(lastMonth)}` : ""}`}
        actions={<><Button asChild variant="outline" size="sm"><Link href="/app/workspace">Upload evidence</Link></Button><Button asChild size="sm"><Link href="/app/simulator">Run scenario</Link></Button></>}
      />

      <section aria-label="Key figures" className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Placed on market" icon={<Package className="size-4" aria-hidden />} status={placed != null ? "declared" : "unknown"}
          value={placed != null ? formatTonnes(placed) : "—"} hint={placed != null ? `${formatKg(placed)} · ${FY}` : "Loading…"} />
        <MetricCard label="Open findings" icon={<AlertTriangle className="size-4" aria-hidden />} status={app.reconciliation ? "needs_review" : "unknown"}
          value={app.reconciliation ? String(open.length) : "—"} hint={app.reconciliation ? `of ${findings.length} total` : <Link className="underline" href="/app/workspace">Run reconciliation</Link>} />
        <MetricCard label="Needs review" icon={<ClipboardCheck className="size-4" aria-hidden />} status={app.reconciliation ? "needs_review" : "unknown"}
          value={app.reconciliation ? String(needsReview.length) : "—"} hint={app.reconciliation ? "marked by a reviewer" : "no findings yet"} />
        <MetricCard label={next ? `Forecast ${formatMonth(next.month)}` : "Forecast"} icon={<Gauge className="size-4" aria-hidden />} status={next ? "estimated" : "unknown"}
          value={next ? formatTonnes(next.packaging_kg) : "—"} hint={next ? `${formatKg(next.packaging_kg)} · synthetic-only model` : "Loading…"} />
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        {fc.loading ? <LoadingState label="Loading forecast" rows={4} /> : fc.error ? <ErrorState error={fc.error} title="Forecast unavailable" onRetry={fc.reload} /> : fc.data && <ForecastChart data={fc.data} />}
        {dash.loading ? <LoadingState label="Loading material mix" rows={4} /> : dash.error ? <ErrorState error={dash.error} title="Material mix unavailable" onRetry={dash.reload} /> : dash.data && <MaterialMix mix={dash.data.material_mix_fy2025_26_kg} fy={FY} />}
      </div>

      <div className="mt-6">
        {sim.loading ? <LoadingState label="Loading material flow" rows={4} /> : sim.error ? <ErrorState error={sim.error} title="Material flow unavailable" onRetry={sim.reload} /> : flow && <MaterialTwin flow={flow} fy={FY} />}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        {app.reconciliation ? (
          <AnomalyTable findings={findings} stateOf={app.stateOf} />
        ) : (
          <Card variant="standard" className="space-y-3">
            <CardTitle>Anomalies and findings</CardTitle>
            <CardDescription>No reconciliation has been run yet, so there is nothing to show — no findings is not the same as “all clear”.</CardDescription>
            <Button asChild className="self-start"><Link href="/app/workspace">Go to evidence</Link></Button>
          </Card>
        )}
        {topOpen ? <WhyPanel finding={topOpen} /> : <Card variant="glass"><CardTitle className="text-base">Why?</CardTitle><CardDescription className="mt-2">Select or run findings to see a rule-based explanation here.</CardDescription></Card>}
      </div>

      <div className="mt-8 space-y-3">
        <StatusLegend />
        <Disclaimer>Demo company with synthetic data. Totals are company-recorded estimates for pre-compliance review — not a CPCB filing, and the forecast is not a regulatory obligation.</Disclaimer>
      </div>
    </>
  );
}
