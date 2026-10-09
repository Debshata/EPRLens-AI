# Dummy Identifier Rules

> SYNTHETIC — EPRLens Demo. Implementation: `synthetic-data/generators/identifiers.py`. Tests: `synthetic-data/tests/test_identifiers.py`, `tests/synthetic/test_entity_integrity.py`.
> Identifiers are structurally useful for software testing but are **not intended to correspond to any real registered entity**.

## Internal entity IDs

| Entity | Format | Width | Example | Test-entity form |
|---|---|---|---|---|
| Company | `COMP_####` | 4 | COMP_0001 | — |
| Supplier | `SUP_####` | 4 | SUP_0004 | SUP_TEST_001 |
| Buyer | `BUY_####` | 4 | BUY_0032 | BUY_TEST_001 |
| Recycler | `REC_####` | 4 | REC_0012 | REC_TEST_001 |
| Product | `PROD_######` | 6 | PROD_000001 | PROD_TEST_001 |
| Packaging component | `PKGCOMP_######` | 6 | PKGCOMP_000231 | — |
| Address | `ADDR_######` | 6 | ADDR_000010 | — |
| Relationship | `REL_######` | 6 | REL_000001 | — |
| Test user | `USR_####` | 4 | USR_0001 | — |
| Transaction | `TXN_########` | 8 | TXN_00012345 | — |
| Invoice (internal) | `INV_########` | 8 | INV_00001234 | — |
| Invoice line | `INVL_#########` | 9 | INVL_000004567 | — |
| Material event | `MEV_#########` | 9 | MEV_000045678 | — |
| Document (PDF) | `DOC_######` | 6 | DOC_000001 | — |

- IDs are assigned in generation order. The **core pack** (COMP_0001–0005, SUP_0001–0010, BUY_0001–0010, REC_0001–0005, their products/components/addresses/relationships, USR_0001–0005, all `_TEST_` entities) is generated first and identically in test and full mode, so these IDs are stable.
- **Reserved 99-range** for illustrative fixtures: `INV_99xxxxxx`, `DOC_99xxxx`, `TXN_99xxxxxx`. The generator never assigns these.

## Seeds

`sub_seed = int(sha256("{seed}:{stage}:{key}")[:16], 16)`; one `random.Random` stream per (stage, entity id). Python's salted `hash()` is never used.

## GSTIN-like values (DS-16 A)

`SS AAAAA9999A E Z C` — real GST state code, PAN-like segment (4th letter `C` company / `F` firm), entity digit, `Z`, then a check character that is **deliberately wrong** (standard mod-36 checksum computed, then shifted by 1–35 positions). Every value therefore fails GSTIN checksum validation. Format regex still passes, so format and checksum checks can be tested separately. `BUY_TEST_001` carries a truncated 14-character value; unregistered buyers carry none.

## Invoice numbers

`<SY + 2 letters of issuer>/<FY code>/<5-digit seq>` e.g. `SYYU/2526/00123` (≤ 16 characters). Credit notes `SYCN/…`, returns `SYRN/…`, import `SYEXP-…`.

## Recycler registration-like IDs

`SYN-PWP-<state abbrev>-<year>-<nnnn>` — deliberately unlike any portal format. It does **not** represent a real CPCB authorization, even for recyclers marked `registered=true` in the synthetic world. Unregistered recyclers may carry a *claimed* number (seq 900+) that matches no registered recycler.

## Contact, bank, other

| Item | Form |
|---|---|
| Email | `demo.<role><nn>@example.com` |
| Phone | `+91-00000-0NNNN` (not a valid mobile) |
| Bank account | `SYN-ACCT-NNNNNN` |
| IFSC-like | `SYNT0DEMO01` |
| PIN code | 6 digits, two-digit region-consistent prefix + 4 random digits (fictional street + plot, so not a real address) |
| Aadhaar / PAN / CIN / IEC | never generated |
