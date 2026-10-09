"""Forecast features: fixed order, no identifiers, no look-ahead, train/serve parity."""
import math

import pandas as pd
import pytest

from conftest import DATA, needs_data
from eprlens_ml import forecast_features as ff

HIST = [{"month": f"2025-{m:02d}", "packaging_kg": 100.0 + 5 * m, "units_sold": 1000 + 50 * m, "weight_per_unit_g": 25.0}
        for m in range(1, 13)] + [{"month": "2026-01", "packaging_kg": 170.0, "units_sold": 1700, "weight_per_unit_g": 25.0}]
SEASON = {i: [1.0] * 12 for i in ff.INDUSTRIES}


def test_feature_list_is_fixed_and_has_no_identifiers():
    assert len(ff.FEATURES) == len(set(ff.FEATURES)) == len(ff.NUMERIC_FEATURES) + len(ff.INDUSTRIES)
    assert not [f for f in ff.FEATURES if "company" in f or "product" in f or "_id" in f]
    assert "next_month_packaging_kg" not in ff.FEATURES


def test_features_deterministic_and_finite():
    a, _, origin, target = ff.build_features(HIST, "Beverages", SEASON)
    b, *_ = ff.build_features(HIST, "Beverages", SEASON)
    assert a == b and origin == "2026-01" and target == "2026-02"
    assert all(math.isfinite(v) for v in ff.vector(a))
    assert list(a) == ff.FEATURES


def test_scale_invariance_of_ratio_features():
    big = [dict(h, packaging_kg=h["packaging_kg"] * 1000) for h in HIST]
    a, *_ = ff.build_features(HIST, "Food", SEASON)
    b, *_ = ff.build_features(big, "Food", SEASON)
    for k in ff.NUMERIC_FEATURES:
        if k != "log_packaging_kg":
            assert a[k] == pytest.approx(b[k])


def test_future_months_cannot_leak():
    """Features depend only on history up to the origin month (the last entry)."""
    a, _, origin, _ = ff.build_features(HIST, "Food", SEASON)
    b, _, origin2, _ = ff.build_features(HIST[:-1], "Food", SEASON)
    assert origin2 < origin and a != b


def test_invalid_history_rejected():
    bad_cases = ([], [{"month": "2026-01"}],
                 [{"month": "2026-02", "packaging_kg": 1}, {"month": "2026-01", "packaging_kg": 1}],
                 [{"month": "2026-01", "packaging_kg": 0}])
    for bad in bad_cases:
        with pytest.raises(ff.HistoryError):
            ff.build_features(bad, "Food", SEASON)
    with pytest.raises(ff.HistoryError):
        ff.build_features(HIST, "Mining", SEASON)


@needs_data
def test_parity_with_generated_panel_lags():
    panel = pd.read_csv(DATA / "csv" / "forecast_panel.csv")
    series = {}
    for r in panel.itertuples(index=False):
        series.setdefault(r.product_id, {})[r.month] = {"month": r.month, "packaging_kg": r.packaging_kg,
                                                         "units_sold": r.units_sold, "weight_per_unit_g": r.weight_per_unit_g}
    for r in panel.sample(400, random_state=1).itertuples(index=False):
        s = series[r.product_id]
        hist = [s[m] for m in (ff.month_add(r.month, -k) for k in range(12, -1, -1)) if m in s]
        _, raw, _, target = ff.build_features(hist, r.industry, SEASON, validate=False)
        assert target == r.target_month
        for col in ("lag_1", "lag_12", "rolling_mean_3"):
            v = getattr(r, col)
            if v == v:
                assert raw[col] == pytest.approx(v, rel=1e-9, abs=6e-4), (r.product_id, r.month, col)  # panel stores 3 dp
