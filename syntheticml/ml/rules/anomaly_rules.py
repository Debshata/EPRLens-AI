"""Layer 1 — deterministic anomaly rules (no ML). Pure Python, Lambda-ready.

Every rule returns {"rule_id", "triggered", "severity", "reason"}.
Rules read only record values, master data and context supplied by the caller —
never ground-truth labels. Rule IDs follow docs/anomaly-catalogue.md.
SYNTHETIC — EPRLens Demo.
"""
import math

RULES_VERSION = "rules-v1"
DEFAULT_CONFIG = {"qty_tolerance_kg": 0.5, "qty_tolerance_rel": 0.005}

# Rule id -> (severity, anomaly types it is designed for)
RULE_CATALOGUE = {
    "DUP_COMPOSITE_KEY": ("high", ["AN05"]),
    "REQUIRED_FIELDS": ("medium", ["AN06"]),
    "QTY_MATCH_TOL": ("medium", ["AN01", "AN02", "AN07", "AN18", "AN19", "AN10"]),
    "QTY_RATIO_POW10": ("high", ["AN01", "AN02"]),
    "UNIT_MISMATCH": ("high", ["AN08"]),
    "RECORD_MISSING": ("medium", ["AN15", "AN16", "AN19"]),
    "MATERIAL_MASTER_MATCH": ("medium", ["AN03"]),
    "CATEGORY_MASTER_MATCH": ("high", ["AN04"]),
    "WEIGHT_MASTER_MATCH": ("medium", ["AN10"]),
    "SUPPLIER_SUPPLIES_ITEM": ("medium", ["AN20"]),
    "SUPPLIER_RECORD_MATCH": ("medium", ["AN20"]),
    "STATUS_CANCELLED_EXCLUDED": ("high", ["AN14"]),
    "CREDIT_NOTE_APPLIED": ("medium", ["AN15"]),
    "RETURN_APPLIED": ("medium", ["AN16"]),
    "ARITHMETIC_TOTALS": ("high", []),
    "NEGATIVE_VALUE": ("high", []),
    "RECYCLED_LE_COLLECTED": ("high", ["AN11"]),
    "COLLECTED_LE_GENERATED": ("medium", ["AN12"]),
    "RECYCLER_REGISTERED": ("high", ["AN13"]),
}
RECORD_REQUIRED_TYPES = {"FG_SALES", "PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL", "IMPORT_COMMERCIAL", "RETURN",
                         "CREDIT_NOTE"}
PURCHASE_TYPES = {"PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL", "IMPORT_COMMERCIAL"}


def _r(rule_id, triggered, reason=""):
    return {"rule_id": rule_id, "triggered": bool(triggered), "severity": RULE_CATALOGUE[rule_id][0],
            "reason": reason if triggered else ""}


def _close(a, b, cfg):
    return abs(a - b) <= max(cfg["qty_tolerance_kg"], cfg["qty_tolerance_rel"] * max(abs(a), abs(b)))


def _pow10(ratio):
    if ratio <= 0:
        return False
    e = math.log10(ratio)
    return abs(e - round(e)) < 0.02 and round(e) != 0


# ============================================================ invoice records
def invoice_rules(record, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    inv = record["invoice"]
    lines = record.get("lines") or []
    master = record.get("master") or {}
    ctx = record.get("context") or {}
    itype = inv.get("invoice_type")
    out = []

    # DUP_COMPOSITE_KEY — an earlier invoice with the same issuer, number, date, recipient and total exists
    earlier = ctx.get("earlier_same_key_invoice_ids") or []
    out.append(_r("DUP_COMPOSITE_KEY", bool(earlier), f"same issuer/number/date/recipient/total as {earlier[:1]}"))

    # REQUIRED_FIELDS
    missing = []
    if not inv.get("invoice_date"):
        missing.append("invoice_date")
    if master.get("issuer_has_gstin") and itype != "IMPORT_COMMERCIAL" and not inv.get("supplier_gstin"):
        missing.append("supplier_gstin")
    for l in lines:
        n = l.get("line_no")
        if itype != "CREDIT_NOTE" and l.get("raw_quantity") is None:
            missing.append(f"line{n}.quantity")
        if itype not in ("CREDIT_NOTE", "RECYCLING_SERVICE") and not l.get("raw_unit"):
            missing.append(f"line{n}.unit")
        if not l.get("hsn_code"):
            missing.append(f"line{n}.hsn_code")
        if l.get("component_id") and not l.get("plastic_category"):
            missing.append(f"line{n}.plastic_category")
    out.append(_r("REQUIRED_FIELDS", missing, "missing " + ", ".join(missing[:5])))

    # Quantity / unit / record checks against the linked internal record
    qty_bad, pow10, unit_bad, rec_missing, sup_mismatch, cancelled_posted = [], [], [], [], [], []
    for l in lines:
        n = l.get("line_no")
        tx = l.get("transaction")
        if tx is None:
            if itype in RECORD_REQUIRED_TYPES and itype not in ("CREDIT_NOTE", "RETURN"):
                rec_missing.append(n)
            continue
        if inv.get("status") == "cancelled" and tx.get("status") == "posted":
            cancelled_posted.append(n)
        if l.get("raw_unit") and tx.get("raw_unit") and l["raw_unit"] != tx["raw_unit"]:
            unit_bad.append(f"line{n}: invoice {l['raw_unit']} vs record {tx['raw_unit']}")
        a, b = l.get("normalized_quantity_kg"), tx.get("normalized_quantity_kg")
        if a is not None and b is not None and not _close(float(a), float(b), cfg):
            qty_bad.append(f"line{n}: invoice {float(a):.3f} kg vs record {float(b):.3f} kg")
            if a and b and _pow10(float(b) / float(a)):
                pow10.append(n)
        if itype in PURCHASE_TYPES and tx.get("supplier_id") and tx["supplier_id"] != inv.get("supplier_id"):
            sup_mismatch.append(n)
    out.append(_r("QTY_MATCH_TOL", qty_bad, "; ".join(qty_bad[:3])))
    out.append(_r("QTY_RATIO_POW10", pow10, f"record differs by a power of ten on lines {pow10}"))
    out.append(_r("UNIT_MISMATCH", unit_bad, "; ".join(unit_bad[:3])))
    out.append(_r("RECORD_MISSING", rec_missing, f"no internal record for lines {rec_missing}"))

    # Master-data checks
    mat_bad, cat_bad, w_bad, sup_bad = [], [], [], []
    sup = master.get("issuer_supplier")
    for l in lines:
        mc = l.get("master_component")
        n = l.get("line_no")
        if mc:
            if l.get("material") and l["material"] != mc["material"]:
                mat_bad.append(f"line{n}: {l['material']} vs master {mc['material']}")
            if l.get("plastic_category") and l["plastic_category"] != mc["synthetic_category"]:
                cat_bad.append(f"line{n}: {l['plastic_category']} vs master {mc['synthetic_category']}")
            if l.get("weight_per_unit_g") and abs(float(l["weight_per_unit_g"]) - float(mc["weight_per_unit_g"])) > 0.05:
                w_bad.append(f"line{n}: {l['weight_per_unit_g']} g vs master {mc['weight_per_unit_g']} g")
        if sup is not None and itype in PURCHASE_TYPES and l.get("material"):
            ok_mat = l["material"] in sup["supported_materials"]
            ok_form = (not mc) or mc.get("component_form") in sup["supported_component_forms"]
            if not (ok_mat and ok_form):
                sup_bad.append(f"line{n}: issuer does not supply {l['material']}")
    out.append(_r("MATERIAL_MASTER_MATCH", mat_bad, "; ".join(mat_bad[:3])))
    out.append(_r("CATEGORY_MASTER_MATCH", cat_bad, "; ".join(cat_bad[:3])))
    out.append(_r("WEIGHT_MASTER_MATCH", w_bad, "; ".join(w_bad[:3])))
    out.append(_r("SUPPLIER_SUPPLIES_ITEM", sup_bad, "; ".join(sup_bad[:3])))
    out.append(_r("SUPPLIER_RECORD_MATCH", sup_mismatch, f"record supplier differs from invoice issuer on lines {sup_mismatch}"))

    # Status / adjustment checks
    out.append(_r("STATUS_CANCELLED_EXCLUDED", cancelled_posted, "cancelled invoice still counted in records"))
    no_tx = all(l.get("transaction") is None for l in lines)
    out.append(_r("CREDIT_NOTE_APPLIED", itype == "CREDIT_NOTE" and no_tx, "credit note not applied in records"))
    out.append(_r("RETURN_APPLIED", itype == "RETURN" and no_tx, "return not applied in records"))

    # Arithmetic and impossible values
    arith = []
    taxable = sum(float(l.get("taxable_value") or 0) for l in lines)
    if abs(taxable - float(inv.get("total_taxable_value") or 0)) > 0.011 * max(1, len(lines)):
        arith.append("sum of lines != taxable total")
    if abs(float(inv.get("total_taxable_value") or 0) + float(inv.get("gst") or 0) - float(inv.get("total") or 0)) > 0.011:
        arith.append("taxable + tax != total")
    out.append(_r("ARITHMETIC_TOTALS", arith, "; ".join(arith)))
    neg = [l.get("line_no") for l in lines if any((l.get(k) is not None and float(l[k]) < 0)
                                                 for k in ("raw_quantity", "normalized_quantity_kg", "taxable_value"))]
    if float(inv.get("total") or 0) < 0:
        neg.append("total")
    out.append(_r("NEGATIVE_VALUE", neg, f"negative values on {neg}"))
    return out


# ============================================================ recycling records
def recycling_rules(record, cfg=None):
    row = record["recycling"]
    master = record.get("master") or {}
    eps = 1e-6
    rec, col, gen = float(row["waste_recycled_kg"]), float(row["waste_collected_kg"]), float(row["waste_generated_kg"])
    return [
        _r("RECYCLED_LE_COLLECTED", rec > col + eps, f"recycled {rec:.1f} kg > collected {col:.1f} kg"),
        _r("COLLECTED_LE_GENERATED", col > gen + eps, f"collected {col:.1f} kg > generated proxy {gen:.1f} kg"),
        _r("RECYCLER_REGISTERED", not master.get("recycler_registered", True),
           f"recycler {row.get('recycler_id')} is not registered in the synthetic registry"),
        _r("NEGATIVE_VALUE", min(rec, col, gen) < 0, "negative quantity"),
    ]


def run_rules(record, cfg=None):
    if record.get("record_type") == "recycling":
        return recycling_rules(record, cfg)
    return invoice_rules(record, cfg)


def triggered(findings):
    return [f for f in findings if f["triggered"]]
