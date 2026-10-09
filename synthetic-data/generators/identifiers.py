"""Deterministic, clearly synthetic identifiers. SYNTHETIC — EPRLens Demo.

Rules: docs/dummy-identifier-rules.md. Nothing here is intended to match a real
registered entity. GSTIN-like values always carry a deliberately WRONG check
character, so they can never be a valid GSTIN (DS-16 A).
"""
import hashlib
import random
import re

CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_FORMAT_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

ID_WIDTHS = {
    "COMP": 4, "SUP": 4, "BUY": 4, "REC": 4, "USR": 4, "DESC": 4,
    "PROD": 6, "PKGCOMP": 6, "ADDR": 6, "REL": 6, "DOC": 6, "SCN": 6,
    "RCY": 7, "ANM": 7, "TXN": 8, "INV": 8, "INVL": 9, "MEV": 9,
}


# ----------------------------------------------------------------- seeding
def sub_seed(master_seed: int, stage: str, key: str = "") -> int:
    """Stable per-stage/per-entity seed (never uses Python's salted hash())."""
    digest = hashlib.sha256(f"{master_seed}:{stage}:{key}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def stream(master_seed: int, stage: str, key: str = "") -> random.Random:
    return random.Random(sub_seed(master_seed, stage, key))


# ----------------------------------------------------------------- entity ids
def make_id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:0{ID_WIDTHS[prefix]}d}"


def test_id(prefix: str, n: int) -> str:
    """Deliberately problematic test entities, e.g. REC_TEST_001."""
    return f"{prefix}_TEST_{n:03d}"


# ----------------------------------------------------------------- GSTIN-like
def gstin_check_char(first14: str) -> str:
    """Standard GSTIN mod-36 check character for a 14-character body."""
    total = 0
    for i, ch in enumerate(first14):
        product = CHARSET.index(ch) * (1 if i % 2 == 0 else 2)
        total += product // 36 + product % 36
    return CHARSET[(36 - total % 36) % 36]


def gstin_checksum_valid(gstin: str) -> bool:
    if not gstin or len(gstin) != 15 or any(c not in CHARSET for c in gstin):
        return False
    return gstin_check_char(gstin[:14]) == gstin[14]


def gstin_format_ok(gstin: str) -> bool:
    return bool(gstin) and bool(GSTIN_FORMAT_RE.match(gstin))


def fake_gstin(rng: random.Random, state_code: str, holder: str = "C") -> str:
    """GSTIN-shaped value whose check character is guaranteed wrong.

    holder: 4th PAN-like letter — 'C' company, 'F' firm/LLP.
    """
    pan = (
        "".join(rng.choice(LETTERS) for _ in range(3))
        + holder
        + rng.choice(LETTERS)
        + f"{rng.randrange(10000):04d}"
        + rng.choice(LETTERS)
    )
    body = f"{state_code}{pan}{rng.choice('123')}Z"
    correct = gstin_check_char(body)
    offset = 1 + rng.randrange(35)  # 1..35 → never the correct character
    wrong = CHARSET[(CHARSET.index(correct) + offset) % 36]
    value = body + wrong
    assert not gstin_checksum_valid(value)
    return value


# ----------------------------------------------------------------- documents
def invoice_series(name: str) -> str:
    """'SY' + first two letters of the issuer name → visibly synthetic series."""
    letters = [c for c in name.upper() if c.isalpha()]
    return "SY" + "".join(letters[:2]).ljust(2, "X")


def fy_code(year_start: int) -> str:
    """FY 2025-26 → '2526'."""
    return f"{year_start % 100:02d}{(year_start + 1) % 100:02d}"


def invoice_number(series: str, fy: str, seq: int) -> str:
    value = f"{series}/{fy}/{seq:05d}"
    if len(value) > 16:
        raise ValueError(f"invoice number too long: {value}")
    return value


def recycler_registration_number(state_abbrev: str, year: int, seq: int) -> str:
    """Deliberately unlike any portal format: SYN-PWP-<ST>-<YYYY>-<NNNN>."""
    return f"SYN-PWP-{state_abbrev}-{year:04d}-{seq:04d}"


def fake_phone(n: int) -> str:
    """Leading zero after +91 → not a valid Indian mobile number."""
    return f"+91-00000-0{n % 10000:04d}"


def fake_bank_account(n: int) -> str:
    return f"SYN-ACCT-{n:06d}"


FAKE_IFSC = "SYNT0DEMO01"
