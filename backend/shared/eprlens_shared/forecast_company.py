"""Company-level forecast built from the per-product forecast-v1 model (ml/artifacts/forecast/v1).

Month 1 is the direct model output; later months re-use the model's own output as history ("projected", not validated).
Output matches the frontend `ForecastResponse` contract. No uncertainty interval is returned (the model has none).
"""
from __future__ import annotations

import copy


def _next_month(m: str) -> str:
    y, mo = map(int, m.split("-"))
    mo += 1
    return f"{y + 1:04d}-01" if mo > 12 else f"{y:04d}-{mo:02d}"


def build_forecast(seed: dict, predict_one, horizon: int = 3) -> dict:
    """seed = forecast_history.json; predict_one(request) -> forecast-v1 handler response dict."""
    products = copy.deepcopy(seed["products"])  # {product_id: [{month, packaging_kg, units_sold, weight_per_unit_g}, ...]}
    points, month = [], seed["history"][-1]["month"]
    meta = seed["model"]
    for step in range(1, horizon + 1):
        month = _next_month(month)
        total, per = 0.0, {}
        for pid, hist in products.items():
            out = predict_one({"company_id": seed["company_id"], "product_id": pid, "industry": seed["industry"], "history": hist[-13:]})
            if out.get("status") != "success":
                raise ValueError(f"Forecast model failed for {pid}: {out.get('message', 'unknown error')}")
            if out["target_month"] != month:
                raise ValueError(f"Forecast target month mismatch for {pid}: {out['target_month']} != {month}")
            kg = float(out["forecast_kg"])
            w = hist[-1]["weight_per_unit_g"]
            per[pid] = kg
            total += kg
            hist.append({"month": month, "packaging_kg": kg, "units_sold": round(kg * 1000 / w), "weight_per_unit_g": w})
        points.append({"month": month, "packaging_kg": round(total, 3), "kind": "model" if step == 1 else "projected", "per_product": per})
    return {
        "company_id": seed["company_id"],
        "basis": seed["basis"],
        "history": seed["history"],
        "forecast": {
            "model_version": meta["model_version"],
            "model_name": meta["model_name"],
            "target": meta["target"],
            "interval": None,
            "interval_note": "interval unavailable — the model does not return an honest uncertainty range",
            "synthetic_only": True,
            "warning": meta["warning"],
            "baseline": {"name": "last_value", "next_month_kg": seed["history"][-1]["packaging_kg"]},
            "metrics_test": meta["metrics_test"],
            "points": points,
        },
    }
