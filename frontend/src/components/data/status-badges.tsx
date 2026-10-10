import { AlertTriangle, CheckCircle2, CircleDashed, CircleHelp, FileCheck2, Pencil, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { EvidenceStatus, ReviewState, Severity } from "@/lib/contracts";

const EVIDENCE: Record<EvidenceStatus, { label: string; variant: React.ComponentProps<typeof Badge>["variant"]; icon: React.ReactNode; hint: string }> = {
  document_supported: { label: "Confirmed", variant: "confirmed", icon: <FileCheck2 className="size-3" aria-hidden />, hint: "Supported by a source document." },
  declared: { label: "Declared", variant: "declared", icon: <Pencil className="size-3" aria-hidden />, hint: "Entered by the user; no document supports it yet." },
  estimated: { label: "Estimated", variant: "estimated", icon: <CircleDashed className="size-3" aria-hidden />, hint: "Calculated or assumed — not measured." },
  needs_review: { label: "Needs review", variant: "needs_review", icon: <AlertTriangle className="size-3" aria-hidden />, hint: "Low confidence or conflicting — a person must check." },
  unknown: { label: "Unknown", variant: "unknown", icon: <CircleHelp className="size-3" aria-hidden />, hint: "No data. Never shown as zero." },
  reviewed: { label: "Reviewed", variant: "reviewed", icon: <ShieldCheck className="size-3" aria-hidden />, hint: "A reviewer has checked and recorded a decision." },
};

export function EvidenceStatusBadge({ status }: { status: EvidenceStatus }) {
  const s = EVIDENCE[status];
  return (
    <Badge variant={s.variant} title={s.hint}>
      {s.icon}
      {s.label}
    </Badge>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge variant={severity}>
      {severity === "high" && <AlertTriangle className="size-3" aria-hidden />}
      {severity} severity
    </Badge>
  );
}

const REVIEW: Record<ReviewState, { label: string; variant: React.ComponentProps<typeof Badge>["variant"] }> = {
  open: { label: "Open", variant: "needs_review" },
  needs_review: { label: "Needs review", variant: "needs_review" },
  accepted: { label: "Correction accepted", variant: "reviewed" },
  rejected: { label: "Suggestion rejected", variant: "reviewed" },
};

export function ReviewStateBadge({ state }: { state: ReviewState }) {
  const s = REVIEW[state];
  return (
    <Badge variant={s.variant}>
      {state === "accepted" || state === "rejected" ? <CheckCircle2 className="size-3" aria-hidden /> : null}
      {s.label}
    </Badge>
  );
}

export function StatusLegend() {
  const items: EvidenceStatus[] = ["document_supported", "declared", "estimated", "needs_review", "unknown", "reviewed"];
  return (
    <ul className="flex flex-wrap items-center gap-2" aria-label="Status legend">
      {items.map((s) => (
        <li key={s}>
          <EvidenceStatusBadge status={s} />
        </li>
      ))}
    </ul>
  );
}
