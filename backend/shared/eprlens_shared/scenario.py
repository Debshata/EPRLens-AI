"""Deterministic what-if (mirror of frontend/src/lib/scenario-math.ts). kg = units x grams per unit / 1000."""
from __future__ import annotations

from .units import round6

FORMULA = "kg = units × grams per unit ÷ 1000; scenario weight = baseline weight × (1 − reduction % ÷ 100)"
DISCLAIMER = (
    "Hypothetical: assumes unchanged sales and a feasible, safe redesign. Not measured waste reduction, "
    "verified cost saving or a change in legal EPR liability."
)


class ScenarioInputError(ValueError):
    def __init__(self, field: str, message: str, next_step: str):
        super().__init__(message)
        self.field, self.next_step = field, next_step


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def compute(units, current_g_per_unit, proposed_g_per_unit) -> dict:
    u, b, p = _num(units), _num(current_g_per_unit), _num(proposed_g_per_unit)
    if u is None or u < 0:
        raise ScenarioInputError("units", "Units must be zero or more.", "Enter the number of units sold in the period (for example 100000).")
    if b is None or b <= 0:
        raise ScenarioInputError("current_g_per_unit", "Current weight must be greater than 0 g.", "Use the declared packaging weight, or enter an estimate.")
    if p is None or p <= 0:
        raise ScenarioInputError("proposed_g_per_unit", "Proposed weight must be greater than 0 g.", "Enter the target grams per unit.")
    baseline = round6(u * b / 1000)
    proposed = round6(u * p / 1000)
    return {
        "baseline_kg": baseline,
        "proposed_kg": proposed,
        "reduction_kg": round6(baseline - proposed),
        "reduction_pct": round6((b - p) / b * 100),
        "formula": FORMULA,
        "hypothetical": True,
        "disclaimer": DISCLAIMER,
    }
