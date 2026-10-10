"""Unit normalisation (mirror of frontend/src/lib/units.ts). Everything is compared in kg; originals are always kept."""
from __future__ import annotations

import math

_KG = {"kg", "kgs", "kilogram", "kilograms"}
_G = {"g", "gm", "gms", "gram", "grams"}
_MT = {"mt", "t", "tonne", "tonnes", "ton", "tons", "metric ton", "metric tons"}
_PCS = {"pcs", "pc", "piece", "pieces", "nos", "no", "bottles", "bottle", "btl", "units", "unit", "bags", "bag"}
_SERVICE = {"job", "jobs", "lot", "service"}  # printed units that cannot be converted to kg


def is_unit_token(unit: str) -> bool:
    """True for any printed unit we recognise, including non-mass service units."""
    u = (unit or "").strip().lower().replace(".", "")
    return normalize_unit(unit) is not None or u in _SERVICE


def normalize_unit(unit: str) -> str | None:
    u = (unit or "").strip().lower().replace(".", "")  # "M.T." -> "mt"
    if u in _KG:
        return "kg"
    if u in _G:
        return "g"
    if u in _MT:
        return "mt"
    if u in _PCS:
        return "pcs"
    return None


def round6(x: float) -> float:
    return round(x + 1e-12, 6)


def to_kg(value: float, unit: str, weight_per_unit_g: float | None = None) -> dict:
    """Returns {"ok": True, "kg": float, "rule": str} or {"ok": False, "reason": str, "next_step": str}."""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return {"ok": False, "reason": "The quantity is not a number.", "next_step": "Correct the quantity in the source file and upload it again."}
    if value < 0:
        return {"ok": False, "reason": "The quantity is negative.", "next_step": "Check whether this is a credit note; otherwise correct the sign."}
    u = normalize_unit(unit)
    if u == "kg":
        return {"ok": True, "kg": round6(value), "rule": "KG"}
    if u == "g":
        return {"ok": True, "kg": round6(value / 1000), "rule": "G_TO_KG_1000"}
    if u == "mt":
        return {"ok": True, "kg": round6(value * 1000), "rule": "MT_TO_KG_1000"}
    if u == "pcs":
        if not weight_per_unit_g or weight_per_unit_g <= 0:
            return {
                "ok": False,
                "reason": f'Quantity is in "{unit}" and no per-unit weight is available, so kg cannot be derived.',
                "next_step": "Add the packaging weight (g per unit) for this item, or mark the quantity as unknown.",
            }
        return {"ok": True, "kg": round6(value * weight_per_unit_g / 1000), "rule": "PCS_X_WEIGHT_G_1000"}
    return {"ok": False, "reason": f'Unit "{unit}" is not recognised.', "next_step": "Use kg, g, MT (tonnes) or pieces with a known weight per unit."}


def power_of_ten_ratio(a: float, b: float, tol_pct: float = 1.0) -> float | None:
    """a/b if it is (within tol_pct) an exact power of ten other than 1, else None."""
    if not (a > 0 and b > 0):
        return None
    ratio = a / b
    exp = round(math.log10(ratio))
    if exp == 0:
        return None
    target = 10.0**exp
    return target if abs(ratio - target) / target <= tol_pct / 100 else None
