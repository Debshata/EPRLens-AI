"""Shared read-only view of the entity master plus deterministic helpers for the
full-dataset generator. SYNTHETIC — EPRLens Demo.

The entity master in synthetic-data/masters is the single source of truth: this
module only READS it; activity data never adds entities.
"""
import math
from datetime import date, timedelta

from . import identifiers as ids
from .entity_index import EntityIndex

SIZE_ORDER = ("micro", "small", "medium", "large")


def month_list(start: str, end: str):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def fy_start_year(day_or_month: str) -> int:
    y, m = int(day_or_month[:4]), int(day_or_month[5:7])
    return y if m >= 4 else y - 1


def fy_label(day_or_month: str) -> str:
    y = fy_start_year(day_or_month)
    return f"FY{y}-{(y + 1) % 100:02d}"


def business_day(r, month: str, lo: int = 1, hi: int = 28) -> str:
    """Deterministic Mon–Sat day inside a month."""
    y, m = int(month[:4]), int(month[5:])
    d = date(y, m, r.randint(lo, hi))
    if d.weekday() == 6:  # Sunday → Monday (stays within the month because hi ≤ 28)
        d += timedelta(days=1)
    return d.isoformat()


def dirichlet(r, alphas):
    xs = [r.gammavariate(a, 1.0) for a in alphas]
    s = sum(xs) or 1.0
    return [x / s for x in xs]


def beta(r, a, b):
    return r.betavariate(a, b)


def split_integer(total: int, weights):
    """Largest-remainder split of an integer by weights (deterministic)."""
    raw = [total * w for w in weights]
    out = [int(math.floor(x)) for x in raw]
    rest = total - sum(out)
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - out[i]), i))
    for i in order[:rest]:
        out[i] += 1
    return out


def weighted_pick(r, items, weights):
    total = sum(weights)
    x = r.random() * total
    for it, w in zip(items, weights):
        x -= w
        if x < 0:
            return it
    return items[-1]


class Counter:
    def __init__(self):
        self.n = {}

    def next(self, prefix):
        self.n[prefix] = self.n.get(prefix, 0) + 1
        return ids.make_id(prefix, self.n[prefix])


class World:
    def __init__(self, cfg, masters_dir, company_limit=None):
        self.cfg = cfg
        self.seed = cfg["seed"]
        self.ix = EntityIndex(masters_dir)
        t = self.ix.tables
        companies = t["companies"]
        if company_limit:
            companies = companies[:company_limit]
        self.companies = companies
        self.company = {c["company_id"]: c for c in companies}
        self.months = month_list(cfg["window"]["start"], cfg["window"]["end"])
        self.month_index = {m: i for i, m in enumerate(self.months)}
        self.products_by_company = {cid: [] for cid in self.company}
        for p in t["products"]:
            if p["company_id"] in self.company:
                self.products_by_company[p["company_id"]].append(p)
        self.product = {p["product_id"]: p for ps in self.products_by_company.values() for p in ps}
        self.versions = {}  # (product_id, component_name) -> [component rows by version]
        for c in t["packaging_components"]:
            if c["product_id"] in self.product:
                self.versions.setdefault((c["product_id"], c["component_name"]), []).append(c)
        for v in self.versions.values():
            v.sort(key=lambda r: r["spec_version"])
        self.groups_by_product = {}
        for (pid, name) in sorted(self.versions):
            self.groups_by_product.setdefault(pid, []).append(name)
        self.supplier = self.ix.by_id["suppliers"]
        self.buyer = self.ix.by_id["buyers"]
        self.recycler = self.ix.by_id["recyclers"]
        self.address = self.ix.by_id["addresses"]
        self.buyers_of, self.recyclers_of, self.discontinued = {}, {}, {}
        for r in t["entity_relationships"]:
            src = r["source_entity_id"]
            if src not in self.company:
                continue
            if r["relationship_type"] == "SELLS_TO":
                self.buyers_of.setdefault(src, []).append(r["target_entity_id"])
            elif r["relationship_type"] == "USES_RECYCLER":
                self.recyclers_of.setdefault(src, []).append(r["target_entity_id"])
            elif r["relationship_type"] == "OWNS_PRODUCT" and r["end_date"]:
                self.discontinued[r["target_entity_id"]] = r["end_date"]
        self.ids = Counter()

    # ------------------------------------------------------------ randomness
    def r(self, stage, key=""):
        return ids.stream(self.seed, stage, key)

    def sub_seed(self, stage, key=""):
        return ids.sub_seed(self.seed, stage, key)

    # ------------------------------------------------------------ specs
    def version_on(self, pid, name, day: str):
        vs = self.versions[(pid, name)]
        for v in vs:
            if v["effective_from"] <= day and (v["effective_to"] is None or v["effective_to"] >= day):
                return v
        return vs[0] if day < vs[0]["effective_from"] else vs[-1]

    def components_on(self, pid, day: str):
        return [self.version_on(pid, name, day) for name in self.groups_by_product.get(pid, [])]

    def active_months(self, p):
        """(first_index, last_index) of months in which a product can sell."""
        launch = p["launch_date"][:7]
        first = self.month_index.get(launch, 0 if launch < self.months[0] else len(self.months))
        last = len(self.months) - 1
        if p["product_id"] in self.discontinued:
            end = self.discontinued[p["product_id"]][:7]
            last = self.month_index.get(end, last)
        return first, last

    def party_name(self, pid):
        for table, key in (("companies", "company_name"), ("suppliers", "supplier_name"),
                           ("buyers", "buyer_name"), ("recyclers", "recycler_name")):
            row = self.ix.by_id[table].get(pid)
            if row:
                return row[key]
        raise KeyError(pid)

    def party(self, pid):
        return self.ix.resolve(pid)

    def party_state(self, pid):
        row = self.ix.resolve(pid)
        return row.get("headquarters_state") or row["state"]
