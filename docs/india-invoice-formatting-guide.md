# India Invoice Formatting Guide (synthetic conventions)

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo.
> These are **formatting conventions for fake documents**. GST law (invoice particulars, number length, tax heads) is not covered by the EPR handbook → **TBD — official-source verification** before any product logic depends on it. All identifiers are fake by construction.

## 1. GSTIN-like identifiers *(DS-16 A)*

Layout (15 characters): `SS` `AAAAA9999A` `E` `Z` `C`

| Pos | Meaning in the real format | Synthetic rule |
|---|---|---|
| 1–2 | State code | Real GST state code of the entity's state (table §8) — needed for CGST/SGST vs IGST |
| 3–12 | PAN-like segment | 5 random letters (4th letter `C` for companies, `F` for firms) + 4 digits + 1 letter |
| 13 | Entity number | `1`–`3` |
| 14 | Default `Z` | `Z` |
| 15 | Check character | **Deliberately wrong**: compute the standard mod-36 checksum, then use a *different* character |

Guarantee: every synthetic GSTIN fails checksum validation, therefore cannot be a valid registered GSTIN. `tests/synthetic/test_entity_integrity.py` asserts this for 100 % of values. A parser test may still check *format* validity (regex) separately from checksum validity.

Variants for anomaly tests: blank GSTIN (AN06), truncated 14-char GSTIN (BUY_TEST_001), state code mismatching address (AN20-adjacent).

## 2. Invoice numbers

- Format: `<series>/<FY>/<seq>` e.g. `SYEF/2526/00123` (≤ 16 characters, letters/digits/`/`/`-`).
- `series` always starts with `SY` + 2 letters from the issuer's name → visibly synthetic.
- `FY` = `2324`, `2425`, `2526`.
- Sequence resets per FY per issuer.
- Shared numbers: a configured set of legitimate groups of 2–5 invoices share one number but differ in party/date/line identity (handbook p.41; AN17 hard negatives).
- Credit notes: `SYCN/<FY>/<seq>`; returns `SYRN/<FY>/<seq>`; imports `SYEXP-<seq>`.

## 3. HSN field placement

- Column "HSN/SAC" immediately after description (L01, L02, L03, L04) or inside the tax-summary table only (L09).
- Illustrative mapping (DS-13): plastic containers/closures/bags/pouches `3923`, plastic film/sheets/blisters `3920`, self-adhesive film labels `3919`, EPS `3921`, paper cartons/boxes `4819`, paper labels `4821`, paper void fill `4808`, glass containers `7010`, aluminium cans `7612`, primary polymers `3901`–`3907`, services `9985`/`9994` (SAC). **TBD — verify; not a tax-classification claim.**

## 4. Tax heads

- Intra-state (supplier state = place of supply): `CGST @ r/2 %` and `SGST @ r/2 %` (UT: `UTGST`, not used in pilot).
- Inter-state: `IGST @ r %`.
- Import commercial invoices: no GST lines; text "IGST on import — per Bill of Entry (not modelled)".
- Rates: config set `{5, 12, 18}`, default 18 (illustrative). Rounding: each tax head rounded to 2 decimals; invoice total rounded to rupee with a printed "Round off" line (some templates).

## 5. Dates

Stored ISO `YYYY-MM-DD`. Printed as `DD/MM/YYYY` (40 %), `DD-MM-YYYY` (20 %), `DD-Mon-YYYY` e.g. `07-Oct-2025` (30 %), `YYYY-MM-DD` (10 %). Ambiguity tests: days ≤ 12 in `DD/MM` vs `MM/DD` (parser must assume DD/MM).

## 6. Indian number format

- Lakh/crore grouping: `12,34,567.89` (last three digits, then pairs).
- Western grouping and ungrouped variants on a minority of documents.
- Amount in words: "Rupees Twelve Lakh Thirty-Four Thousand Five Hundred Sixty-Seven and Eighty-Nine Paise Only".

## 7. Currency

`₹` where the font supports it, else `Rs.`; `INR` in headers. Import invoices show `USD` with an "INR equivalent @ <rate>" column; the rate is illustrative and fixed per month in config.

## 8. State codes used (verify before product use)

| Code | State/UT | PIN first digit |
|---|---|---|
| 03 | Punjab | 1 |
| 06 | Haryana | 1 |
| 07 | Delhi | 1 |
| 08 | Rajasthan | 3 |
| 09 | Uttar Pradesh | 2 |
| 05 | Uttarakhand | 2 |
| 10 | Bihar | 8 |
| 19 | West Bengal | 7 |
| 21 | Odisha | 7 |
| 18 | Assam | 7 |
| 23 | Madhya Pradesh | 4 |
| 24 | Gujarat | 3 |
| 27 | Maharashtra | 4 |
| 30 | Goa | 4 |
| 29 | Karnataka | 5 |
| 36 | Telangana | 5 |
| 37 | Andhra Pradesh | 5 |
| 33 | Tamil Nadu | 6 |
| 32 | Kerala | 6 |
| 02 | Himachal Pradesh | 1 |

## 9. Other identifiers (never real)

| Item | Synthetic form |
|---|---|
| Phone | `+91-00000-0NNNN` (leading zero → not a valid mobile) |
| Email | `<role>.<nn>@example.com` (RFC 2606 reserved domain) |
| Website | `www.<slug>.example` |
| Bank account | `SYN-ACCT-NNNNNN` |
| IFSC-like | `SYNT0DEMO01` (bank code `SYNT` is a synthetic marker; not routable — verify non-existence before demo) |
| CIN / PAN / IEC | Not printed (not required for parsing); if a template needs a CIN line it prints `CIN: SYNTHETIC-NOT-ISSUED` |
| PWP registration | `SYN-PWP-<state>-<year>-<nnnn>` (format deliberately unlike any portal format) |
| Aadhaar | **Never generated** (handbook mentions it for unregistered vendors; we print "Vendor KYC: on file (synthetic)") |
