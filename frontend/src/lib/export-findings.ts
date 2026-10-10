import type { Finding, ReviewState } from "./contracts";

const esc = (v: unknown) => {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

/** CSV of the currently visible findings; original values and the effective review state are both included. */
export function findingsToCsv(findings: Finding[], stateOf: (f: Finding) => ReviewState): string {
  const header = ["finding_id", "title", "severity", "review_state", "invoice_number", "expected_raw", "expected_unit", "expected_kg", "observed_raw", "observed_unit", "observed_kg", "difference_kg", "rule_ids", "rule_version", "legal_determination"];
  const rows = findings.map((f) => [
    f.finding_id, f.title, f.severity, stateOf(f), f.invoice_number, f.expected.raw_value, f.expected.raw_unit, f.expected.value_kg,
    f.observed.raw_value, f.observed.raw_unit, f.observed.value_kg, f.difference_kg, f.rule_ids.join("|"), f.rule_version, "false",
  ]);
  return [header, ...rows].map((r) => r.map(esc).join(",")).join("\n") + "\n";
}

export function downloadText(fileName: string, text: string, mime = "text/csv") {
  const url = URL.createObjectURL(new Blob([text], { type: `${mime};charset=utf-8` }));
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
