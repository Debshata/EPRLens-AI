"use client";

import { Bookmark, RotateCcw, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/data/data-state";
import { Disclaimer } from "@/components/data/disclaimer";
import { PageHeader } from "@/components/data/page-header";
import { BeforeAfterSummary } from "@/components/scenario/before-after-summary";
import { ScenarioInputs, type ScenarioForm } from "@/components/scenario/scenario-inputs";
import { ScenarioPresets } from "@/components/scenario/scenario-presets";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { useApp } from "@/lib/app-state";
import type { ScenarioResult } from "@/lib/contracts";
import { formatKg } from "@/lib/formatters";
import { reductionPctFromWeights, validateScenarioInput, weightFromReduction } from "@/lib/scenario-math";
import { useAsync } from "@/lib/use-async";

interface Saved { id: string; name: string; form: ScenarioForm; result: ScenarioResult; at: string }
const SAVED_KEY = "eprlens.scenarios.v1";

function loadSaved(): Saved[] {
  try { return JSON.parse(window.localStorage.getItem(SAVED_KEY) ?? "[]") as Saved[]; } catch { return []; }
}
function persist(list: Saved[]) {
  try { window.localStorage.setItem(SAVED_KEY, JSON.stringify(list)); } catch { /* storage unavailable: keep in memory */ }
}

export default function SimulatorPage() {
  const app = useApp();
  const companyId = app.company!.company.company_id;
  const cat = useAsync(() => api.getSimulator(companyId), [companyId]);
  const [form, setForm] = useState<ScenarioForm | null>(null);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);

  useEffect(() => setSaved(loadSaved()), []);

  const defaults = useMemo<ScenarioForm | null>(() => {
    if (!cat.data) return null;
    const d = cat.data.default;
    const p = cat.data.products.find((x) => x.product_id === d.product_id)!;
    const c = p.components.find((x) => x.component_id === d.component_id)!;
    return { product_id: p.product_id, component_id: c.component_id, units: String(p.units_fy2025_26), baseline: String(c.weight_per_unit_g), proposed: String(d.proposed_weight_g) };
  }, [cat.data]);

  useEffect(() => { if (defaults && !form) setForm(defaults); }, [defaults, form]);

  const errors = useMemo(() => (form ? validateScenarioInput({ units: form.units, baseline_g_per_unit: form.baseline, proposed_g_per_unit: form.proposed } as never) : []), [form]);

  useEffect(() => {
    if (!form || errors.length) { setResult(null); return; }
    let alive = true;
    void api.runScenario({ product_id: form.product_id, component_id: form.component_id, units: Number(form.units), baseline_g_per_unit: Number(form.baseline), proposed_g_per_unit: Number(form.proposed) }).then((r) => alive && setResult(r));
    return () => { alive = false; };
  }, [form, errors.length]);

  if (cat.loading || !form) return cat.error ? <ErrorState error={cat.error} onRetry={cat.reload} /> : <LoadingState label="Loading simulator" rows={5} />;
  if (!cat.data) return <EmptyState title="No product data" description="Upload a transaction CSV first so the simulator has products and weights to start from." action={{ label: "Upload evidence", href: "/app/workspace" }} />;

  const baseline = Number(form.baseline);
  const proposed = Number(form.proposed);
  const pct = Number.isFinite(baseline) && Number.isFinite(proposed) && baseline > 0 ? reductionPctFromWeights(baseline, proposed) : 0;
  const product = cat.data.products.find((p) => p.product_id === form.product_id)!;
  const comp = product.components.find((c) => c.component_id === form.component_id)!;
  const edited = Number(form.baseline) !== comp.weight_per_unit_g;

  const patch = (p: Partial<ScenarioForm>) => setForm((f) => ({ ...f!, ...p }));
  const save = () => {
    if (!result) return;
    const entry: Saved = { id: `s${Date.now()}`, name: `${product.product_name} · ${comp.component_name}: ${form.baseline} → ${form.proposed} g`, form, result, at: new Date().toISOString() };
    const next = [entry, ...saved].slice(0, 8);
    setSaved(next);
    persist(next);
  };

  return (
    <>
      <PageHeader kicker="Decisions" title="What-if simulator" description="Test a packaging-weight change against the declared baseline. Everything here is a hypothetical calculation from the values you see." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <Card variant="standard" className="space-y-5">
          <CardTitle>Scenario</CardTitle>
          <ScenarioInputs catalog={cat.data} form={form} onChange={patch} errors={errors} reductionPct={pct} baselineStatus={edited ? "estimated" : "declared"}
            onReduction={(v) => patch({ proposed: String(weightFromReduction(baseline > 0 ? baseline : 0, v)) })} />
          <ScenarioPresets catalog={cat.data} onPick={setForm} />
          <div className="flex flex-wrap gap-3 border-t border-white/10 pt-4">
            <Button variant="outline" size="sm" onClick={() => setForm(defaults)}><RotateCcw aria-hidden /> Reset to baseline</Button>
            <Button size="sm" onClick={save} disabled={!result}><Bookmark aria-hidden /> Save scenario</Button>
          </div>
        </Card>

        <div className="space-y-6">
          {result ? <BeforeAfterSummary result={result} /> : (
            <Card variant="caution" role="status"><p className="text-sm">Fix the highlighted fields to see a result. {errors[0]?.next_step}</p></Card>
          )}
          <Card variant="standard" className="space-y-3">
            <CardTitle className="text-base">Assumptions</CardTitle>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
              <li>Units stay unchanged at <span className="num text-fg">{Number(form.units).toLocaleString("en-US")}</span>.</li>
              <li>The redesigned pack is assumed feasible, safe and recyclable — not checked here.</li>
              <li>Baseline weight is <strong className="text-fg">{edited ? "estimated (edited)" : "declared"}</strong> from the product master; it is not measured.</li>
            </ul>
          </Card>
        </div>
      </div>

      <section className="mt-8" aria-label="Saved scenarios">
        <h2 className="mb-3 font-heading text-xl font-semibold">Saved scenarios</h2>
        {saved.length === 0 ? <p className="text-sm text-muted">None yet. Saved scenarios stay in this browser only.</p> : (
          <ul className="grid gap-3 md:grid-cols-2">
            {saved.map((s) => (
              <li key={s.id}>
                <Card variant="compact" className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{s.name}</p>
                    <p className="num text-xs text-muted">−{formatKg(s.result.reduction_kg)} · {new Date(s.at).toISOString().slice(0, 16).replace("T", " ")} UTC</p>
                    <Button variant="text" onClick={() => setForm(s.form)}>Load</Button>
                  </div>
                  <Button variant="ghost" size="icon" aria-label={`Delete saved scenario ${s.name}`} onClick={() => { const next = saved.filter((x) => x.id !== s.id); setSaved(next); persist(next); }}><Trash2 aria-hidden /></Button>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="mt-6"><Disclaimer>Hypothetical future material, not measured pollution avoided, a verified cost saving, or a change in legal EPR liability.</Disclaimer></div>
    </>
  );
}
