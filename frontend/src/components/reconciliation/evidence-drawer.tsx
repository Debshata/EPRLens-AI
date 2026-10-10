"use client";

import { Check, FileText, Flag, X } from "lucide-react";
import { useState } from "react";
import { ReviewStateBadge, SeverityBadge } from "@/components/data/status-badges";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { CorrectionDialog, type DialogMode } from "./correction-dialog";
import { ReconciliationDiff } from "./reconciliation-diff";
import { WhyPanel } from "./why-panel";
import type { Finding, ReviewAction } from "@/lib/contracts";
import { formatMass } from "@/lib/formatters";
import type { ReviewInput } from "@/lib/review-store";
import { stateAfter } from "@/lib/review-store";

const KIND_LABEL: Record<ReviewAction["kind"], string> = {
  accept_correction: "Accepted a correction",
  reject_suggestion: "Rejected the suggestion",
  mark_needs_review: "Marked as needs review",
  reopen: "Reopened",
};

export function EvidenceDrawer({
  finding,
  history,
  onClose,
  onReview,
}: {
  finding: Finding | null;
  history: ReviewAction[];
  onClose: () => void;
  onReview: (finding: Finding, input: ReviewInput) => void;
}) {
  const [mode, setMode] = useState<DialogMode | null>(null);
  const mine = finding ? history.filter((a) => a.finding_id === finding.finding_id) : [];
  const last = mine[mine.length - 1];
  const state = last ? stateAfter(last.kind) : finding?.review_state ?? "open";
  const accepted = [...mine].reverse().find((a) => a.kind === "accept_correction");
  const acceptedActive = last?.kind === "accept_correction" ? last : null;

  return (
    <>
      <Dialog open={!!finding} onOpenChange={(o) => !o && onClose()}>
        <DialogContent side="right" aria-describedby="drawer-desc" className="space-y-5">
          {finding && (
            <>
              <div className="pr-10">
                <div className="flex flex-wrap items-center gap-2"><SeverityBadge severity={finding.severity} /><ReviewStateBadge state={state} /></div>
                <DialogTitle className="mt-3 font-heading text-xl font-semibold leading-snug">{finding.title}</DialogTitle>
                <DialogDescription id="drawer-desc" className="num mt-1 text-xs text-muted">
                  {finding.invoice_number ? `Invoice ${finding.invoice_number}` : finding.component} · {finding.finding_id}
                </DialogDescription>
              </div>

              <ReconciliationDiff finding={finding} accepted={acceptedActive ?? (state === "accepted" ? accepted : null)} />
              <WhyPanel finding={finding} />

              <section aria-label="Evidence sources" className="space-y-2 text-sm">
                <h3 className="font-mono text-[11px] uppercase tracking-wider text-muted">Evidence</h3>
                <ul className="space-y-1.5">
                  <li className="flex items-center gap-2"><FileText className="size-4 text-brand-bright" aria-hidden />
                    {finding.document_id ? (
                      <a className="num text-brand-bright underline-offset-4 hover:underline" href={`/samples/${finding.document_id}.pdf`} target="_blank" rel="noreferrer">{finding.document_id}.pdf (open PDF)</a>
                    ) : (
                      <span className="text-muted">Source document not available in this demo — shown as unavailable rather than invented.</span>
                    )}
                  </li>
                  <li className="num text-xs text-muted">Reference: {finding.expected.source_ref} ↔ {finding.observed.source_ref}</li>
                </ul>
              </section>

              <section aria-label="Review actions" className="space-y-3">
                <h3 className="font-mono text-[11px] uppercase tracking-wider text-muted">Review</h3>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => setMode("accept_correction")}><Check aria-hidden /> Accept correction</Button>
                  <Button size="sm" variant="outline" onClick={() => setMode("reject_suggestion")}><X aria-hidden /> Reject suggestion</Button>
                  <Button size="sm" variant="ghost" onClick={() => onReview(finding, { kind: "mark_needs_review", reason: "" })}><Flag aria-hidden /> Mark needs review</Button>
                  {state !== "open" && <Button size="sm" variant="text" onClick={() => onReview(finding, { kind: "reopen", reason: "" })}>Reopen</Button>}
                </div>
                <ol className="space-y-2 border-l border-white/10 pl-4 text-sm" aria-label="Audit history" data-testid="audit-history">
                  <li className="text-muted">Detected — original recorded value <span className="num text-fg">{finding.observed.value_kg != null ? formatMass(finding.observed.value_kg) : String(finding.observed.raw_value)}</span></li>
                  {mine.map((a) => (
                    <li key={a.action_id}>
                      <span className="font-medium">{KIND_LABEL[a.kind]}</span>
                      <span className="num block text-xs text-muted">{a.timestamp.replace("T", " ").slice(0, 16)} UTC · {a.actor}</span>
                      {a.reason && <span className="block text-muted">“{a.reason}”</span>}
                      {a.proposed_value_kg != null && <span className="num block text-xs">Proposed: {formatMass(a.proposed_value_kg)} · original kept: {a.original_value_kg != null ? formatMass(a.original_value_kg) : "—"}</span>}
                    </li>
                  ))}
                </ol>
              </section>
              <p className="text-xs text-muted">A correction does not mean physical waste was reduced, and it does not change any government report. This is pre-compliance review, not certification.</p>
            </>
          )}
        </DialogContent>
      </Dialog>
      {finding && (
        <CorrectionDialog
          finding={finding}
          mode={mode}
          onClose={() => setMode(null)}
          onSubmit={(input) => {
            onReview(finding, input);
            setMode(null);
          }}
        />
      )}
    </>
  );
}
