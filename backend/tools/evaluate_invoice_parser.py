"""Evaluate the invoice parser against the 1,000 ground-truth JSON files.

    python backend/tools/evaluate_invoice_parser.py [N]

Synthetic PDFs only: this measures layout coverage of the generated templates, not real-world invoice accuracy.
"""
import sys, json, glob, collections, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "shared"))
from eprlens_shared.invoice_parse import extract_text, parse_invoice_text
base = str(ROOT / "syntheticml" / "data" / "generated" / "invoices")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
stats = collections.Counter(); fails = collections.defaultdict(list)
for f in sorted(glob.glob(f"{base}/json/*.json"))[:N]:
    g = json.load(open(f)); e = g["expected_fields"]; d = g["document_id"]
    try:
        raw = open(f"{base}/pdf/{d}.pdf", "rb").read()
        text, pages = extract_text(raw)
        p = parse_invoice_text(text, pages, d, f"{d}.pdf", hashlib.sha256(raw).hexdigest())
    except Exception as ex:
        stats["crash"] += 1; fails["crash"].append((d, repr(ex)[:80])); continue
    tid = g["template_id"]; stats["docs"] += 1
    def chk(name, ok):
        stats[name] += bool(ok)
        if not ok: fails[name].append((d, tid))
    chk("invoice_number", p["invoice_number"] == (e["invoice_number"] or ""))
    chk("invoice_date", (p["invoice_date"] or None) == (e.get("invoice_date") or None))
    chk("vendor", p["vendor"]["name"] == (e.get("vendor") or ""))
    gl, pl = e["lines"], p["lines"]
    chk("line_count", len(gl) == len(pl))
    if len(gl) == len(pl):
        for a, b in zip(gl, pl):
            stats["lines"] += 1
            q_ok = (b["quantity"] is None and a["quantity"] is None) or (b["quantity"] is not None and a["quantity"] is not None and abs(float(b["quantity"]) - float(a["quantity"])) < 1e-6)
            kg_ok = (b["normalized_quantity_kg"] is None and (a.get("normalization_requires_master") or a["normalized_quantity_kg"] is None)) or (b["normalized_quantity_kg"] is not None and a["normalized_quantity_kg"] is not None and abs(b["normalized_quantity_kg"] - a["normalized_quantity_kg"]) <= max(0.01, 1e-4 * a["normalized_quantity_kg"]))
            stats["line_qty"] += q_ok; stats["line_kg"] += bool(kg_ok)
            if not q_ok: fails["line_qty"].append((d, tid, a["quantity"], b["quantity"]))
            if not kg_ok: fails["line_kg"].append((d, tid, a["normalized_quantity_kg"], b["normalized_quantity_kg"], a.get("normalization_requires_master")))
    tot = e.get("invoice_total")
    chk("total", tot is None or (p["total_amount"] is not None and abs(p["total_amount"] - tot) < 0.01))
n = stats["docs"]
import json as _j
(ROOT / "backend" / "evaluation" / "invoice_parser_metrics.json").write_text(_j.dumps({"documents": n, "synthetic_only": True, "parser_version": "pdf-text-v1", "invoice_number": stats["invoice_number"], "invoice_date": stats["invoice_date"], "vendor": stats["vendor"], "line_count": stats["line_count"], "total": stats["total"], "lines": stats["lines"], "line_quantity": stats["line_qty"], "line_kg": stats["line_kg"], "crashes": stats["crash"]}, indent=1) + "\n") if N == 1000 else None
print({k: (v if k in ("docs", "crash") else f"{v}/{(stats['lines'] if k.startswith('line_') and k != 'line_count' or k=='lines' else n)}") for k, v in stats.items()})
for k, v in fails.items():
    print(k, len(v), v[:6], collections.Counter(x[1] for x in v if len(x) > 1 and isinstance(x[1], str)).most_common(6))
