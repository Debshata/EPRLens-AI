import pytest

from eprlens_shared.scenario import ScenarioInputError, compute
from eprlens_shared.units import normalize_unit, power_of_ten_ratio, to_kg


def test_conversions():
    assert to_kg(0.5, "MT") == {"ok": True, "kg": 500.0, "rule": "MT_TO_KG_1000"}
    assert to_kg(2500, "g")["kg"] == 2.5
    assert to_kg(48000, "pcs", 21)["kg"] == 1008
    assert to_kg(5.06, "M.T.")["kg"] == 5060
    assert not to_kg(10, "pcs")["ok"]
    assert not to_kg(-1, "kg")["ok"]
    assert not to_kg(1, "furlong")["ok"]
    assert normalize_unit("Btl") == "pcs" and normalize_unit("Bags") == "pcs" and normalize_unit("KGS") == "kg"


def test_power_of_ten():
    assert power_of_ten_ratio(500000, 500) == 1000
    assert power_of_ten_ratio(500, 500000) == 0.001
    assert power_of_ten_ratio(19183.559, 10391.394) is None


def test_scenario_matches_ux_spec_and_repo_event():
    r = compute(100000, 25, 20)
    assert (r["baseline_kg"], r["proposed_kg"], r["reduction_kg"], r["reduction_pct"]) == (2500, 2000, 500, 20)
    assert compute(100000, 25, 21.25)["reduction_kg"] == 375
    assert compute(1000, 22, 22)["reduction_kg"] == 0


@pytest.mark.parametrize("args", [(-1, 25, 20), (1, 0, 20), (1, 25, "x"), (None, 1, 1)])
def test_scenario_rejects_bad_input(args):
    with pytest.raises(ScenarioInputError) as e:
        compute(*args)
    assert e.value.next_step
