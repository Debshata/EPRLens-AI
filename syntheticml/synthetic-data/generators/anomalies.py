"""Anomaly injection on the OBSERVED copy of the world, with ground truth.
SYNTHETIC — EPRLens Demo. Catalogue: docs/anomaly-catalogue.md.

Principles:
  * The clean world is copied before injection and written separately.
  * Each anomaly instance touches records that no other instance touched
    (no compounds), so every label maps to exactly one mutation.
  * Labels live only in anomaly_ground_truth.csv (+ summary flags on invoices).
"""
import copy

from . import identifiers as ids
from .world import fy_start_year

SEVERITY = {
    "AN01": "high", "AN02": "medium", "AN03": "medium", "AN04": "high", "AN05": "high", "AN06": "medium",
    "AN07": "medium", "AN08": "high", "AN09": "medium", "AN10": "medium", "AN11": "high", "AN12": "medium",
    "AN13": "high", "AN14": "high", "AN15": "medium", "AN16": "medium", "AN17": "n/a", "AN18": "medium",
    "AN19": "medium", "AN20": "medium",
}
METHOD = {
    "AN01": "R+ML", "AN02": "R+ML", "AN03": "R", "AN04": "R", "AN05": "R", "AN06": "R", "AN07": "R",
    "AN08": "R", "AN09": "ML", "AN10": "R+ML", "AN11": "R", "AN12": "R", "AN13": "R", "AN14": "R",
    "AN15": "R", "AN16": "R", "AN17": "R", "AN18": "R", "AN19": "R", "AN20": "R",
}
RULES = {
    "AN01": ["QTY_RATIO_POW10", "QTY_MATCH_TOL"], "AN02": ["QTY_RATIO_POW10", "QTY_MATCH_TOL"],
    "AN03": ["MATERIAL_MASTER_MATCH"], "AN04": ["CATEGORY_MASTER_MATCH"], "AN05": ["DUP_COMPOSITE_KEY"],
    "AN06": ["REQUIRED_FIELDS"], "AN07": ["QTY_MATCH_TOL"], "AN08": ["UNIT_RATIO_1000", "QTY_MATCH_TOL"],
    "AN09": [], "AN10": ["WEIGHT_RANGE_BY_FORM", "QTY_MATCH_TOL"], "AN11": ["RECYCLED_LE_COLLECTED"],
    "AN12": ["COLLECTED_LE_GENERATED"], "AN13": ["RECYCLER_REGISTERED"], "AN14": ["STATUS_CANCELLED_EXCLUDED"],
    "AN15": ["CREDIT_NOTE_APPLIED"], "AN16": ["RETURN_APPLIED"], "AN17": ["DUP_COMPOSITE_KEY"],
    "AN18": ["SPEC_VERSION_BY_DATE"], "AN19": ["CATEGORY_SPLIT_SUM"], "AN20": ["SUPPLIER_SUPPLIES_ITEM"],
}
MATERIAL_SWAP = {"PET": "HDPE", "HDPE": "PP", "PP": "HDPE", "LDPE": "PP", "LLDPE": "PP", "PS": "PP", "PVC": "PET",
                 "MLP": "LDPE", "COMPOSTABLE": "LDPE"}
CATEGORY_SWAP = {"CAT_I": "CAT_II", "CAT_II": "CAT_III", "CAT_III": "CAT_II", "CAT_IV": "CAT_II"}
PURCHASE_TYPES = ("PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL", "IMPORT_COMMERCIAL")
COUNT_UNITS = ("pcs", "bottles", "bags")


def _fmt(v):
    return "" if v is None else str(v)


class Injector:
    def __init__(self, w, reg, txns, recycling, splits, shared_groups, twins):
        self.w, self.reg = w, reg
        self.txns = txns
        self.txn = {t["transaction_id"]: t for t in txns}
        self.removed_txns = set()
        self.recycling = recycling
        self.rec_by_id = {r["recycling_record_id"]: r for r in recycling}
        self.splits = splits
        self.gt = []
        self.used_inv, self.used_txn, self.used_rec = set(), set(), set()
        self.shared = {i for g in shared_groups for i in g}
        self.shared_groups = shared_groups
        self.twins = set(twins)
        self.touched = set()
        self.cfg = w.cfg["anomalies"]
        self.line_by_txn = {}
        self.line_by_rec = {}
        for iid, lines in reg.lines.items():
            for l in lines:
                if l["transaction_id"]:
                    self.line_by_txn[l["transaction_id"]] = l
                if l["source_record_id"]:
                    self.line_by_rec[l["source_record_id"]] = l

    # ------------------------------------------------------------ bookkeeping
    def label(self, atype, record_type, record_id, company_id, field, orig, mod, invoice_id=None,
              is_anomaly=True, test_case="targeted_anomaly", note=None):
        self.gt.append({
            "anomaly_instance_id": None, "record_id": record_id, "record_type": record_type, "anomaly_type": atype,
            "company_id": company_id, "invoice_id": invoice_id, "field": field, "original_value": _fmt(orig),
            "modified_value": _fmt(mod), "expected_detection_method": METHOD[atype],
            "expected_rule_ids": RULES[atype], "severity": SEVERITY[atype], "is_anomaly": is_anomaly,
            "test_case_type": test_case, "split": self.splits[company_id], "seed": self.w.sub_seed("anomaly", atype),
            "note": note, "synthetic_flag": True,
        })
        if invoice_id:
            self.touched.add(invoice_id)

    def rng(self, atype):
        return self.w.r("anomaly", atype)

    def trade_txns(self, types=("sale", "purchase", "import")):
        out = []
        for t in self.txns:
            if t["transaction_type"] not in types or t["status"] != "posted" or not t["invoice_id"]:
                continue
            if t["transaction_id"] in self.used_txn or t["invoice_id"] in self.used_inv:
                continue
            if t["invoice_id"] in self.shared or t["invoice_id"] in self.twins:
                continue
            if self.reg.invoices[t["invoice_id"]]["status"] != "issued":
                continue
            out.append(t)
        return out

    def take(self, atype, cands, k, key=lambda x: x):
        cands = sorted(cands, key=key)
        r = self.rng(atype)
        return r.sample(cands, max(0, min(k, len(cands))))

    def scale_txn(self, t, f):
        if t["raw_unit"] in COUNT_UNITS:
            t["raw_quantity"] = int(round(t["raw_quantity"] * f))
        else:
            t["raw_quantity"] = round(t["raw_quantity"] * f, 6)
        if t["units"] is not None:
            t["units"] = int(round(t["units"] * f))
        t["normalized_quantity_kg"] = round(t["normalized_quantity_kg"] * f, 3)
        if t["plastic_kg"] is not None:
            t["plastic_kg"] = round(t["plastic_kg"] * f, 3)
        line = self.line_by_txn.get(t["transaction_id"])
        if line:
            line["recorded_quantity_kg"] = t["normalized_quantity_kg"]

    def mark(self, t):
        self.used_txn.add(t["transaction_id"])
        self.used_inv.add(t["invoice_id"])

    # ------------------------------------------------------------ CSV-side quantity errors
    def an01_an02_an07(self):
        cnt = self.cfg["invoice_counts"]
        r = self.rng("AN01")
        for t in self.take("AN01", [t for t in self.trade_txns() if t["normalized_quantity_kg"] > 1],
                           cnt["AN01"], key=lambda t: t["transaction_id"]):
            f = r.choices([10, 100, 1000], weights=[0.5, 0.3, 0.2])[0]
            o = t["raw_quantity"]
            self.scale_txn(t, f)
            self.mark(t)
            self.label("AN01", "transaction", t["transaction_id"], t["company_id"], "raw_quantity", o,
                       t["raw_quantity"], t["invoice_id"], note=f"x{f}")
        r = self.rng("AN02")
        cands = [t for t in self.trade_txns() if t["raw_quantity"] >= 1000]
        for t in self.take("AN02", cands, cnt["AN02"], key=lambda t: t["transaction_id"]):
            f = r.choice([10, 100, 1000])
            while t["raw_quantity"] / f < 1:
                f //= 10
            o = t["raw_quantity"]
            self.scale_txn(t, 1.0 / f)
            self.mark(t)
            self.label("AN02", "transaction", t["transaction_id"], t["company_id"], "raw_quantity", o,
                       t["raw_quantity"], t["invoice_id"], note=f"/{f}")
        r = self.rng("AN07")
        cands = [t for t in self.trade_txns() if t["raw_quantity"] >= 20]
        for t in self.take("AN07", cands, cnt["AN07"], key=lambda t: t["transaction_id"]):
            f = 1 + r.choice([-1, 1]) * r.uniform(0.05, 0.6)
            o = t["raw_quantity"]
            self.scale_txn(t, f)
            self.mark(t)
            self.label("AN07", "transaction", t["transaction_id"], t["company_id"], "raw_quantity", o,
                       t["raw_quantity"], t["invoice_id"], note=f"x{f:.3f}")

    def an08(self):
        k = self.cfg["invoice_counts"]["AN08"]
        r = self.rng("AN08")
        demo = [t for t in self.txns if t.get("_topup") == "demo_half_tonne"]
        picked = []
        for t in demo:
            self._an08_apply(t, "mt_magnitude", note="DEMO: 0.5 MT printed, 500 MT recorded (handbook p.15 pattern)")
            picked.append(t)
        pool = self.trade_txns(("purchase", "import"))
        subtypes = [("mt_magnitude", lambda t: t["raw_unit"] == "MT"),
                    ("kg_as_mt", lambda t: t["raw_unit"] == "kg"),
                    ("kg_as_g", lambda t: t["raw_unit"] == "kg"),
                    ("pcs_as_kg", lambda t: t["raw_unit"] == "pcs")]
        per = (k - len(picked)) // 4
        for i, (sub, ok) in enumerate(subtypes):
            want = per if i < 3 else k - len(picked)
            imports = [t for t in self.trade_txns(("import",)) if ok(t)]
            domestic = [t for t in self.trade_txns(("purchase",)) if ok(t)]
            n_imp = min(len(imports), int(round(want * 0.4)))
            chosen = self.take("AN08", imports, n_imp, key=lambda t: t["transaction_id"])
            chosen += self.take("AN08", [t for t in domestic if t not in chosen], want - len(chosen),
                                key=lambda t: t["transaction_id"])
            for t in chosen:
                self._an08_apply(t, sub)
                picked.append(t)
        del pool, r

    def _an08_apply(self, t, sub, note=None):
        o = f"{t['raw_quantity']} {t['raw_unit']}"
        if sub == "mt_magnitude":
            t["raw_quantity"] = round(t["raw_quantity"] * 1000, 3)
            t["normalized_quantity_kg"] = round(t["normalized_quantity_kg"] * 1000, 3)
        elif sub == "kg_as_mt":
            t["raw_unit"] = "MT"
            t["normalized_quantity_kg"] = round(t["normalized_quantity_kg"] * 1000, 3)
        elif sub == "kg_as_g":
            t["raw_unit"] = "g"
            t["normalized_quantity_kg"] = round(t["normalized_quantity_kg"] / 1000, 3)
        elif sub == "pcs_as_kg":
            t["raw_unit"] = "kg"
            t["normalized_quantity_kg"] = float(t["raw_quantity"])
        t["plastic_kg"] = t["normalized_quantity_kg"] if t["plastic_kg"] else t["plastic_kg"]
        line = self.line_by_txn.get(t["transaction_id"])
        if line:
            line["recorded_quantity_kg"] = t["normalized_quantity_kg"]
        self.mark(t)
        self.label("AN08", "transaction", t["transaction_id"], t["company_id"], "raw_quantity|raw_unit", o,
                   f"{t['raw_quantity']} {t['raw_unit']}", t["invoice_id"], note=note or sub)

    def an18(self):
        w = self.w
        k = self.cfg["invoice_counts"]["AN18"]
        v2 = {}
        for (pid, name), vs in w.versions.items():
            if len(vs) > 1:
                v2.setdefault(pid, []).append((vs[0], vs[1]))
        cands = [t for t in self.trade_txns(("sale",)) if t["product_id"] in v2
                 and any(t["date"] >= b["effective_from"] for _, b in v2[t["product_id"]])]
        for t in self.take("AN18", cands, k, key=lambda t: t["transaction_id"]):
            o = t["normalized_quantity_kg"]
            delta = sum(t["units"] * (a["weight_per_unit_g"] - b["weight_per_unit_g"]) / 1000.0
                        for a, b in v2[t["product_id"]] if t["date"] >= b["effective_from"])
            t["normalized_quantity_kg"] = round(o + delta, 3)
            line = self.line_by_txn.get(t["transaction_id"])
            if line:
                line["recorded_quantity_kg"] = t["normalized_quantity_kg"]
            self.mark(t)
            self.label("AN18", "transaction", t["transaction_id"], t["company_id"], "normalized_quantity_kg", o,
                       t["normalized_quantity_kg"], t["invoice_id"], note="v1 weight used after v2 effective_from")

    def an19(self):
        k = self.cfg["invoice_counts"]["AN19"]
        cands = []
        for iid, inv in self.reg.invoices.items():
            if inv["invoice_type"] not in ("PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL") or iid in self.used_inv:
                continue
            if inv["status"] != "issued" or iid in self.shared or iid in self.twins:
                continue
            ls = self.reg.lines[iid]
            for a in range(len(ls)):
                for b in range(a + 1, len(ls)):
                    la, lb = ls[a], ls[b]
                    if la["raw_unit"] == lb["raw_unit"] and la["plastic_category"] != lb["plastic_category"]:
                        cands.append((iid, la["transaction_id"], lb["transaction_id"]))
                        break
                else:
                    continue
                break
        for iid, ta, tb in self.take("AN19", cands, k):
            a, b = self.txn[ta], self.txn[tb]
            o = a["raw_quantity"]
            a["raw_quantity"] = round(a["raw_quantity"] + b["raw_quantity"], 6)
            if a["units"] is not None and b["units"] is not None:
                a["units"] = a["units"] + b["units"]
            a["normalized_quantity_kg"] = round(a["normalized_quantity_kg"] + b["normalized_quantity_kg"], 3)
            a["plastic_kg"] = round((a["plastic_kg"] or 0) + (b["plastic_kg"] or 0), 3)
            self.removed_txns.add(tb)
            self.line_by_txn[ta]["recorded_quantity_kg"] = a["normalized_quantity_kg"]
            self.line_by_txn[tb]["recorded_quantity_kg"] = None
            self.used_inv.add(iid)
            self.used_txn.update([ta, tb])
            self.label("AN19", "transaction", ta, a["company_id"], "raw_quantity", o, a["raw_quantity"], iid,
                       note=f"absorbed {tb} (different category) into one record")

    # ------------------------------------------------------------ distributional spikes (both sides)
    def an09(self):
        w = self.w
        k = self.cfg["product_month_counts"]["AN09"]
        pm = {}
        for t in self.trade_txns(("sale",)):
            pm.setdefault((t["product_id"], t["date"][:7]), []).append(t)
        r = self.rng("AN09")
        done = 0
        for key in self.take("AN09", list(pm), len(pm)):
            if done >= k:
                break
            txs = [t for t in pm[key] if t["transaction_id"] not in self.used_txn and t["invoice_id"] not in self.used_inv]
            if not txs:
                continue
            done += 1
            f = round(r.uniform(3, 6), 3)
            before = sum(t["units"] for t in txs)
            for t in txs:
                self._scale_both(t, f)
            after = sum(t["units"] for t in txs)
            for t in txs:
                self.mark(t)
            self.label("AN09", "product_month", f"{key[0]}:{key[1]}", txs[0]["company_id"], "units", before, after,
                       None, note=f"x{f} on {len(txs)} sale rows and their invoice lines")
            for t in txs:
                self.touched.add(t["invoice_id"])
        # TS02 SUP_TEST_001 supplier spikes
        tops = [t for t in self.txns if t.get("_topup") == "share" and t["transaction_id"] not in self.used_txn]
        for t in self.take("AN09", tops, self.cfg["supplier_spike_counts"]["AN09"], key=lambda t: t["transaction_id"]):
            o = t["raw_quantity"]
            self._scale_both(t, 5.0)
            self.mark(t)
            self.label("AN09", "transaction", t["transaction_id"], t["company_id"], "raw_quantity", o,
                       t["raw_quantity"], t["invoice_id"], note="TS02_SUPPLIER_ABNORMAL_QUANTITY x5 (invoice and record)")
        del w

    def _scale_both(self, t, f):
        self.scale_txn(t, f)
        line = self.line_by_txn[t["transaction_id"]]
        line["raw_quantity"] = t["raw_quantity"]
        line["normalized_quantity_kg"] = t["normalized_quantity_kg"]
        line["recorded_quantity_kg"] = t["normalized_quantity_kg"]
        self._reprice(line)

    def _reprice(self, line):
        inv = self.reg.invoices[line["invoice_id"]]
        line["taxable_value"] = round((line["raw_quantity"] if line["raw_quantity"] is not None else 1) * line["rate"], 2)
        line["gst_amount"] = 0.0 if inv["tax_mode"] == "import" else round(line["taxable_value"] * line["gst_rate"] / 100, 2)
        self.reg.recompute(inv)

    # ------------------------------------------------------------ document-side errors
    def doc_invoices(self, types):
        return [iid for iid, inv in self.reg.invoices.items() if inv["invoice_type"] in types and inv["status"] == "issued"
                and iid not in self.used_inv and iid not in self.shared and iid not in self.twins]

    def an03_an04_an10(self):
        cnt = self.cfg["invoice_counts"]
        for atype, k in (("AN03", cnt["AN03"]), ("AN04", cnt["AN04"]), ("AN10", cnt["AN10"])):
            cands = []
            for iid in self.doc_invoices(PURCHASE_TYPES):
                for l in self.reg.lines[iid]:
                    if atype == "AN03" and l["material"] in MATERIAL_SWAP:
                        cands.append((iid, l["invoice_line_id"]))
                        break
                    if atype == "AN04" and l["plastic_category"] in CATEGORY_SWAP:
                        cands.append((iid, l["invoice_line_id"]))
                        break
                    if atype == "AN10" and l["raw_unit"] == "pcs" and l["weight_per_unit_g"]:
                        cands.append((iid, l["invoice_line_id"]))
                        break
            r = self.rng(atype)
            for iid, lid in self.take(atype, cands, k):
                l = next(x for x in self.reg.lines[iid] if x["invoice_line_id"] == lid)
                inv = self.reg.invoices[iid]
                if atype == "AN03":
                    o = l["material"]
                    l["material"] = MATERIAL_SWAP[o]
                    l["item_description"] = l["item_description"].replace(f"- {o}", f"- {l['material']}")
                    self.label("AN03", "invoice_line", lid, inv["company_id"], "material", o, l["material"], iid)
                elif atype == "AN04":
                    o = l["plastic_category"]
                    l["plastic_category"] = CATEGORY_SWAP[o]
                    self.label("AN04", "invoice_line", lid, inv["company_id"], "plastic_category", o, l["plastic_category"], iid)
                else:
                    o = l["weight_per_unit_g"]
                    nw = round(o * r.uniform(8, 15), 1)
                    l["weight_per_unit_g"] = nw
                    l["item_description"] = l["item_description"].replace(f"({o} g/pc)", f"({nw} g/pc)")
                    l["normalized_quantity_kg"] = round(l["raw_quantity"] * nw / 1000.0, 3)
                    self.label("AN10", "invoice_line", lid, inv["company_id"], "weight_per_unit_g", o, nw, iid)
                self.used_inv.add(iid)

    def an06(self):
        k = self.cfg["invoice_counts"]["AN06"]
        subs = [("raw_quantity", 0.25), ("raw_unit", 0.15), ("invoice_date", 0.15), ("plastic_category", 0.20),
                ("supplier_gstin", 0.15), ("hsn_code", 0.10)]
        for sub, share in subs:
            n = int(round(k * share))
            if sub == "plastic_category":
                cands = [i for i in self.doc_invoices(PURCHASE_TYPES)
                         if any(l["plastic_category"] in CATEGORY_SWAP for l in self.reg.lines[i])]
            elif sub == "supplier_gstin":
                cands = [i for i in self.doc_invoices(("PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL", "FG_SALES"))
                         if self.reg.invoices[i]["supplier_gstin"]]
            else:
                cands = self.doc_invoices(("PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL", "FG_SALES"))
            for iid in self.take("AN06", cands, n):
                inv = self.reg.invoices[iid]
                if sub in ("invoice_date", "supplier_gstin"):
                    o = inv[sub]
                    inv[sub] = None
                    self.label("AN06", "invoice", iid, inv["company_id"], sub, o, None, iid)
                else:
                    if sub == "plastic_category":
                        l = next(x for x in self.reg.lines[iid] if x["plastic_category"] in CATEGORY_SWAP)
                    else:
                        l = self.reg.lines[iid][0]
                    o = l[sub]
                    l[sub] = None
                    if sub in ("raw_quantity", "raw_unit"):
                        l["normalized_quantity_kg"] = None
                    self.label("AN06", "invoice_line", l["invoice_line_id"], inv["company_id"], sub, o, None, iid)
                self.used_inv.add(iid)

    def an20(self):
        w = self.w
        k = self.cfg["invoice_counts"]["AN20"]
        n = 0
        # TS03: SUP_TEST_002 invoices switch PP -> HDPE from 2025-07 (supplier master says PP only)
        for iid in sorted(self.doc_invoices(PURCHASE_TYPES)):
            inv = self.reg.invoices[iid]
            if inv["supplier_id"] != "SUP_TEST_002" or inv["invoice_date"] < "2025-07-01":
                continue
            for l in self.reg.lines[iid]:
                if l["material"] == "PP":
                    l["material"] = "HDPE"
                    l["item_description"] = l["item_description"].replace("- PP", "- HDPE")
                    self.label("AN20", "invoice_line", l["invoice_line_id"], inv["company_id"], "material", "PP", "HDPE",
                               iid, note="TS03_SUPPLIER_MATERIAL_CHANGE")
                    n += 1
            self.used_inv.add(iid)
        normal = [s for s in w.ix.tables["suppliers"] if not s["test_entity"]]
        cands = self.doc_invoices(("PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL"))
        r = self.rng("AN20")
        for iid in self.take("AN20", cands, max(0, k - n)):
            inv = self.reg.invoices[iid]
            mats = {l["material"] for l in self.reg.lines[iid]}
            wrong = [s for s in normal if not mats & set(s["supported_materials"]) and s["supplier_id"] != inv["supplier_id"]]
            if not wrong:
                continue
            s = wrong[r.randrange(len(wrong))]
            o = inv["supplier_id"]
            inv["supplier_id"] = s["supplier_id"]
            inv["supplier_gstin"] = s["fake_gstin"]
            inv["tax_mode"] = "intra" if s["state"] == inv["place_of_supply_state"] else "inter"
            self.reg.recompute(inv)
            self.used_inv.add(iid)
            self.label("AN20", "invoice", iid, inv["company_id"], "supplier_id", o, s["supplier_id"], iid,
                       note=f"{s['supplier_type']} does not supply {sorted(mats)}")

    # ------------------------------------------------------------ status / adjustments
    def an05(self, txns_out):
        w = self.w
        k = self.cfg["invoice_counts"]["AN05"]
        from .activity import _txn
        cands = self.doc_invoices(("FG_SALES", "PKG_PURCHASE", "PKG_COMPONENT"))
        for iid in self.take("AN05", cands, k):
            orig = self.reg.invoices[iid]
            dup = copy.deepcopy(orig)
            dup["invoice_id"] = w.ids.next("INV")
            self.reg.invoices[dup["invoice_id"]] = dup
            self.reg.lines[dup["invoice_id"]] = []
            for l in self.reg.lines[iid]:
                nl = copy.deepcopy(l)
                nl["invoice_line_id"] = w.ids.next("INVL")
                nl["invoice_id"] = dup["invoice_id"]
                if l["transaction_id"]:
                    src = self.txn[l["transaction_id"]]
                    tx = _txn(w, **{kk: v for kk, v in src.items() if not kk.startswith("_") and kk != "transaction_id"})
                    tx["invoice_id"] = dup["invoice_id"]
                    txns_out.append(tx)
                    self.txn[tx["transaction_id"]] = tx
                    nl["transaction_id"] = tx["transaction_id"]
                    self.used_txn.add(tx["transaction_id"])
                self.reg.lines[dup["invoice_id"]].append(nl)
            self.used_inv.update([iid, dup["invoice_id"]])
            dup["_duplicate_of"] = iid
            self.label("AN05", "invoice", dup["invoice_id"], orig["company_id"], "invoice_id", iid, dup["invoice_id"],
                       dup["invoice_id"], note=f"duplicate entry of {iid} (same number, date, amount)")

    def an14_an15_an16(self):
        cnt = self.cfg["invoice_counts"]
        for iid in self.take("AN14", [t for t in self.twins if t not in self.used_inv], cnt["AN14"]):
            inv = self.reg.invoices[iid]
            for l in self.reg.lines[iid]:
                self.txn[l["transaction_id"]]["status"] = "posted"
            self.used_inv.add(iid)
            self.label("AN14", "invoice", iid, inv["company_id"], "transaction.status", "cancelled", "posted", iid)
        for atype, itype in (("AN15", "CREDIT_NOTE"), ("AN16", "RETURN")):
            cands = [i for i in self.doc_invoices((itype,))]
            for iid in self.take(atype, cands, cnt[atype]):
                inv = self.reg.invoices[iid]
                for l in self.reg.lines[iid]:
                    if l["transaction_id"]:
                        self.removed_txns.add(l["transaction_id"])
                        o = l["transaction_id"]
                        l["transaction_id"] = None
                        l["recorded_quantity_kg"] = None
                        self.label(atype, "invoice", iid, inv["company_id"], "transaction_id", o, None, iid,
                                   note=f"{'credit note' if atype == 'AN15' else 'return'} not applied in records")
                self.used_inv.add(iid)

    # ------------------------------------------------------------ recycling
    def recycling_anomalies(self):
        w = self.w
        cnt = self.cfg["recycling_counts"]
        multi = {}
        for iid, ls in self.reg.lines.items():
            if self.reg.invoices[iid]["invoice_type"] == "RECYCLER_PROCESSING":
                for l in ls:
                    multi[l["source_record_id"]] = len(ls)
        rows = sorted(self.recycling, key=lambda r: r["recycling_record_id"])
        r11 = self.rng("AN11")
        for row in self.take("AN11", rows, cnt["AN11"], key=lambda r: r["recycling_record_id"]):
            o = row["waste_recycled_kg"]
            row["waste_recycled_kg"] = round(row["waste_collected_kg"] * r11.uniform(1.1, 1.6), 3)
            self._sync_rec_line(row)
            self.used_rec.add(row["recycling_record_id"])
            self.label("AN11", "recycling", row["recycling_record_id"], row["company_id"], "waste_recycled_kg", o,
                       row["waste_recycled_kg"], self.line_by_rec[row["recycling_record_id"]]["invoice_id"])
        r12 = self.rng("AN12")
        rest = [r for r in rows if r["recycling_record_id"] not in self.used_rec]
        for row in self.take("AN12", rest, cnt["AN12"], key=lambda r: r["recycling_record_id"]):
            o = row["waste_collected_kg"]
            row["waste_collected_kg"] = round(row["waste_generated_kg"] * r12.uniform(1.1, 1.8), 3)
            self._sync_rec_line(row)
            self.used_rec.add(row["recycling_record_id"])
            self.label("AN12", "recycling", row["recycling_record_id"], row["company_id"], "waste_collected_kg", o,
                       row["waste_collected_kg"], self.line_by_rec[row["recycling_record_id"]]["invoice_id"])
        # AN13 — TS01 rows first (COMP_0003 -> REC_TEST_001), then normal unregistered recyclers
        unreg = [x for x in w.ix.tables["recyclers"] if not x["registered"] and not x["test_entity"]]
        rest = [r for r in rows if r["recycling_record_id"] not in self.used_rec and multi.get(r["recycling_record_id"], 0) >= 2]
        ts01 = [r for r in rest if r["company_id"] == "COMP_0003"][: min(self.cfg["ts01_rows"], cnt["AN13"])]
        r13 = self.rng("AN13")
        picks = [(r, "REC_TEST_001") for r in ts01]
        others = [r for r in rest if r not in ts01]
        for row in self.take("AN13", others, cnt["AN13"] - len(picks), key=lambda r: r["recycling_record_id"]):
            mats = {m for p in w.products_by_company[row["company_id"]] for name in w.groups_by_product.get(p["product_id"], [])
                    for m in [w.versions[(p["product_id"], name)][0]["material"]]}
            fit = [u for u in unreg if mats & set(u["supported_materials"])] or unreg
            picks.append((row, fit[r13.randrange(len(fit))]["recycler_id"]))
        for row, rid in picks:
            if row["recycling_record_id"] in self.used_rec:
                continue
            o = row["recycler_id"]
            row["recycler_id"] = rid
            row["recycler_registered"] = False
            new_iid = self._move_rec_line(row, rid)
            self.used_rec.add(row["recycling_record_id"])
            self.label("AN13", "recycling", row["recycling_record_id"], row["company_id"], "recycler_id", o, rid, new_iid,
                       note="TS01_UNREGISTERED_RECYCLER" if rid == "REC_TEST_001" else "credits claimed via unregistered recycler")

    def _sync_rec_line(self, row):
        l = self.line_by_rec[row["recycling_record_id"]]
        l["raw_quantity"] = round(row["waste_recycled_kg"], 2)
        l["normalized_quantity_kg"] = l["raw_quantity"]
        l["recorded_quantity_kg"] = round(row["waste_recycled_kg"], 3)
        l["item_description"] = (f"Processing of post-consumer {row['synthetic_category']} plastic waste {row['month']} "
                                 f"(received {row['waste_collected_kg']:.2f} kg)")
        self._reprice(l)

    def _move_rec_line(self, row, rid):
        l = self.line_by_rec[row["recycling_record_id"]]
        old = self.reg.invoices[l["invoice_id"]]
        self.reg.lines[old["invoice_id"]].remove(l)
        self.reg.recompute(old)
        inv = self.reg.new_invoice("RECYCLER_PROCESSING", old["company_id"], rid, old["company_id"], old["invoice_date"],
                                   old["place_of_supply_state"])
        number_new(self.w, self.reg, inv)
        l["invoice_id"] = inv["invoice_id"]
        self.reg.lines[inv["invoice_id"]].append(l)
        self.reg.recompute(inv)
        self.used_inv.update([old["invoice_id"], inv["invoice_id"]])
        return inv["invoice_id"]

    # ------------------------------------------------------------ AN17 hard negatives
    def an17(self):
        for g in self.shared_groups:
            for iid in g:
                inv = self.reg.invoices[iid]
                self.label("AN17", "invoice", iid, inv["company_id"], "invoice_number", inv["invoice_number"],
                           inv["invoice_number"], iid, is_anomaly=False, test_case="targeted_legit_hard",
                           note=f"legitimate shared number across {len(g)} invoices")

    # ------------------------------------------------------------ finish
    def finish(self):
        for i, g in enumerate(self.gt, start=1):
            g["anomaly_instance_id"] = ids.make_id("ANM", i)
        first = {}
        for g in self.gt:
            if g["is_anomaly"] and g["invoice_id"]:
                first.setdefault(g["invoice_id"], g["anomaly_type"])
        for g in self.gt:
            if g["anomaly_type"] == "AN09" and g["record_type"] == "product_month":
                pass
        for iid in self.touched:
            if iid in first:
                self.reg.invoices[iid]["is_anomaly"] = True
                self.reg.invoices[iid]["anomaly_type"] = first[iid]
        for t in self.txns:
            line = self.line_by_txn.get(t["transaction_id"])
            if line is not None and line["invoice_id"] in self.reg.invoices and t["transaction_id"] not in self.removed_txns:
                pass
        return [t for t in self.txns if t["transaction_id"] not in self.removed_txns]


def number_new(w, reg, inv):
    """Assign the next number in the issuer's series to an invoice created after numbering."""
    from .invoicing import _kind
    kind = _kind(inv)
    fy = ids.fy_code(fy_start_year(inv["invoice_date"]))
    prefix = ids.invoice_series(w.party_name(inv["supplier_id"])) if kind == "TAX" else f"SY{kind}"
    existing = [i["invoice_number"] for i in reg.invoices.values()
                if i["invoice_number"] and i["invoice_number"].startswith(f"{prefix}/{fy}/")
                and i["supplier_id"] == inv["supplier_id"]]
    n = max([int(x.rsplit("/", 1)[1]) for x in existing] or [0]) + 1
    inv["invoice_number"] = ids.invoice_number(prefix, fy, n)


def inject(w, reg, txns, recycling, splits, shared_groups, twins):
    inj = Injector(w, reg, txns, recycling, splits, shared_groups, twins)
    extra = []
    inj.an08()          # demo instance first
    inj.an01_an02_an07()
    inj.an18()
    inj.an19()
    inj.an09()
    inj.an03_an04_an10()
    inj.an06()
    inj.an20()
    inj.an05(extra)
    inj.an14_an15_an16()
    inj.recycling_anomalies()
    inj.an17()
    observed = inj.finish() + extra
    # AN09 product-month flags: mark linked invoices
    pm_invoices = set()
    for g in inj.gt:
        if g["anomaly_type"] == "AN09" and g["record_type"] == "product_month":
            pid, month = g["record_id"].split(":")
            for t in observed:
                if t["product_id"] == pid and t["date"][:7] == month and t["transaction_type"] == "sale" and t["invoice_id"]:
                    if t["transaction_id"] in inj.used_txn:
                        pm_invoices.add(t["invoice_id"])
    for iid in pm_invoices:
        inv = reg.invoices[iid]
        if not inv["is_anomaly"]:
            inv["is_anomaly"], inv["anomaly_type"] = True, "AN09"
    inj.pm_invoices = pm_invoices
    return inj, observed
