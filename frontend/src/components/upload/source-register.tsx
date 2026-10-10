"use client";
import { Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { UploadedFile } from "@/lib/contracts";
import { formatBytes, shortHash } from "@/lib/formatters";

const STATUS: Record<UploadedFile["status"], { label: string; variant: React.ComponentProps<typeof Badge>["variant"] }> = {
  validated: { label: "Validated", variant: "declared" },
  processing: { label: "Processing…", variant: "neutral" },
  extracted: { label: "Extracted", variant: "confirmed" },
  needs_review: { label: "Needs review", variant: "needs_review" },
  failed: { label: "Failed", variant: "high" },
};

export function SourceRegister({ uploads, onRemove }: { uploads: UploadedFile[]; onRemove: (id: string) => void }) {
  return (
    <Card variant="standard" className="space-y-4">
      <CardTitle>Source register</CardTitle>
      {uploads.length === 0 ? (
        <p className="text-sm text-muted">No files yet. Upload evidence or choose a bundled sample to begin.</p>
      ) : (
        <Table aria-label="Uploaded sources">
          <THead>
            <TR className="hover:bg-transparent"><TH>File</TH><TH>Type</TH><TH>Hash</TH><TH>Status</TH><TH><span className="sr-only">Actions</span></TH></TR>
          </THead>
          <TBody>
            {uploads.map((u) => (
              <TR key={u.id}>
                <TD>
                  <span className="break-all">{u.name}</span>
                  <span className="num block text-xs text-muted">{formatBytes(u.size_bytes)}{u.synthetic_sample ? " · synthetic sample" : ""}</span>
                  {u.duplicate_of && <span className="mt-1 block text-xs text-caution">Duplicate of an earlier upload — results reused, nothing discarded.</span>}
                </TD>
                <TD className="capitalize">{u.kind}</TD>
                <TD className="num text-xs text-muted">{shortHash(u.sha256)}…</TD>
                <TD><Badge variant={STATUS[u.status].variant}>{STATUS[u.status].label}</Badge></TD>
                <TD>
                  <Button variant="ghost" size="icon" aria-label={`Remove ${u.name} from the register`} onClick={() => { if (window.confirm(`Remove “${u.name}” from this workspace? Review history is kept.`)) onRemove(u.id); }}>
                    <Trash2 aria-hidden />
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </Card>
  );
}
