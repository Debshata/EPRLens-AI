"use client";

import { Download, FilterX, Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState } from "@/components/data/data-state";
import { Disclaimer } from "@/components/data/disclaimer";
import { PageHeader } from "@/components/data/page-header";
import { StatusLegend } from "@/components/data/status-badges";
import { EvidenceDrawer } from "@/components/reconciliation/evidence-drawer";
import { FindingTable } from "@/components/reconciliation/finding-table";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { useApp } from "@/lib/app-state";
import type { ReviewState, Severity } from "@/lib/contracts";
import { runFullDemo } from "@/lib/demo-setup";
import { downloadText, findingsToCsv } from "@/lib/export-findings";

function ReviewInner() {
  const app = useApp();
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState<"all" | Severity>("all");
  const [review, setReview] = useState<"open" | "all" | ReviewState>("open");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const autoDemo = useRef(false);

  const findings = useMemo(() => app.reconciliation?.findings ?? [], [app.reconciliation]);
  const selectedId = params.get("selected");
  const selected = findings.find((f) => f.finding_id === selectedId) ?? null;

  async function loadSamples() {
    setLoading(true);
    setError(null);
    try {
      await runFullDemo(app);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  // Deep link from the landing page: /app/review?demo=1 prepares the full sample flow once.
  useEffect(() => {
    if (params.get("demo") === "1" && app.hydrated && !app.reconciliation && !autoDemo.current) {
      autoDemo.current = true;
      void loadSamples();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.hydrated, app.reconciliation, params]);

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return findings.filter((f) => {
      const st = app.stateOf(f);
      if (review === "open" ? st !== "open" && st !== "needs_review" : review !== "all" && st !== review) return false;
      if (severity !== "all" && f.severity !== severity) return false;
      if (needle && !`${f.title} ${f.invoice_number ?? ""} ${f.component ?? ""} ${f.finding_id}`.toLowerCase().includes(needle)) return false;
      return true;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [findings, q, severity, review, app.history]);

  const setSelected = (id: string | null) => {
    const next = new URLSearchParams(params.toString());
    next.delete("demo");
    if (id) next.set("selected", id);
    else next.delete("selected");
    router.replace(`/app/review${next.toString() ? `?${next}` : ""}`, { scroll: false });
  };

  const filtersActive = q !== "" || severity !== "all" || review !== "open";

  return (
    <>
      <PageHeader
        kicker="Findings"
        title="Review & reconciliation"
        description="Each finding compares what a document says with what was recorded. Original values are never overwritten — a correction is added beside them with a reason."
        actions={
          <Button variant="outline" size="sm" disabled={!visible.length} onClick={() => downloadText("eprlens-findings.csv", findingsToCsv(visible, app.stateOf))}>
            <Download aria-hidden /> Export CSV
          </Button>
        }
      />

      {error != null && <div className="mb-6"><ErrorState error={error} title="The sample flow could not finish" onRetry={() => void loadSamples()} /></div>}

      {!app.reconciliation ? (
        <EmptyState
          title="No findings yet"
          description="Findings appear after you upload a transaction CSV and an invoice and run reconciliation. You can also load the bundled synthetic sample to see the full flow."
          action={{ label: loading ? "Loading sample…" : "Load the sample flow", onClick: () => void loadSamples() }}
        />
      ) : (
        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-[1fr_180px_200px_auto]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
              <Input aria-label="Search findings" placeholder="Search invoice, item or id" className="pl-9" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <Select aria-label="Filter by severity" value={severity} onChange={(e) => setSeverity(e.target.value as typeof severity)}>
              <option value="all">All severities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
            </Select>
            <Select aria-label="Filter by review state" value={review} onChange={(e) => setReview(e.target.value as typeof review)}>
              <option value="open">Open + needs review</option><option value="all">All states</option><option value="accepted">Accepted</option><option value="rejected">Rejected</option>
            </Select>
            <Button variant="ghost" onClick={() => { setQ(""); setSeverity("all"); setReview("open"); }} disabled={!filtersActive}>
              <FilterX aria-hidden /> Reset filters
            </Button>
          </div>

          <p className="text-sm text-muted" role="status" aria-live="polite">
            Showing <span className="num text-fg">{visible.length}</span> of <span className="num text-fg">{findings.length}</span> findings
          </p>

          {visible.length ? (
            <FindingTable findings={visible} stateOf={app.stateOf} onOpen={(f) => setSelected(f.finding_id)} />
          ) : (
            <EmptyState title="No findings match these filters" description="Your filters hide every finding. Reset them to see the default open list." action={{ label: "Reset filters", onClick: () => { setQ(""); setSeverity("all"); setReview("open"); } }} />
          )}

          <StatusLegend />
          <Disclaimer>Findings are data-consistency checks. They are not a determination of compliance or non-compliance, and a model score is not a probability of non-compliance.</Disclaimer>
        </div>
      )}

      <EvidenceDrawer finding={selected} history={app.history} onClose={() => setSelected(null)} onReview={app.reviewFinding} />
    </>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={null}>
      <ReviewInner />
    </Suspense>
  );
}
