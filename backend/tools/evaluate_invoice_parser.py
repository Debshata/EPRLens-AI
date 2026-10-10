"""Evaluate the invoice parser against the 1,000 ground-truth JSON files.

    python backend/tools/evaluate_invoice_parser.py [N]      # N = how many documents (default 1000)

Synthetic PDFs only: this measures layout coverage of the generated templates, not real-world invoice accuracy.
With N = 1000 the counts are written to backend/evaluation/invoice_parser_metrics.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "shared"))

from eprlens_shared.invoice_parse import PARSER_VERSION, extract_text, parse_invoice_text  # noqa: E402

BASE = ROOT / "syntheticml" / "data" / "generated" / "invoices"
METRICS = ROOT / "backend" / "evaluation" / "invoice_parser_metrics.json"


def kg_matches(got: dict, expected: dict) -> bool:
    """kg must match; unknown (None) is correct when the document gives no weight to convert a piece count."""
    if got["normalized_quantity_kg"] is None:
        return bool(expected.get("normalization_requires_master")) or expected["normalized_quantity_kg"] is None
    if expected["normalized_quantity_kg"] is None:
        return False
    return abs(got["normalized_quantity_kg"] - expected["normalized_quantity_kg"]) <= max(0.01, 1e-4 * expected["normalized_quantity_kg"])


def qty_matches(got: dict, expected: dict) -> bool:
    if got["quantity"] is None or expected["quantity"] is None:
        return got["quantity"] is None and expected["quantity"] is None
    return abs(float(got["quantity"]) - float(expected["quantity"])) < 1e-6


def evaluate(limit: int) -> tuple[Counter, dict[str, list]]:
    stats: Counter = Counter()
    failures: dict[str, list] = {}

    def record(name: str, ok: bool, doc: str, template: str) -> None:
        stats[name] += int(ok)
        if not ok:
            failures.setdefault(name, []).append((doc, template))

    for gt_file in sorted((BASE / "json").glob("DOC_*.json"))[:limit]:
        truth = json.loads(gt_file.read_text(encoding="utf-8"))
        expected, doc, template = truth["expected_fields"], truth["document_id"], truth["template_id"]
        raw = (BASE / "pdf" / f"{doc}.pdf").read_bytes()
        try:
            text, pages = extract_text(raw)
            parsed = parse_invoice_text(text, pages, doc, f"{doc}.pdf", hashlib.sha256(raw).hexdigest())
        except Exception as exc:  # noqa: BLE001 - a crash is a result, not a reason to stop
            stats["crashes"] += 1
            failures.setdefault("crashes", []).append((doc, repr(exc)[:80]))
            continue
        stats["documents"] += 1
        record("invoice_number", parsed["invoice_number"] == (expected["invoice_number"] or ""), doc, template)
        record("invoice_date", (parsed["invoice_date"] or None) == (expected.get("invoice_date") or None), doc, template)
        record("vendor", parsed["vendor"]["name"] == (expected.get("vendor") or ""), doc, template)
        record("total", expected.get("invoice_total") is None or parsed["total_amount"] == expected["invoice_total"], doc, template)
        same_count = len(parsed["lines"]) == len(expected["lines"])
        record("line_count", same_count, doc, template)
        if same_count:
            for got, exp in zip(parsed["lines"], expected["lines"], strict=True):
                stats["lines"] += 1
                record("line_quantity", qty_matches(got, exp), doc, template)
                record("line_kg", kg_matches(got, exp), doc, template)
    return stats, failures


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    stats, failures = evaluate(limit)
    docs, lines = stats["documents"], stats["lines"]
    print(f"documents {docs}, crashes {stats['crashes']}, lines {lines}")
    for name in ("invoice_number", "invoice_date", "vendor", "total", "line_count"):
        print(f"  {name:15s} {stats[name]}/{docs}")
    for name in ("line_quantity", "line_kg"):
        print(f"  {name:15s} {stats[name]}/{lines}")
    for name, items in failures.items():
        print(f"  misses in {name}: {len(items)} e.g. {items[:3]}")
    if limit == 1000:
        keys = ("invoice_number", "invoice_date", "vendor", "total", "line_count", "line_quantity", "line_kg")
        payload = {"documents": docs, "lines": lines, "synthetic_only": True, "parser_version": PARSER_VERSION, "crashes": stats["crashes"], **{k: stats[k] for k in keys}}
        METRICS.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
