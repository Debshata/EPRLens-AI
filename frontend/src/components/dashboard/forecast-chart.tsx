"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { ForecastResponse } from "@/lib/contracts";
import { formatKg, formatMonth, formatTonnes } from "@/lib/formatters";
import { TOKENS } from "@/lib/tokens";

interface Point {
  month: string;
  observed?: number;
  forecast?: number;
  projected?: number;
  baseline?: number;
}

export function ForecastChart({ data }: { data: ForecastResponse }) {
  const [showTable, setShowTable] = useState(false);
  const f = data.forecast;

  const points = useMemo<Point[]>(() => {
    const rows: Point[] = data.history.slice(-24).map((h) => ({ month: h.month, observed: h.packaging_kg }));
    // Visual joins only: the dashed lines start at the previous point so the eye can follow them.
    rows[rows.length - 1].forecast = rows[rows.length - 1].observed;
    for (const p of f.points.filter((x) => x.kind === "model")) {
      rows.push({ month: p.month, forecast: p.packaging_kg, baseline: f.baseline.next_month_kg });
    }
    const projected = f.points.filter((x) => x.kind === "projected");
    if (projected.length) {
      const join = rows[rows.length - 1];
      join.projected = join.forecast ?? join.observed;
      for (const p of projected) rows.push({ month: p.month, projected: p.packaging_kg, baseline: f.baseline.next_month_kg });
    }
    return rows;
  }, [data.history, f.points, f.baseline]);

  const firstForecastMonth = f.points[0].month;
  const next = f.points[0];
  const baselineGap = next.packaging_kg - f.baseline.next_month_kg;

  return (
    <Card variant="standard" className="space-y-4" data-testid="forecast-chart">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>Packaging forecast</CardTitle>
          <CardDescription>Packaging mass of units sold, kg per month (estimated: units × declared weight). Solid = observed; dashed = model forecast.</CardDescription>
        </div>
        <div className="flex flex-wrap gap-2"><Badge variant="estimated">Forecast · estimated</Badge><Badge variant="synthetic">Synthetic-only model</Badge></div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-white/[0.04] p-3">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted">Next month ({formatMonth(next.month)})</p>
          <p className="num mt-1 text-xl font-semibold text-brand-bright" data-testid="forecast-next">{formatKg(next.packaging_kg)}</p>
          <p className="num text-xs text-muted">{formatTonnes(next.packaging_kg)}</p>
        </div>
        <div className="rounded-xl bg-white/[0.04] p-3">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted">Last-value baseline</p>
          <p className="num mt-1 text-xl font-semibold">{formatKg(f.baseline.next_month_kg)}</p>
          <p className="num text-xs text-muted">model is {baselineGap >= 0 ? "+" : "−"}{formatKg(Math.abs(baselineGap))} vs baseline</p>
        </div>
        <div className="rounded-xl bg-white/[0.04] p-3">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted">Uncertainty</p>
          <p className="mt-1 text-sm font-medium text-caution">Interval unavailable</p>
          <p className="text-xs text-muted">The model returns a point forecast only.</p>
        </div>
      </div>

      <div className="h-72 w-full" role="img" aria-label={`Line chart of monthly packaging kg. Latest observed ${formatKg(data.history[data.history.length - 1].packaging_kg)}; next-month model forecast ${formatKg(next.packaging_kg)}. A data table is available below.`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={TOKENS.border} strokeDasharray="3 3" />
            <XAxis dataKey="month" tickFormatter={(m: string) => formatMonth(m).replace(" 20", " ’")} stroke={TOKENS.muted} tick={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono)" }} minTickGap={24} />
            <YAxis tickFormatter={(v: number) => `${Math.round(v / 1000)} t`} stroke={TOKENS.muted} tick={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono)" }} width={52} />
            <Tooltip
              contentStyle={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 12, fontSize: 12 }}
              labelFormatter={(m) => formatMonth(String(m))}
              formatter={(v, name) => [`${formatKg(Number(v))} (${formatTonnes(Number(v))})`, String(name)]}
            />
            <ReferenceLine x={firstForecastMonth} stroke={TOKENS.muted} strokeDasharray="2 4" label={{ value: "forecast →", fill: TOKENS.muted, fontSize: 11, position: "insideTopLeft" }} />
            <Line name="Observed" dataKey="observed" stroke={TOKENS.brand} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
            <Line name="Baseline (last value)" dataKey="baseline" stroke={TOKENS.muted} strokeWidth={1.5} strokeDasharray="1 4" dot={{ r: 3 }} isAnimationActive={false} />
            <Line name="Model forecast" dataKey="forecast" stroke={TOKENS.brandBright} strokeWidth={2} strokeDasharray="6 4" dot={{ r: 4, fill: TOKENS.brandBright }} isAnimationActive={false} />
            <Line name="Projected (recursive, not validated)" dataKey="projected" stroke={TOKENS.info} strokeWidth={2} strokeDasharray="2 4" dot={{ r: 3, fill: TOKENS.bg, stroke: TOKENS.info }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted" aria-label="Chart legend">
        <li><span className="mr-1.5 inline-block h-0.5 w-5 bg-brand align-middle" />Observed</li>
        <li><span className="mr-1.5 inline-block w-5 border-t-2 border-dashed border-brand-bright align-middle" />Model forecast (next month)</li>
        <li><span className="mr-1.5 inline-block w-5 border-t-2 border-dotted border-info align-middle" />Projected months (model output fed back; not validated)</li>
        <li><span className="mr-1.5 inline-block w-5 border-t-2 border-dotted border-muted align-middle" />Last-value baseline</li>
      </ul>

      <div className="rounded-xl border border-white/10 p-3 text-xs text-muted">
        <p><span className="text-fg">{f.model_name}</span> · <span className="num">{f.model_version}</span> · target <span className="num">{f.target}</span>. Test MAE <span className="num text-fg">{formatKg(f.metrics_test.mae_kg)}</span> vs last-value <span className="num">{formatKg(f.metrics_test.baseline_last_value_mae_kg)}</span> (per product-month).</p>
        <p className="mt-1">{f.warning} Forecast material demand is not a verified regulatory obligation.</p>
      </div>

      <Button variant="text" onClick={() => setShowTable((s) => !s)} aria-expanded={showTable}>{showTable ? "Hide data table" : "View data table"}</Button>
      {showTable && (
        <Table aria-label="Forecast data">
          <THead><TR className="hover:bg-transparent"><TH>Month</TH><TH>Type</TH><TH className="text-right">kg</TH><TH className="text-right">tonnes</TH></TR></THead>
          <TBody>
            {[...data.history.slice(-12).map((h) => ({ m: h.month, t: "Observed", v: h.packaging_kg })), ...f.points.map((p) => ({ m: p.month, t: p.kind === "model" ? "Model forecast" : "Projected", v: p.packaging_kg }))].map((r) => (
              <TR key={`${r.m}-${r.t}`}><TD className="num">{formatMonth(r.m)}</TD><TD>{r.t}</TD><TD className="num text-right">{formatKg(r.v)}</TD><TD className="num text-right">{formatTonnes(r.v)}</TD></TR>
            ))}
          </TBody>
        </Table>
      )}
    </Card>
  );
}
