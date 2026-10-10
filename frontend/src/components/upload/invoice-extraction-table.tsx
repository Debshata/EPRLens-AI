import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { EvidenceStatusBadge } from "@/components/data/status-badges";
import type { Invoice } from "@/lib/contracts";
import { formatDate, formatInr, formatKg } from "@/lib/formatters";

export function InvoiceExtractionTable({ invoice }: { invoice: Invoice }) {
  return (
    <Card variant="standard" className="space-y-5" data-testid="invoice-extraction">
      <div>
        <CardTitle>Extracted invoice</CardTitle>
        <CardDescription>
          Read from the digital PDF text. Original value and unit are kept next to the kg-normalised value. Method: <span className="num">{invoice.extraction.method}</span> · parser <span className="num">{invoice.extraction.parser_version}</span>
        </CardDescription>
      </div>
      <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Invoice number", invoice.invoice_number],
          ["Date", formatDate(invoice.invoice_date)],
          ["Vendor", invoice.vendor.name],
          ["Total", invoice.total_amount != null ? formatInr(invoice.total_amount) : "Unknown"],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">{k}</dt>
            <dd className="num mt-0.5 break-words">{v}</dd>
          </div>
        ))}
      </dl>
      <Table aria-label="Extracted invoice lines">
        <THead>
          <TR className="hover:bg-transparent">
            <TH>Source (page:line)</TH><TH>Item</TH><TH className="text-right">Original</TH><TH className="text-right">Normalised</TH><TH>Status</TH>
          </TR>
        </THead>
        <TBody>
          {invoice.lines.map((l) => (
            <TR key={l.line_reference}>
              <TD className="num whitespace-nowrap text-xs text-muted">{l.line_reference}</TD>
              <TD>{l.description}<span className="block text-xs text-muted">{l.material}</span></TD>
              <TD className="num whitespace-nowrap text-right">{l.printed_quantity || l.quantity != null ? `${l.printed_quantity ?? l.quantity} ${l.printed_unit ?? l.unit}` : "Unknown"}</TD>
              <TD className="num whitespace-nowrap text-right">{l.normalized_quantity_kg != null ? formatKg(l.normalized_quantity_kg) : "Unknown"}</TD>
              <TD><EvidenceStatusBadge status={l.normalized_quantity_kg != null ? "document_supported" : "unknown"} /></TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </Card>
  );
}
