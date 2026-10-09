"""Forecast feature engineering — ONE pure-Python implementation used for training
AND for AWS Lambda inference (copied into the forecast artifact as features.py).

Input: a product's monthly history (ascending, last entry = latest known month).
Output: a fixed-order feature vector for predicting the NEXT month's packaging kg.

No pandas / numpy / scikit-learn needed here. SYNTHETIC — EPRLens Demo.
"""
import math

INDUSTRIES = ["Appliances", "Automotive", "Beverages", "Cosmetics", "E-commerce", "FMCG", "Food",
              "Household Products", "Industrial Goods", "Personal Care", "Pharmaceuticals", "Retail", "Electronics"]
INDUSTRIES = sorted(INDUSTRIES)

# Scale-free features (ratios to the latest month) so one model serves tiny and huge products.
NUMERIC_FEATURES = [
    "log_packaging_kg",      # log(1 + latest month kg): product scale
    "r_lag1", "r_lag2", "r_lag3", "r_lag6", "r_lag11", "r_lag12",   # past months / latest month
    "r_rm3", "r_rm6",        # rolling means / latest month
    "seasonal_shift",        # last year: (month t-11) / (month t-12) = how last year moved into the target month
    "season_ratio",          # industry seasonality index: target month / latest month (from TRAIN data only)
    "sales_growth",          # units: latest / previous - 1
    "log_weight_g",          # packaging grams per unit (latest)
    "weight_change",         # weight latest / previous (spec changes)
    "target_month_sin", "target_month_cos",
    "history_months",        # months of history available (0-12)
]
FEATURES = NUMERIC_FEATURES + [f"industry_{i}" for i in INDUSTRIES]
# Raw (scale-dependent) features, used only by the raw Linear Regression variant.
RAW_FEATURES = ["packaging_kg", "lag_1", "lag_2", "lag_3", "lag_6", "lag_12", "rolling_mean_3", "rolling_mean_6",
                "units_sold"]
FILL = {"r_lag1": 1.0, "r_lag2": 1.0, "r_lag3": 1.0, "r_lag6": 1.0, "r_lag11": 1.0, "r_lag12": 1.0, "r_rm3": 1.0,
        "r_rm6": 1.0, "seasonal_shift": 1.0, "season_ratio": 1.0, "sales_growth": 0.0, "weight_change": 1.0}
CLIP = 20.0  # ratio clip so a single bad month cannot dominate


def month_add(month, k):
    y, m = int(month[:4]), int(month[5:7])
    n = y * 12 + (m - 1) + k
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


class HistoryError(ValueError):
    pass


def validate_history(history):
    if not isinstance(history, list) or not history:
        raise HistoryError("history must be a non-empty list")
    prev = None
    for h in history:
        for key in ("month", "packaging_kg"):
            if key not in h:
                raise HistoryError(f"history entry missing '{key}'")
        if not isinstance(h["month"], str) or len(h["month"]) != 7:
            raise HistoryError("month must be 'YYYY-MM'")
        if h["packaging_kg"] is None or float(h["packaging_kg"]) < 0:
            raise HistoryError("packaging_kg must be >= 0")
        if prev and h["month"] <= prev:
            raise HistoryError("history must be strictly ascending by month")
        prev = h["month"]
    if float(history[-1]["packaging_kg"]) <= 0:
        raise HistoryError("latest month packaging_kg must be > 0")


def _ratio(a, b):
    if a is None or b is None or b <= 0:
        return None
    return max(0.0, min(CLIP, a / b))


def build_features(history, industry, season_table, validate=True):
    """Return (features: dict name -> float, raw: dict, origin_month, target_month)."""
    if validate:
        validate_history(history)
    if industry not in INDUSTRIES:
        raise HistoryError(f"unknown industry '{industry}'")
    by = {h["month"]: h for h in history}
    origin = history[-1]["month"]
    target = month_add(origin, 1)
    cur = float(history[-1]["packaging_kg"])

    def kg(k):
        h = by.get(month_add(origin, -k))
        v = None if h is None else float(h["packaging_kg"])
        return v if v and v > 0 else None

    def units(k):
        h = by.get(month_add(origin, -k))
        return None if h is None or h.get("units_sold") in (None, 0) else float(h["units_sold"])

    def weight(k):
        h = by.get(month_add(origin, -k))
        return None if h is None or not h.get("weight_per_unit_g") else float(h["weight_per_unit_g"])

    lags = {k: kg(k) for k in (1, 2, 3, 6, 11, 12)}
    win3 = [kg(k) if k else cur for k in range(3)]
    win6 = [kg(k) if k else cur for k in range(6)]
    rm3 = sum(win3) / 3 if all(v is not None for v in win3) else None
    rm6 = sum(win6) / 6 if all(v is not None for v in win6) else None
    u0, u1 = units(0), units(1)
    w0, w1 = weight(0), weight(1)
    si = season_table.get(industry, [1.0] * 12)
    s_o, s_t = si[int(origin[5:]) - 1], si[int(target[5:]) - 1]
    tm = int(target[5:])
    f = {
        "log_packaging_kg": math.log1p(cur),
        "r_lag1": _ratio(lags[1], cur), "r_lag2": _ratio(lags[2], cur), "r_lag3": _ratio(lags[3], cur),
        "r_lag6": _ratio(lags[6], cur), "r_lag11": _ratio(lags[11], cur), "r_lag12": _ratio(lags[12], cur),
        "r_rm3": _ratio(rm3, cur), "r_rm6": _ratio(rm6, cur),
        "seasonal_shift": _ratio(lags[11], lags[12]),
        "season_ratio": (s_t / s_o) if s_o > 0 else None,
        "sales_growth": (u0 / u1 - 1.0) if (u0 and u1) else None,
        "log_weight_g": math.log1p(w0) if w0 else 0.0,
        "weight_change": _ratio(w0, w1),
        "target_month_sin": math.sin(2 * math.pi * tm / 12.0),
        "target_month_cos": math.cos(2 * math.pi * tm / 12.0),
        "history_months": float(sum(1 for k in range(1, 13) if kg(k) is not None)),
    }
    for k, v in FILL.items():
        if f[k] is None:
            f[k] = v
    for i in INDUSTRIES:
        f[f"industry_{i}"] = 1.0 if i == industry else 0.0
    raw = {"packaging_kg": cur, "lag_1": lags[1], "lag_2": lags[2], "lag_3": lags[3], "lag_6": lags[6],
           "lag_12": lags[12], "rolling_mean_3": rm3, "rolling_mean_6": rm6, "units_sold": u0,
           "lag_11": lags[11]}
    return f, raw, origin, target


def vector(features):
    return [float(features[name]) for name in FEATURES]


def to_kg(pred_log_ratio, current_kg):
    """Model predicts log(next / current); convert back to kg."""
    return float(current_kg) * math.exp(max(-10.0, min(10.0, float(pred_log_ratio))))
