"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { FieldError, Input, Label, Textarea } from "@/components/ui/input";
import type { Finding } from "@/lib/contracts";
import { formatMass } from "@/lib/formatters";
import { validateReviewInput, type ReviewInput } from "@/lib/review-store";

export type DialogMode = "accept_correction" | "reject_suggestion";

export function CorrectionDialog({
  finding,
  mode,
  onClose,
  onSubmit,
}: {
  finding: Finding;
  mode: DialogMode | null;
  onClose: () => void;
  onSubmit: (input: ReviewInput) => void;
}) {
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<{ message: string; next_step: string } | null>(null);

  function submit() {
    if (!mode) return;
    const input: ReviewInput = { kind: mode, reason, proposed_value_kg: mode === "accept_correction" && value.trim() !== "" ? Number(value) : null };
    const v = validateReviewInput(input);
    if (!v.ok) return setError({ message: v.message, next_step: v.next_step });
    setError(null);
    onSubmit(input);
    setValue("");
    setReason("");
  }

  const accept = mode === "accept_correction";
  return (
    <Dialog open={mode !== null} onOpenChange={(o) => { if (!o) { setError(null); onClose(); } }}>
      <DialogContent>
        <DialogTitle className="font-heading text-xl font-semibold">{accept ? "Accept a correction" : "Reject this suggestion"}</DialogTitle>
        <DialogDescription className="mt-2 text-sm text-muted">
          {accept
            ? "Record the value you believe is correct and why. The original recorded value stays visible and unchanged in the audit history."
            : "Record why the recorded value should stand. Nothing is deleted; this decision is added to the history."}
        </DialogDescription>
        <p className="num mt-4 rounded-lg bg-white/[0.04] p-3 text-sm">Original recorded value: {finding.observed.value_kg != null ? formatMass(finding.observed.value_kg) : String(finding.observed.raw_value)}</p>
        <div className="mt-4 space-y-4">
          {accept && (
            <div>
              <Label htmlFor="corr-value">Corrected quantity (kg)</Label>
              <Input id="corr-value" type="number" inputMode="decimal" min={0} step="any" value={value} onChange={(e) => setValue(e.target.value)} placeholder="e.g. 500" aria-describedby={error ? "corr-error" : undefined} />
            </div>
          )}
          <div>
            <Label htmlFor="corr-reason">Reason</Label>
            <Textarea id="corr-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder={accept ? "e.g. Supplier confirmed 0.5 MT by email on 12 Nov" : "e.g. Bulk resin order — 500 MT is correct"} aria-describedby={error ? "corr-error" : undefined} />
          </div>
          {error && (
            <FieldError id="corr-error">
              {error.message} <span className="text-muted">{error.next_step}</span>
            </FieldError>
          )}
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant={accept ? "primary" : "danger"} onClick={submit}>{accept ? "Save correction" : "Reject suggestion"}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
