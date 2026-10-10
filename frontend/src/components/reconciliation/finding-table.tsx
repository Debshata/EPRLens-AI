"use client";

import { ReviewStateBadge, SeverityBadge } from "@/components/data/status-badges";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { Finding, QuantityRef, ReviewState } from "@/lib/contracts";
import { formatMass } from "@/lib/formatters";

function Value({ q }: { q: QuantityRef }) {
  return (
    <>
      {q.value_kg != null ? formatMass(q.value_kg) : `${q.raw_value}${q.raw_unit ? ` ${q.raw_unit}` : ""}`}
      <span className="mt-0.5 block font-sans text-[11px] text-muted">{q.label}</span>
    </>
  );
}

export function FindingTable({ findings, stateOf, onOpen }: { findings: Finding[]; stateOf: (f: Finding) => ReviewState; onOpen: (f: Finding) => void }) {
  return (
    <Table aria-label="Findings">
      <THead>
        <TR className="hover:bg-transparent">
          <TH>Issue</TH><TH className="text-right">Reference value</TH><TH className="text-right">Compared value</TH><TH className="text-right">Difference</TH><TH>Severity</TH><TH>Review</TH>
        </TR>
      </THead>
      <TBody>
        {findings.map((f) => (
          <TR key={f.finding_id} className="cursor-pointer" onClick={() => onOpen(f)}>
            <TD>
              <button type="button" className="text-left font-medium text-fg underline-offset-4 hover:text-brand-bright hover:underline" onClick={(e) => { e.stopPropagation(); onOpen(f); }}>
                {f.title}
              </button>
              <span className="num mt-0.5 block text-xs text-muted">{f.invoice_number ?? f.component} · {f.anomaly_code}</span>
            </TD>
            <TD className="num whitespace-nowrap text-right"><Value q={f.expected} /></TD>
            <TD className="num whitespace-nowrap text-right"><Value q={f.observed} /></TD>
            <TD className="num whitespace-nowrap text-right font-semibold">{f.difference_kg != null ? formatMass(f.difference_kg) : "n/a"}</TD>
            <TD><SeverityBadge severity={f.severity} /></TD>
            <TD><ReviewStateBadge state={stateOf(f)} /></TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}
