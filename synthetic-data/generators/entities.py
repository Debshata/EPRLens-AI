"""Entity-master generation (companies, products, components, suppliers, buyers,
recyclers, addresses, relationships, test users). SYNTHETIC — EPRLens Demo.

Design:
  * The CORE pack (demo company, 4 anchor companies, 10 suppliers, 10 buyers,
    5 recyclers, *_TEST_* entities, 5 users) is generated first and identically
    in both modes, so its IDs are stable for the demo, frontend mocks and AWS
    test events.
  * FULL mode then appends the extension entities (COMP_0006…, SUP_0011…, …).
  * Every random draw comes from a stream keyed by (seed, stage, entity id).
"""
import math
from datetime import date, timedelta

from . import archetypes as arch
from . import geo, names
from . import identifiers as ids

PROCESSING_MATERIALS = {
    "PET recycling": ["PET"],
    "HDPE recycling": ["HDPE"],
    "LDPE recycling": ["LDPE", "LLDPE"],
    "PP recycling": ["PP"],
    "mixed-plastic processing": ["HDPE", "LDPE", "LLDPE", "PP", "PS", "PVC"],
    "MLP processing": ["MLP"],
    "industrial composting": ["COMPOSTABLE"],
}
PREFERRED_PROCESSING = {"PET": "PET recycling", "MLP": "MLP processing", "COMPOSTABLE": "industrial composting"}

BUYER_TYPE_WEIGHTS = {
    "distributor": 22, "wholesaler": 18, "retailer": 18, "supermarket": 12, "e-commerce seller": 12,
    "institutional buyer": 9, "manufacturing customer": 9,
}
# P(GST-registered) and P(EPR-registered | GST-registered) by buyer type — illustrative (DS-12).
BUYER_GST_P = {
    "distributor": 0.98, "wholesaler": 0.95, "retailer": 0.75, "supermarket": 0.99, "e-commerce seller": 0.97,
    "institutional buyer": 0.95, "manufacturing customer": 0.99,
}
BUYER_EPR_P = {
    "distributor": 0.6, "wholesaler": 0.5, "retailer": 0.2, "supermarket": 0.6, "e-commerce seller": 0.5,
    "institutional buyer": 0.3, "manufacturing customer": 0.7,
}
ROLE_SHORT = {
    "company_admin": "admin", "sustainability_manager": "manager", "compliance_manager": "compliance",
    "finance_user": "finance", "operations_user": "ops", "consultant": "consultant", "demo_user": "user",
}
ROLE_PERMISSIONS = {  # proposal only — D034 (roles) is pending
    "company_admin": ["company:read", "company:write", "users:manage", "uploads:write", "findings:review",
                      "scenarios:run", "reports:export"],
    "sustainability_manager": ["company:read", "uploads:write", "findings:review", "forecast:read",
                               "scenarios:run", "reports:export"],
    "compliance_manager": ["company:read", "uploads:write", "findings:review", "rules:read", "reports:export"],
    "finance_user": ["company:read", "invoices:read", "uploads:write"],
    "operations_user": ["company:read", "transactions:read", "uploads:write"],
    "consultant": ["company:read", "findings:review", "scenarios:run", "reports:export", "multi_company:read"],
    "demo_user": ["company:read", "forecast:read", "scenarios:run"],
}
FULL_ROLE_CYCLE = ["finance_user", "operations_user", "company_admin", "sustainability_manager",
                   "compliance_manager", "demo_user", "operations_user", "finance_user", "company_admin",
                   "consultant"]


# ----------------------------------------------------------------- helpers
def d(s):
    return date.fromisoformat(s) if isinstance(s, str) else s


def rand_date(r, start, end):
    start, end = d(start), d(end)
    return start + timedelta(days=r.randrange((end - start).days + 1))


def weighted(r, weights: dict):
    items = list(weights.items())
    total = sum(w for _, w in items)
    x = r.random() * total
    for k, w in items:
        x -= w
        if x < 0:
            return k
    return items[-1][0]


def prob(table: dict, key):
    return table.get(key, table["default"])


class Ctx:
    def __init__(self, cfg):
        self.cfg = cfg
        self.seed = cfg["seed"]
        self.used_names = set()
        self.used_brands = set()
        self.counters = {p: 0 for p in ("PROD", "PKGCOMP", "ADDR", "REL")}
        self.companies, self.products, self.components = [], [], []
        self.suppliers, self.buyers, self.recyclers = [], [], []
        self.addresses, self.relationships, self.users = [], [], []
        self.company_buyers = {}      # company_id -> [buyer_id]
        self.company_recyclers = {}   # company_id -> [recycler_id]
        self.extra_buys_from = []     # (company_id, supplier_id, start, end)
        self.extra_supplied_by = []   # (component_id, supplier_id, start, end)

    def r(self, stage, key=""):
        return ids.stream(self.seed, stage, key)

    def next_id(self, prefix):
        self.counters[prefix] += 1
        return ids.make_id(prefix, self.counters[prefix])

    # ------------------------------------------------------------ addresses
    def add_address(self, entity_type, entity_id, kind, state, r, city=None):
        aid = self.next_id("ADDR")
        city = city or r.choice(geo.cities(state))
        line1 = r.choice([
            f"Plot No. {r.randint(1, 299)}, Sector {r.randint(1, 40)}",
            f"Unit {r.randint(101, 909)}, {names.fused(r)} House",
            f"Shed {r.randint(1, 80)}, Phase {r.choice(['I', 'II', 'III'])}",
        ])
        self.addresses.append({
            "address_id": aid, "entity_type": entity_type, "entity_id": entity_id, "address_kind": kind,
            "address_line_1": line1, "address_line_2": names.locality(r), "city": city, "state": state,
            "state_code": geo.state_code(state),
            "postal_code": r.choice(geo.pin_prefixes(state)) + f"{r.randrange(10000):04d}",
            "country": "India", "synthetic_flag": True,
        })
        return aid, city


# ----------------------------------------------------------------- companies
def size_band(cfg, turnover):
    b = cfg["size_bands_cr"]
    if turnover < b["micro"]:
        return "micro"
    if turnover < b["small"]:
        return "small"
    if turnover < b["medium"]:
        return "medium"
    return "large"


def turnover_percentile(cfg, t):
    tc = cfg["turnover"]
    z = (math.log(t) - math.log(tc["median_cr"])) / tc["sigma"]
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def describe(company, product_categories):
    roles = []
    if company["manufacturer"]:
        roles.append("manufactures its products")
    if company["importer"]:
        roles.append("imports products or packaging")
    if company["brand_owner"]:
        roles.append("sells under its own brands")
    role_text = ", ".join(roles[:-1]) + (" and " if len(roles) > 1 else "") + roles[-1]
    cats = ", ".join(sorted(set(product_categories))[:3]).lower()
    n = len(company["states_operated"])
    return (f"{company['company_name']} is a {company['company_size']} {company['industry'].lower()} business "
            f"headquartered in {company['headquarters_state']} that {role_text}. Main lines: {cats}. "
            f"Sells in {n} state{'s' if n != 1 else ''}. (SYNTHETIC — EPRLens Demo)")


def build_company(ctx, cid, industry=None, fixed=None):
    cfg, fixed = ctx.cfg, (fixed or {})
    r = ctx.r("company", cid)
    industry = fixed.get("industry") or industry or weighted(r, cfg["industry_weights"])
    tc = cfg["turnover"]
    turnover = fixed.get("turnover_cr")
    if turnover is None:
        turnover = min(max(r.lognormvariate(math.log(tc["median_cr"]), tc["sigma"]), tc["min_cr"]), tc["max_cr"])
    turnover = round(turnover, 2)
    size = size_band(cfg, turnover)
    rp = cfg["role_probabilities"]
    manufacturer = fixed.get("manufacturer", r.random() < prob(rp["manufacturer"], industry))
    importer = fixed.get("importer", r.random() < prob(rp["importer"], industry))
    brand_owner = fixed.get("brand_owner", r.random() < prob(rp["brand_owner"], industry))
    if not (manufacturer or importer or brand_owner):
        brand_owner = True
    msme = fixed.get("msme_flag", r.random() < cfg["msme_probability"][size])
    hq = fixed.get("headquarters_state") or weighted(r, cfg["state_weights"])
    if "states_operated" in fixed:
        states = list(fixed["states_operated"])
    else:
        lo, hi = cfg["states_operated_range"][size]
        n = r.randint(lo, hi)
        states = [hq]
        pool = {k: v for k, v in cfg["state_weights"].items() if k != hq}
        while len(states) < n and pool:
            s = weighted(r, pool)
            states.append(s)
            pool.pop(s)
    status = fixed.get("registration_status")
    if status is None:
        if r.random() < cfg["epr_registered_probability"][size]:
            status = "registered"
        else:
            status = r.choice(["not_registered", "application_pending", "unknown"])
    name = fixed.get("company_name") or names.company_name(r, industry, ctx.used_names)
    ctx.used_names.add(name)
    lo_p, hi_p = arch.UNIT_PRICE[industry]
    unit_price = math.exp(r.uniform(math.log(lo_p), math.log(hi_p)))
    annual_units = int(turnover * 1e7 * r.uniform(0.6, 0.9) / unit_price)
    created = rand_date(r, "2023-01-02", "2023-03-31")
    addr_id, _ = ctx.add_address("company", cid, "hq", hq, r)
    for plant_state in fixed.get("plants", []):
        ctx.add_address("company", cid, "plant", plant_state, r)
    if not fixed and size in ("medium", "large"):
        for _ in range(r.randint(0, 2)):
            ctx.add_address("company", cid, r.choice(["plant", "warehouse"]), r.choice(states), r)
    row = {
        "company_id": cid, "company_name": name, "industry": industry, "company_size": size,
        "turnover_cr": turnover, "manufacturer": manufacturer, "importer": importer,
        "brand_owner": brand_owner, "msme_flag": msme, "states_operated": states,
        "headquarters_state": hq, "hq_address_id": addr_id,
        # separate stream so adding this field changes no other draw
        "fake_gstin": ids.fake_gstin(ctx.r("company_gstin", cid), geo.state_code(hq), "C"),
        "epr_registered": status == "registered", "registration_status": status,
        "waste_stream": "plastic_packaging", "business_description": "", "annual_units": annual_units,
        "active_products": 0, "created_at": f"{created.isoformat()}T10:00:00+05:30",
        "test_entity": False, "test_scenario": None, "synthetic_flag": True,
    }
    ctx.companies.append(row)
    return row, r


# ----------------------------------------------------------------- products & components
def add_component(ctx, product, spec, r, version=1, weight=None, recycled=None, eff_from=None, eff_to=None,
                  test=False, scenario=None):
    form = spec["form"]
    cat, conf, hsn, _ = arch.FORM_RULES[form]
    if spec["material"] not in arch.PLASTIC_MATERIALS:
        cat = "NA"  # e.g. a metal crown cap: form says rigid, but it is not plastic packaging
        hsn = {"METAL": "8309", "GLASS": "7010", "PAPER": "4821", "CARDBOARD": "4819"}.get(spec["material"], hsn)
    cid = ctx.next_id("PKGCOMP")
    if weight is None:
        lo, hi = spec["weight_g"] if isinstance(spec["weight_g"], (list, tuple)) else (spec["weight_g"],) * 2
        weight = round(r.uniform(lo, hi), 1)
    if recycled is None:
        rc = spec.get("recycled_pct", 0)
        if isinstance(rc, (list, tuple)):
            recycled = round(r.uniform(*rc)) if rc[1] > 0 else 0
        else:
            recycled = rc
    row = {
        "component_id": cid, "product_id": product["product_id"], "component_name": spec["name"],
        "component_form": form, "material": spec["material"], "synthetic_category": cat,
        "category_basis": "synthetic_convention_by_form", "category_confidence": conf,
        "legal_verification_status": "TBD",
        "plastic_epr_relevant": spec["material"] in arch.PLASTIC_MATERIALS,
        "weight_per_unit_g": weight, "recycled_content_pct": recycled, "hsn_code": hsn,
        "supplier_id": None, "evidence_reference": f"SYN-SPEC-{cid}-v{version}", "spec_version": version,
        "effective_from": (eff_from or d(product["launch_date"])).isoformat(),
        "effective_to": eff_to.isoformat() if eff_to else None,
        "test_entity": test, "test_scenario": scenario, "synthetic_flag": True,
    }
    ctx.components.append(row)
    return row


def add_versioned_component(ctx, product, spec, r, test=False, scenario=None):
    """Adds v1 (and v2 if spec has 'v2'). Returns list of rows."""
    v2 = spec.get("v2")
    if not v2:
        return [add_component(ctx, product, spec, r, test=test, scenario=scenario)]
    switch = d(v2["effective_from"])
    v1 = add_component(ctx, product, spec, r, version=1, eff_to=switch - timedelta(days=1), test=test, scenario=scenario)
    v2row = add_component(ctx, product, spec, r, version=2, weight=v2["weight_g"], recycled=v2.get("recycled_pct", 0),
                          eff_from=switch, test=test, scenario=scenario)
    return [v1, v2row]


def add_product(ctx, company, pid, name, category, unit, upc, launch, test=False, scenario=None):
    row = {
        "product_id": pid, "company_id": company["company_id"], "product_name": name,
        "product_category": category, "industry": company["industry"], "launch_date": d(launch).isoformat(),
        "selling_unit": unit, "units_per_case": upc, "active": True,
        "test_entity": test, "test_scenario": scenario, "synthetic_flag": True,
    }
    ctx.products.append(row)
    return row


def build_fixed_products(ctx, company, specs, r):
    for spec in specs:
        p = add_product(ctx, company, ctx.next_id("PROD"), spec["name"], spec["category"], spec["unit"],
                        spec["units_per_case"], spec["launch_date"])
        for cspec in spec["components"]:
            add_versioned_component(ctx, p, cspec, r)


def build_random_products(ctx, company, n, r):
    cfg = ctx.cfg
    arches = list(arch.ARCHETYPES[company["industry"]])
    r.shuffle(arches)
    brands = [names.brand(r, ctx.used_brands)]
    used = set()
    for i in range(n):
        a = arches[i] if i < len(arches) else r.choice(arches)
        name = None
        for _ in range(60):
            if len(used) > 4 * len(brands) and len(brands) < 3:
                brands.append(names.brand(r, ctx.used_brands))
            cand = f"{r.choice(brands)} {r.choice(a['desc'])} {r.choice(a['size'])}"
            if cand not in used:
                name = cand
                break
        if name is None:
            brands.append(names.brand(r, ctx.used_brands))
            name = f"{brands[-1]} {a['desc'][0]} {a['size'][0]}"
        used.add(name)
        if r.random() < 0.7:
            launch = rand_date(r, "2015-01-01", "2023-03-31")
        else:
            launch = rand_date(r, cfg["window"]["start"], "2025-12-31")
        p = add_product(ctx, company, ctx.next_id("PROD"), name, a["category"], a["unit"], r.choice(a["case"]), launch)
        for part in a["parts"]:
            spec = dict(part)
            if r.random() < cfg["spec_version_share"] and arch.FORM_RULES[part["form"]][0] != "NA":
                lo, hi = part["weight_g"]
                base = round(r.uniform(lo, hi), 1)
                spec["weight_g"] = (base, base)
                earliest = max(d(launch) + timedelta(days=180), d("2024-01-01"))
                if earliest > d("2025-12-01"):
                    add_versioned_component(ctx, p, part, r)
                    continue
                switch = rand_date(r, earliest, "2025-12-01")
                spec["v2"] = {"weight_g": round(base * r.uniform(0.80, 0.95), 1), "effective_from": switch.isoformat()}
            add_versioned_component(ctx, p, spec, r)
    company["business_description"] = describe(company, [a["category"] for a in arches[:n]])


# ----------------------------------------------------------------- suppliers
def make_supplier(ctx, sid, stype, state=None, test=False, scenario=None):
    r = ctx.r("supplier", sid)
    state = state or weighted(r, ctx.cfg["state_weights"])
    addr_id, city = ctx.add_address("supplier", sid, "hq", state, r)
    roll = r.random()
    status = "registered" if roll < 0.7 else ("unregistered" if roll < 0.9 else "unknown")
    unit = arch.SUPPLIER_TYPE_UNIT[stype]
    moq = {"pcs": r.choice([5000, 10000, 25000, 50000]), "MT": r.choice([0.5, 1, 2, 5]),
           "kg": r.choice([100, 250, 500, 1000]), "rolls": r.choice([10, 20, 50])}[unit]
    row = {
        "supplier_id": sid, "supplier_name": names.supplier_name(r, stype, ctx.used_names), "supplier_type": stype,
        "state": state, "city": city, "hq_address_id": addr_id,
        "fake_gstin": ids.fake_gstin(r, geo.state_code(state), "C"), "registration_status": status,
        "supported_materials": list(arch.SUPPLIER_TYPE_MATERIALS[stype]),
        "supported_component_forms": list(arch.SUPPLIER_TYPE_FORMS[stype]), "min_order_quantity": moq,
        "typical_unit": unit, "test_entity": test, "test_scenario": scenario, "synthetic_flag": True,
    }
    ctx.suppliers.append(row)
    return row


def supplier_type_for(form, material):
    for t in arch.FORM_RULES[form][3]:
        if material in arch.SUPPLIER_TYPE_MATERIALS[t]:
            return t
    raise ValueError(f"no supplier type for {form}/{material}")


def eligible_strict(pool, comp):
    prefs = arch.FORM_RULES[comp["component_form"]][3]
    return [s for s in pool if s["supplier_type"] in prefs and comp["material"] in s["supported_materials"]]


def eligible(pool, comp):
    """Only suppliers whose type supplies this form AND this material — no cross-type fallback."""
    return eligible_strict(pool, comp)


def build_core_suppliers(ctx, n, comps):
    pool = []
    for c in comps:
        if c["supplier_id"] or eligible_strict(pool, c):
            continue
        sid = ids.make_id("SUP", len(pool) + 1)
        pool.append(make_supplier(ctx, sid, supplier_type_for(c["component_form"], c["material"])))
    r = ctx.r("supplier_fill", "core")
    while len(pool) < n:
        sid = ids.make_id("SUP", len(pool) + 1)
        pool.append(make_supplier(ctx, sid, r.choice(sorted(arch.SUPPLIER_TYPE_MATERIALS))))
    return pool


def assign_suppliers(ctx, comps, pool, stage):
    product_company = {p["product_id"]: p["company_id"] for p in ctx.products}
    used = {}
    v1_supplier = {}
    for c in comps:
        key = (c["product_id"], c["component_name"])
        if c["supplier_id"]:
            used.setdefault(product_company[c["product_id"]], set()).add(c["supplier_id"])
            v1_supplier.setdefault(key, c["supplier_id"])
            continue
        if key in v1_supplier:
            c["supplier_id"] = v1_supplier[key]
            continue
        company = product_company[c["product_id"]]
        r = ctx.r(stage, c["component_id"])
        cands = eligible(pool, c)
        if not cands:
            raise ValueError(f"no supplier for {c['component_id']} {c['material']}")
        prefs = arch.FORM_RULES[c["component_form"]][3]
        mine = used.get(company, set())
        weights = {}
        for s in cands:
            rank = prefs.index(s["supplier_type"]) if s["supplier_type"] in prefs else len(prefs)
            weights[s["supplier_id"]] = (4.0 / (1 + 2 * rank)) * (3.0 if s["supplier_id"] in mine else 1.0)
        pick = weighted(r, weights)
        chosen = next(s for s in cands if s["supplier_id"] == pick)
        c["supplier_id"] = chosen["supplier_id"]
        v1_supplier[key] = c["supplier_id"]
        used.setdefault(company, set()).add(c["supplier_id"])


# ----------------------------------------------------------------- buyers
def make_buyer(ctx, bid, state_weights, btype=None, state=None, test=False, scenario=None):
    r = ctx.r("buyer", bid)
    btype = btype or weighted(r, BUYER_TYPE_WEIGHTS)
    state = state or weighted(r, state_weights)
    addr_id, city = ctx.add_address("buyer", bid, "hq", state, r)
    gst_registered = r.random() < BUYER_GST_P[btype]
    gstin = ids.fake_gstin(r, geo.state_code(state), r.choice("CF")) if gst_registered else None
    size = r.choice(["micro", "small"]) if btype == "retailer" else r.choice(["small", "medium", "medium", "large"])
    row = {
        "buyer_id": bid, "buyer_name": names.buyer_name(r, btype, ctx.used_names), "buyer_type": btype,
        "state": state, "city": city, "hq_address_id": addr_id, "fake_gstin": gstin,
        "gst_registered": gst_registered, "epr_registered": gst_registered and r.random() < BUYER_EPR_P[btype],
        "company_size": size, "test_entity": test, "test_scenario": scenario, "synthetic_flag": True,
    }
    ctx.buyers.append(row)
    return row


def link_buyers(ctx, company, pool, k):
    r = ctx.r("sells_to", company["company_id"])
    states = set(company["states_operated"])
    local = [b for b in pool if b["state"] in states and not b["test_entity"]]
    other = [b for b in pool if b["state"] not in states and not b["test_entity"]]
    r.shuffle(local)
    r.shuffle(other)
    chosen = (local + other)[:k]
    ctx.company_buyers[company["company_id"]] = sorted(b["buyer_id"] for b in chosen)


# ----------------------------------------------------------------- recyclers
def make_recycler(ctx, rid, ptype, seq, registered=True, claimed=True, state=None, test=False, scenario=None):
    r = ctx.r("recycler", rid)
    state = state or weighted(r, ctx.cfg["state_weights"])
    addr_id, city = ctx.add_address("recycler", rid, "hq", state, r)
    reg_no = ids.recycler_registration_number(geo.state_abbrev(state), r.choice([2022, 2023, 2024]), seq) \
        if (registered or claimed) else None
    cap = round(ctx.cfg["recyclers"]["capacity_kg_median"] * math.exp(r.gauss(0, 0.8)), -3)
    row = {
        "recycler_id": rid, "recycler_name": names.recycler_name(r, ctx.used_names), "state": state, "city": city,
        "hq_address_id": addr_id, "fake_gstin": ids.fake_gstin(r, geo.state_code(state), "C"),
        "registered": registered, "fake_registration_number": reg_no, "processing_type": ptype,
        "supported_materials": list(PROCESSING_MATERIALS[ptype]), "monthly_capacity_kg": max(cap, 5000.0),
        "test_entity": test, "test_scenario": scenario, "synthetic_flag": True,
    }
    ctx.recyclers.append(row)
    return row


def company_plastic_materials(ctx, company_id):
    pids = {p["product_id"] for p in ctx.products if p["company_id"] == company_id}
    return sorted({c["material"] for c in ctx.components if c["product_id"] in pids and c["plastic_epr_relevant"]})


def link_recyclers(ctx, company, pool):
    r = ctx.r("uses_recycler", company["company_id"])
    chosen = []
    for m in company_plastic_materials(ctx, company["company_id"]):
        if any(m in rc["supported_materials"] for rc in chosen):
            continue
        cands = [rc for rc in pool if rc["registered"] and not rc["test_entity"] and m in rc["supported_materials"]]
        if cands:
            same_state = [rc for rc in cands if rc["state"] in company["states_operated"]]
            chosen.append(r.choice(same_state or cands))
    ctx.company_recyclers[company["company_id"]] = sorted({rc["recycler_id"] for rc in chosen})


# ----------------------------------------------------------------- users
def make_user(ctx, n, role, company_id, scope, role_counts):
    role_counts[role] = role_counts.get(role, 0) + 1
    k = role_counts[role]
    ctx.users.append({
        "user_id": ids.make_id("USR", n),
        "display_name": f"Demo {role.replace('_', ' ').title()} {k:02d}",
        "fake_email": f"demo.{ROLE_SHORT[role]}{k:02d}@example.com",
        "role": role, "company_id": company_id, "company_scope": scope,
        "permissions": ROLE_PERMISSIONS[role], "fixture_only": True, "synthetic_flag": True,
    })


# ----------------------------------------------------------------- relationships
def emit_relationships(ctx, company_ids):
    """Appends relationship rows for the given companies in a deterministic order."""
    rows = []
    comps_by_product = {}
    for c in ctx.components:
        comps_by_product.setdefault(c["product_id"], []).append(c)
    supplier_ids = {s["supplier_id"] for s in ctx.suppliers}
    for cid in company_ids:
        company = next(c for c in ctx.companies if c["company_id"] == cid)
        products = [p for p in ctx.products if p["company_id"] == cid]
        start_window = ctx.cfg["window"]["start"]
        # BUYS_FROM (earliest component start per supplier)
        first = {}
        for p in products:
            for c in comps_by_product.get(p["product_id"], []):
                first[c["supplier_id"]] = min(first.get(c["supplier_id"], c["effective_from"]), c["effective_from"])
        for sid in sorted(first):
            rows.append(("company", cid, "BUYS_FROM", "supplier", sid, first[sid], None))
        for (ecid, sid, s, e) in ctx.extra_buys_from:
            if ecid == cid and sid in supplier_ids:
                rows.append(("company", cid, "BUYS_FROM", "supplier", sid, s, e))
        for bid in ctx.company_buyers.get(cid, []):
            rows.append(("company", cid, "SELLS_TO", "buyer", bid, start_window, None))
        for rid in ctx.company_recyclers.get(cid, []):
            rows.append(("company", cid, "USES_RECYCLER", "recycler", rid, start_window, None))
        for p in products:
            end = None if p["active"] else p.get("_discontinued")
            rows.append(("company", cid, "OWNS_PRODUCT", "product", p["product_id"], p["launch_date"], end))
        for p in products:
            for c in comps_by_product.get(p["product_id"], []):
                rows.append(("product", p["product_id"], "USES_COMPONENT", "component", c["component_id"],
                             c["effective_from"], c["effective_to"]))
        for p in products:
            for c in comps_by_product.get(p["product_id"], []):
                rows.append(("component", c["component_id"], "SUPPLIED_BY", "supplier", c["supplier_id"],
                             c["effective_from"], c["effective_to"]))
                for (ccid, sid, s, e) in ctx.extra_supplied_by:
                    if ccid == c["component_id"]:
                        rows.append(("component", ccid, "SUPPLIED_BY", "supplier", sid, s, e))
    for st, sid, rt, tt, tid, s, e in rows:
        ctx.relationships.append({
            "relationship_id": ctx.next_id("REL"), "source_entity_type": st, "source_entity_id": sid,
            "relationship_type": rt, "target_entity_type": tt, "target_entity_id": tid,
            "start_date": s, "end_date": e, "active": e is None, "synthetic_flag": True,
        })


# ----------------------------------------------------------------- core pack
def build_core(ctx):
    cfg = ctx.cfg
    demo = cfg["demo_company"]
    company, r = build_company(ctx, demo["company_id"], fixed=demo)
    build_fixed_products(ctx, company, demo["products"], r)
    company["business_description"] = (
        "EcoFizz Beverages Pvt Ltd is a FICTIONAL Delhi-based beverage manufacturer and brand owner selling "
        "carbonated soft drinks and packaged drinking water in PET bottles, plus one glass-bottle soda, across "
        "five north-Indian states. Bottles and caps are bought from packaging suppliers; outer cartons are "
        "corrugated board. (SYNTHETIC — EPRLens Demo)")

    for a in cfg["anchor_companies"]:
        comp, rr = build_company(ctx, a["company_id"], industry=a["industry"])
        for role in ("manufacturer", "importer", "brand_owner"):
            if role in a:
                comp[role] = a[role]
        build_random_products(ctx, comp, a["n_products"], rr)

    # PROD_TEST_001 — stale-weight scenario
    t = cfg["test_entities"]["PROD_TEST_001"]
    owner = next(c for c in ctx.companies if c["company_id"] == t["company_id"])
    brand = next(p for p in ctx.products if p["company_id"] == owner["company_id"])["product_name"].split()[0]
    tr = ctx.r("test_entity", "PROD_TEST_001")
    tp = add_product(ctx, owner, ids.test_id("PROD", 1), f"{brand} {t['name_suffix']}", "Savoury snacks", "pack", 48,
                     t["launch_date"], test=True, scenario=t["scenario"])
    for cspec in t["components"]:
        add_versioned_component(ctx, tp, cspec, tr, test=True, scenario=t["scenario"])

    # Inactive product example
    disc = cfg["inactive_examples"]["discontinued_product_company"]
    last = [p for p in ctx.products if p["company_id"] == disc and not p["test_entity"]][-1]
    last["active"] = False
    last["_discontinued"] = "2025-06-30"

    core_company_ids = [c["company_id"] for c in ctx.companies]
    n_sup = cfg["packs"]["test"]["suppliers"]

    # SUP_TEST_002 is the primary cap supplier for COMP_0003 (PP)
    te = cfg["test_entities"]
    st2 = make_supplier(ctx, ids.test_id("SUP", 2), te["SUP_TEST_002"]["supplier_type"], te["SUP_TEST_002"]["state"],
                        test=True, scenario=te["SUP_TEST_002"]["scenario"])
    st2["supported_materials"] = ["PP"]
    pids3 = {p["product_id"] for p in ctx.products if p["company_id"] == te["SUP_TEST_002"]["primary_for"]}
    for c in ctx.components:
        if c["product_id"] in pids3 and c["material"] == "PP" and c["component_form"] in ("cap", "closure"):
            c["supplier_id"] = st2["supplier_id"]
    core_pool = build_core_suppliers(ctx, n_sup, ctx.components)
    assign_suppliers(ctx, ctx.components, core_pool, "assign_core")

    st1 = make_supplier(ctx, ids.test_id("SUP", 1), te["SUP_TEST_001"]["supplier_type"], te["SUP_TEST_001"]["state"],
                        test=True, scenario=te["SUP_TEST_001"]["scenario"])
    demo_pet = [c for c in ctx.components if c["product_id"] == "PROD_000001" and c["material"] == "PET"]
    for c in demo_pet:
        ctx.extra_supplied_by.append((c["component_id"], st1["supplier_id"], c["effective_from"], c["effective_to"]))
    ctx.extra_buys_from.append((te["SUP_TEST_001"]["secondary_for"], st1["supplier_id"], cfg["window"]["start"], None))

    # Ended supplier relationship example
    ended_for = cfg["inactive_examples"]["ended_supplier_relationship_company"]
    current = {c["supplier_id"] for c in ctx.components
               if c["product_id"] in {p["product_id"] for p in ctx.products if p["company_id"] == ended_for}}
    spare = [s for s in core_pool if s["supplier_id"] not in current]
    if spare:
        ctx.extra_buys_from.append((ended_for, spare[0]["supplier_id"], cfg["window"]["start"], "2024-12-31"))

    # Buyers
    core_states = {}
    for c in ctx.companies:
        for s in c["states_operated"]:
            core_states[s] = core_states.get(s, 0) + 1
    for i in range(1, cfg["packs"]["test"]["buyers"] + 1):
        make_buyer(ctx, ids.make_id("BUY", i), core_states)
    bt = make_buyer(ctx, ids.test_id("BUY", 1), core_states, btype=te["BUY_TEST_001"]["buyer_type"],
                    state=te["BUY_TEST_001"]["state"], test=True, scenario=te["BUY_TEST_001"]["scenario"])
    bt["fake_gstin"] = bt["fake_gstin"][:14]  # deliberately incomplete
    bt["epr_registered"] = False
    for c in ctx.companies:
        k = ctx.r("n_buyers", c["company_id"]).randint(3, 5)
        link_buyers(ctx, c, ctx.buyers, k)
    ctx.company_buyers[te["BUY_TEST_001"]["buyer_of"]].append(bt["buyer_id"])

    # Recyclers (core all registered) + REC_TEST_001
    needed = sorted({m for cid in core_company_ids for m in company_plastic_materials(ctx, cid)})
    pool = []
    for m in needed:
        if any(m in rc["supported_materials"] for rc in pool):
            continue
        ptype = PREFERRED_PROCESSING.get(m, "mixed-plastic processing")
        pool.append(make_recycler(ctx, ids.make_id("REC", len(pool) + 1), ptype, len(pool) + 1))
    fill = ctx.r("recycler_fill", "core")
    while len(pool) < cfg["packs"]["test"]["recyclers"]:
        ptype = fill.choice(["HDPE recycling", "PP recycling", "LDPE recycling", "PET recycling"])
        pool.append(make_recycler(ctx, ids.make_id("REC", len(pool) + 1), ptype, len(pool) + 1))
    rt = te["REC_TEST_001"]
    rtest = make_recycler(ctx, ids.test_id("REC", 1), "mixed-plastic processing", 901, registered=False, claimed=True,
                          state=rt["state"], test=True, scenario=rt["scenario"])
    for c in ctx.companies:
        link_recyclers(ctx, c, ctx.recyclers)
    ctx.company_recyclers[rt["used_by"]].append(rtest["recycler_id"])

    # Users
    role_counts = {}
    for n, role in enumerate(cfg["test_user_roles_core"], start=1):
        if role == "consultant":
            make_user(ctx, n, role, None, core_company_ids, role_counts)
        else:
            home = "COMP_0002" if role == "compliance_manager" else "COMP_0001"
            make_user(ctx, n, role, home, [home], role_counts)
    ctx.role_counts = role_counts

    finalize_companies(ctx, core_company_ids)
    emit_relationships(ctx, core_company_ids)
    return core_company_ids


# ----------------------------------------------------------------- extension (full mode)
def build_extension(ctx, pack):
    cfg = ctx.cfg
    test = cfg["packs"]["test"]
    ext_ids = []
    for i in range(test["companies"] + 1, pack["companies"] + 1):
        cid = ids.make_id("COMP", i)
        comp, r = build_company(ctx, cid)
        q = turnover_percentile(cfg, comp["turnover_cr"])
        lo, hi = cfg["products_per_company"]["min"], cfg["products_per_company"]["max"]
        n = min(max(lo + round((hi - lo) * q) + r.randint(-2, 2), lo), hi)
        build_random_products(ctx, comp, n, r)
        ext_ids.append(cid)

    types = sorted(arch.SUPPLIER_TYPE_MATERIALS)
    tr = ctx.r("supplier_types", "ext")
    for i in range(test["suppliers"] + 1, pack["suppliers"] + 1):
        k = i - test["suppliers"] - 1
        stype = types[k % len(types)] if k < 5 * len(types) else tr.choice(types)
        make_supplier(ctx, ids.make_id("SUP", i), stype)
    pool = [s for s in ctx.suppliers if not s["test_entity"]]
    ext_comps = [c for c in ctx.components if c["supplier_id"] is None]
    assign_suppliers(ctx, ext_comps, pool, "assign_ext")

    for i in range(test["buyers"] + 1, pack["buyers"] + 1):
        make_buyer(ctx, ids.make_id("BUY", i), cfg["state_weights"])
    size_buyers = {"micro": (2, 4), "small": (2, 5), "medium": (4, 8), "large": (6, 15)}
    for cid in ext_ids:
        c = next(x for x in ctx.companies if x["company_id"] == cid)
        k = ctx.r("n_buyers", cid).randint(*size_buyers[c["company_size"]])
        link_buyers(ctx, c, ctx.buyers, k)

    n_unreg = round(cfg["recyclers"]["unregistered_share"] * pack["recyclers"])
    rr = ctx.r("recycler_types", "ext")
    ptypes = sorted(PROCESSING_MATERIALS)
    ext_rec_ids = list(range(test["recyclers"] + 1, pack["recyclers"] + 1))
    unreg = set(rr.sample(ext_rec_ids, min(n_unreg, len(ext_rec_ids))))
    for i in ext_rec_ids:
        k = i - test["recyclers"] - 1
        ptype = ptypes[k % len(ptypes)] if k < 2 * len(ptypes) else rr.choice(ptypes)
        is_reg = i not in unreg
        make_recycler(ctx, ids.make_id("REC", i), ptype, i, registered=is_reg,
                      claimed=is_reg or rr.random() < 0.5)
    for cid in ext_ids:
        c = next(x for x in ctx.companies if x["company_id"] == cid)
        link_recyclers(ctx, c, ctx.recyclers)
        r = ctx.r("unreg_recycler", cid)
        if r.random() < 0.1:
            mats = set(company_plastic_materials(ctx, cid))
            bad = [x for x in ctx.recyclers if not x["registered"] and not x["test_entity"]
                   and mats & set(x["supported_materials"])]
            if bad:
                ctx.company_recyclers[cid].append(r.choice(bad)["recycler_id"])

    n_core_users = len(ctx.users)
    for j in range(pack["test_users"] - n_core_users):
        role = FULL_ROLE_CYCLE[j % len(FULL_ROLE_CYCLE)]
        home = ext_ids[j % len(ext_ids)] if ext_ids else "COMP_0001"
        if role == "consultant":
            make_user(ctx, n_core_users + j + 1, role, None, ext_ids[:10], ctx.role_counts)
        else:
            make_user(ctx, n_core_users + j + 1, role, home, [home], ctx.role_counts)

    finalize_companies(ctx, ext_ids)
    emit_relationships(ctx, ext_ids)


def finalize_companies(ctx, company_ids):
    for c in ctx.companies:
        if c["company_id"] in company_ids:
            c["active_products"] = sum(1 for p in ctx.products if p["company_id"] == c["company_id"] and p["active"])


def generate(cfg, pack_name="test"):
    ctx = Ctx(cfg)
    build_core(ctx)
    if pack_name == "full":
        build_extension(ctx, cfg["packs"]["full"])
    for p in ctx.products:
        p.pop("_discontinued", None)
    order = lambda key: (lambda row: ("_TEST_" in row[key], row[key]))  # noqa: E731
    ctx.suppliers.sort(key=order("supplier_id"))
    ctx.buyers.sort(key=order("buyer_id"))
    ctx.recyclers.sort(key=order("recycler_id"))
    ctx.products.sort(key=order("product_id"))
    return ctx
