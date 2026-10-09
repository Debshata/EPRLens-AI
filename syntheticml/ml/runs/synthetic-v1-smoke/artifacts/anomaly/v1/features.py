"""Isolation-Forest features for ONE invoice record — pure Python, shared by
training and AWS Lambda (copied into the anomaly artifact as features.py).

A record is plain JSON (see ml/AWS_HANDOFF.md):
  invoice  : header fields as printed / registered
  lines    : invoice lines, each optionally with the linked internal "transaction"
  context  : statistics the backend computes from the company's own history
No label / ground-truth field is ever read here. SYNTHETIC — EPRLens Demo.
"""
import math

INVOICE_TYPES = ["CREDIT_NOTE", "FG_SALES", "IMPORT_COMMERCIAL", "MULTI_MATERIAL", "PKG_COMPONENT", "PKG_PURCHASE",
                 "RECYCLING_SERVICE", "RETURN", "WASTE_PROCUREMENT"]
FEATURES = [
    "log_amount_inr",        # invoice total in INR (log)
    "log_total_kg",          # invoice quantity in kg (log)
    "n_lines",
    "max_qty_log_ratio",     # largest |log(invoice kg / recorded kg)| across lines
    "item_spike",            # largest log(month quantity / item's median monthly quantity)
    "item_mom",              # largest log(month quantity / previous month quantity)
    "issuer_rel_amount",     # log(invoice total / median total for this issuer -> company)
    "issuer_frequency",      # log(1 + invoices from this issuer to this company)
    "rate_rel",              # largest |log(rate per kg / reference rate per kg for supplier+material)|
    "weight_rel",            # largest |log(printed g/unit / master g/unit)|
] + [f"type_{t}" for t in INVOICE_TYPES]
LABEL_LIKE = {"is_anomaly", "anomaly_type", "anomaly_types", "expected_detection", "expected_detection_method",
              "expected_rule_ids", "ground_truth", "bad_value", "original_value", "modified_value", "test_case_type",
              "test_case", "severity", "anomaly_instance_id", "anomaly_instance_ids", "note", "split", "label"}


def _log_ratio(a, b):
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return math.log(a / b)


def _fx(inv):
    return float(inv.get("fx_rate") or 1.0)


def amount_inr(inv):
    return float(inv.get("total") or 0.0) * _fx(inv)


def anomaly_features(record, rate_reference=None):
    """Return dict feature -> float (fixed set, see FEATURES)."""
    inv = record["invoice"]
    lines = record.get("lines") or []
    ctx = record.get("context") or {}
    rate_reference = rate_reference or {}
    fx = _fx(inv)
    total_kg = sum(float(l.get("normalized_quantity_kg") or 0.0) for l in lines)
    qty_ratio, spike, mom, rate_rel, weight_rel = 0.0, 0.0, 0.0, 0.0, 0.0
    for l in lines:
        key = str(l.get("line_no"))
        rec = l.get("recorded_quantity_kg")
        r = _log_ratio(l.get("normalized_quantity_kg"), rec)
        if r is not None:
            qty_ratio = max(qty_ratio, abs(r))
        mq = (ctx.get("item_month_qty") or {}).get(key)
        med = (ctx.get("item_median_qty") or {}).get(key)
        prev = (ctx.get("item_prev_month_qty") or {}).get(key)
        s = _log_ratio(mq, med)
        if s is not None:
            spike = max(spike, s)
        m = _log_ratio(mq, prev)
        if m is not None:
            mom = max(mom, m)
        kg = l.get("normalized_quantity_kg")
        ref = rate_reference.get(f"{inv.get('supplier_id')}|{l.get('material')}")
        if kg and kg > 0 and ref and l.get("taxable_value"):
            rr = _log_ratio(float(l["taxable_value"]) * fx / kg, ref)
            if rr is not None:
                rate_rel = max(rate_rel, abs(rr))
        mw = (l.get("master_component") or {}).get("weight_per_unit_g")
        wr = _log_ratio(l.get("weight_per_unit_g"), mw)
        if wr is not None:
            weight_rel = max(weight_rel, abs(wr))
    issuer_rel = _log_ratio(amount_inr(inv), ctx.get("issuer_company_median_total_inr"))
    f = {
        "log_amount_inr": math.log1p(max(0.0, amount_inr(inv))),
        "log_total_kg": math.log1p(max(0.0, total_kg)),
        "n_lines": float(len(lines)),
        "max_qty_log_ratio": min(qty_ratio, 15.0),
        "item_spike": max(-5.0, min(spike, 10.0)),
        "item_mom": max(-5.0, min(mom, 10.0)),
        "issuer_rel_amount": max(-10.0, min(issuer_rel if issuer_rel is not None else 0.0, 10.0)),
        "issuer_frequency": math.log1p(float(ctx.get("issuer_company_invoice_count") or 0)),
        "rate_rel": min(rate_rel, 10.0),
        "weight_rel": min(weight_rel, 10.0),
    }
    for t in INVOICE_TYPES:
        f[f"type_{t}"] = 1.0 if inv.get("invoice_type") == t else 0.0
    return f


def vector(features):
    return [float(features[n]) for n in FEATURES]


def assert_no_label_fields(names):
    bad = sorted(set(names) & LABEL_LIKE)
    if bad:
        raise ValueError(f"label-like columns must never be model inputs: {bad}")
