import random

import pytest

from generators import identifiers as ids
from generators.formatting import inr


def test_gstin_check_char_round_trip():
    rng = random.Random(1)
    for _ in range(500):
        body = f"{rng.randrange(1, 38):02d}" + "".join(rng.choice(ids.LETTERS) for _ in range(5)) \
            + f"{rng.randrange(10000):04d}" + rng.choice(ids.LETTERS) + "1Z"
        valid = body + ids.gstin_check_char(body)
        assert ids.gstin_checksum_valid(valid)
        assert ids.gstin_format_ok(valid)


def test_fake_gstin_always_fails_checksum_but_keeps_format():
    rng = random.Random(7)
    for _ in range(2000):
        g = ids.fake_gstin(rng, "07", rng.choice("CF"))
        assert len(g) == 15 and g.startswith("07")
        assert ids.gstin_format_ok(g)
        assert not ids.gstin_checksum_valid(g)


def test_sub_seed_is_stable_and_separated():
    assert ids.sub_seed(1, "a", "x") == ids.sub_seed(1, "a", "x")
    assert ids.sub_seed(1, "a", "x") != ids.sub_seed(1, "b", "x")
    assert ids.sub_seed(1, "a", "x") != ids.sub_seed(2, "a", "x")


def test_id_formats():
    assert ids.make_id("COMP", 1) == "COMP_0001"
    assert ids.make_id("PROD", 1) == "PROD_000001"
    assert ids.make_id("PKGCOMP", 231) == "PKGCOMP_000231"
    assert ids.make_id("TXN", 12345) == "TXN_00012345"
    assert ids.test_id("REC", 1) == "REC_TEST_001"


def test_invoice_number_is_marked_and_short():
    n = ids.invoice_number(ids.invoice_series("EcoFizz Beverages"), ids.fy_code(2025), 123)
    assert n == "SYEC/2526/00123"
    assert len(n) <= 16
    with pytest.raises(ValueError):
        ids.invoice_number("SYXX-TOO-LONG", "2526", 1)


def test_non_routable_contact_and_bank_formats():
    assert ids.fake_phone(4401).startswith("+91-00000-0")
    assert ids.fake_bank_account(12) == "SYN-ACCT-000012"
    assert ids.recycler_registration_number("DL", 2023, 7) == "SYN-PWP-DL-2023-0007"


@pytest.mark.parametrize("value,expected", [
    (0, "0.00"), (999.5, "999.50"), (1000, "1,000.00"), (123456.78, "1,23,456.78"),
    (12345678.9, "1,23,45,678.90"), (-1500, "-1,500.00"),
])
def test_indian_grouping(value, expected):
    assert inr(value) == expected
