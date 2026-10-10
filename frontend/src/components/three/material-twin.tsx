"use client";

import dynamic from "next/dynamic";
import { ArrowDownUp, Box, Layers } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { EvidenceStatusBadge } from "@/components/data/status-badges";
import { MaterialFlow2D } from "./material-flow-2d";
import { hasWebGL, prefersReducedMotion } from "./webgl";
import { formatKg, formatPct, formatTonnes } from "@/lib/formatters";
import { rowsForNode, type MaterialFlow } from "@/lib/material-flow";

const MaterialFlow3D = dynamic(() => import("./material-flow-3d"), { ssr: false, loading: () => <div className="h-[360px] rounded-2xl border border-white/10 bg-black/40 md:h-[440px]" role="status" aria-label="Loading 3D view" /> });

type SortKey = "kg" | "product";

export function MaterialTwin({ flow, fy }: { flow: MaterialFlow; fy: string }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"2d" | "3d">("2d");
  const [webgl, setWebgl] = useState(false);
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "kg", dir: -1 });

  // 3D is progressive enhancement: only auto-enabled with WebGL, no reduced-motion preference and a wide screen.
  useEffect(() => {
    const ok = hasWebGL();
    setWebgl(ok);
    if (ok && !prefersReducedMotion() && window.innerWidth >= 768) setView("3d");
  }, []);

  const rows = useMemo(() => {
    const base = selected ? rowsForNode(flow, selected) : flow.rows;
    return [...base].sort((a, b) => (sort.key === "kg" ? (a.kg - b.kg) * sort.dir : a.product_name.localeCompare(b.product_name) * sort.dir));
  }, [flow, selected, sort]);
  const selNode = flow.nodes.find((n) => n.id === selected) ?? null;
  const toggleSort = (key: SortKey) => setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: key === "kg" ? -1 : 1 }));

  return (
    <Card variant="standard" className="space-y-5" data-testid="material-twin">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>Material flow · {fy}</CardTitle>
          <CardDescription>Company → product → packaging → material. Sizes come from units sold × declared weight per unit — an estimate, shown the same way in the table below.</CardDescription>
        </div>
        <div className="flex items-center gap-2" role="group" aria-label="View mode">
          <Button size="sm" variant={view === "2d" ? "primary" : "outline"} onClick={() => setView("2d")} aria-pressed={view === "2d"}><Layers aria-hidden /> 2D</Button>
          <Button size="sm" variant={view === "3d" ? "primary" : "outline"} onClick={() => setView("3d")} aria-pressed={view === "3d"} disabled={!webgl} title={webgl ? undefined : "3D needs WebGL, which is unavailable here. The 2D view shows the same data."}><Box aria-hidden /> 3D</Button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <EvidenceStatusBadge status="estimated" />
        <Badge variant="neutral">Basis: units sold × g/unit</Badge>
        <span>Not the same measure as “placed on market” above (exports and returns differ) — the two are never added.</span>
      </div>

      {view === "3d" && webgl ? <MaterialFlow3D flow={flow} selected={selected} onSelect={setSelected} /> : <MaterialFlow2D flow={flow} selected={selected} onSelect={setSelected} />}
      <p className="text-xs text-muted">{view === "3d" ? "Drag to rotate slightly; click a node to see its values. " : "Click any item to filter the table. "}No automatic motion.</p>

      <div className="rounded-xl bg-white/[0.04] p-4 text-sm" aria-live="polite" data-testid="twin-detail">
        {selNode ? (
          <>
            <p className="font-medium">{selNode.label} <span className="font-mono text-xs uppercase text-muted">· {selNode.level}</span></p>
            <p className="num mt-1">{formatKg(selNode.kg)} <span className="text-muted">({formatTonnes(selNode.kg)} · {formatPct(selNode.share * 100)} of total)</span></p>
            <Button variant="text" className="mt-1" onClick={() => setSelected(null)}>Clear selection</Button>
          </>
        ) : (
          <p className="num text-muted">Total <span className="text-fg">{formatKg(flow.total_kg)}</span> ({formatTonnes(flow.total_kg)}). Select a node to inspect it.</p>
        )}
      </div>

      <Table aria-label="Material flow values">
        <THead>
          <TR className="hover:bg-transparent">
            <TH><button className="inline-flex items-center gap-1 hover:text-fg" onClick={() => toggleSort("product")}>Product <ArrowDownUp className="size-3" aria-hidden /></button></TH>
            <TH>Packaging</TH><TH>Material</TH><TH className="text-right">g / unit</TH><TH className="text-right">Units</TH>
            <TH className="text-right"><button className="inline-flex items-center gap-1 hover:text-fg" onClick={() => toggleSort("kg")}>kg <ArrowDownUp className="size-3" aria-hidden /></button></TH>
            <TH className="text-right">Share</TH>
          </TR>
        </THead>
        <TBody>
          {rows.map((r) => (
            <TR key={r.component_id}>
              <TD>{r.product_name}</TD><TD>{r.component_name}</TD><TD>{r.material}</TD>
              <TD className="num text-right">{r.weight_per_unit_g}</TD><TD className="num text-right">{r.units.toLocaleString("en-US")}</TD>
              <TD className="num text-right">{formatKg(r.kg)}</TD><TD className="num text-right">{formatPct(r.share * 100)}</TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </Card>
  );
}
