"""Single source of field definitions for every synthetic table.

SYNTHETIC — EPRLens Demo. Status: PROPOSED (see docs/DECISIONS-REQUIRED.md).

Each field is a tuple: (name, type, required, description, extras)
  type: string | integer | number | boolean | date | month | datetime | array
  extras keys:
    prov      H = handbook-supported concept, E = engineering assumption,
              M = internal metadata, GT = ground-truth only, P = printed on invoice
    pattern   regex for strings
    enum      allowed values
    nullable  value may be null (empty string in CSV)
    fk        "table.column" foreign key
    minimum / maximum
    items     item type for arrays (CSV encodes arrays as "|"-joined strings)

`build_schemas.py` turns this into JSON Schema files.
"""

SCHEMA_VERSION = "0.2.0"

ID = {
    "company": r"^COMP_\d{4}$",
    "supplier": r"^SUP_(\d{4}|TEST_\d{3})$",
    "buyer": r"^BUY_(\d{4}|TEST_\d{3})$",
    "recycler": r"^REC_(\d{4}|TEST_\d{3})$",
    "product": r"^PROD_(\d{6}|TEST_\d{3})$",
    "component": r"^PKGCOMP_\d{6}$",
    "address": r"^ADDR_\d{6}$",
    "relationship": r"^REL_\d{6}$",
    "user": r"^USR_\d{4}$",
    "transaction": r"^TXN_\d{8}$",
    "event": r"^MEV_\d{9}$",
    "invoice": r"^INV_\d{8}$",
    "invoice_line": r"^INVL_\d{9}$",
    "document": r"^DOC_\d{6}$",
    "recycling": r"^RCY_\d{7}$",
    "scenario": r"^SCN_\d{6}$",
    "anomaly": r"^ANM_\d{7}$",
    "description": r"^DESC_\d{4}$",
}
PARTY = r"^(COMP_\d{4}|SUP_(\d{4}|TEST_\d{3})|BUY_(\d{4}|TEST_\d{3})|REC_(\d{4}|TEST_\d{3}))$"
GSTIN_FORMAT = r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"

INDUSTRIES = [
    "Beverages", "FMCG", "Cosmetics", "Personal Care", "Food", "Pharmaceuticals",
    "Electronics", "Appliances", "Automotive", "Retail", "E-commerce",
    "Household Products", "Industrial Goods",
]
MATERIALS = [
    "PET", "HDPE", "LDPE", "LLDPE", "PP", "PVC", "PS", "MLP", "COMPOSTABLE",
    "PAPER", "CARDBOARD", "GLASS", "METAL", "BATTERY", "OTHER",
]
CATEGORIES = ["CAT_I", "CAT_II", "CAT_III", "CAT_IV", "NA", "UNKNOWN"]
SUPPLIER_TYPES = [
    "PET bottle manufacturer", "plastic resin supplier", "flexible packaging supplier", "cap supplier",
    "closure supplier", "label supplier", "shrink-film supplier", "pouch supplier", "carton supplier",
    "packaging converter", "raw-material supplier", "component supplier",
]
BUYER_TYPES = [
    "distributor", "wholesaler", "retailer", "supermarket", "e-commerce seller",
    "institutional buyer", "manufacturing customer",
]
PROCESSING_TYPES = [
    "PET recycling", "HDPE recycling", "LDPE recycling", "PP recycling",
    "mixed-plastic processing", "MLP processing",
    "industrial composting",  # handbook p.8 lists composting among PWP activities; needed for CAT_IV (DS-23)
]
ROLES = [
    "company_admin", "sustainability_manager", "compliance_manager", "finance_user",
    "operations_user", "consultant", "demo_user",
]
REL_TYPES = ["BUYS_FROM", "SELLS_TO", "USES_RECYCLER", "OWNS_PRODUCT", "USES_COMPONENT", "SUPPLIED_BY"]
ENTITY_TYPES = ["company", "supplier", "buyer", "recycler", "product", "component"]
INVOICE_TYPES = [
    "PKG_PURCHASE", "FG_SALES", "RECYCLER_PROCESSING", "WASTE_PROCUREMENT", "CREDIT_NOTE",
    "RETURN", "IMPORT_COMMERCIAL", "PKG_COMPONENT", "MULTI_MATERIAL", "RECYCLING_SERVICE",
]
UNITS = ["kg", "g", "MT", "pcs", "cartons", "bottles", "bags", "rolls"]
ANOMALY_TYPES = [f"AN{n:02d}" for n in range(1, 21)]
EVENT_TYPES = [
    "OPENING_BALANCE", "PURCHASED", "PRODUCED", "CONSUMED", "WRITTEN_OFF", "PLACED_ON_MARKET",
    "RETURNED", "EXPORTED", "WASTE_GENERATED_PROXY", "COLLECTED", "RECYCLED",
    "CREDITS_DOCUMENTED", "CLOSING_BALANCE",
]
FORMS = [
    "bottle", "jar", "cap", "closure", "tray", "drum", "tub", "pail", "preform", "eps_block",
    "blister", "film", "shrink_wrap", "stretch_wrap", "label_film", "bag", "mailer", "liner",
    "pouch_mono", "sachet_mono", "pouch_laminate", "sachet_laminate", "laminated_tube",
    "compostable_bag", "compostable_mailer", "carton", "box", "paper_label", "glass_bottle",
    "can", "void_fill",
]


def f(name, type_, required, description, **extras):
    return (name, type_, required, description, extras)


SYN = f("synthetic_flag", "boolean", True, "Always true. SYNTHETIC — EPRLens Demo.", prov="M", enum=[True])
TEST_ENTITY = f("test_entity", "boolean", True, "True for deliberately problematic *_TEST_* entities (DS-22/23).", prov="M")
TEST_SCENARIO = f("test_scenario", "string", False, "Scenario code (see docs/dummy-entities.md), null for normal entities.",
                  prov="M", nullable=True, pattern=r"^TS\d{2}_[A-Z0-9_]+$")
LEGAL_STATUS = ["TBD", "handbook_named_only", "officially_verified"]

TABLES = {
    # ------------------------------------------------------------------ masters
    "companies": {
        "title": "Company master",
        "primary_key": "company_id",
        "fields": [
            f("company_id", "string", True, "Company id", prov="M", pattern=ID["company"]),
            f("company_name", "string", True, "Fictional company name", prov="E"),
            f("industry", "string", True, "Industry", prov="E", enum=INDUSTRIES),
            f("company_size", "string", True, "Illustrative turnover band (not official MSME criteria)", prov="E",
              enum=["micro", "small", "medium", "large"]),
            f("turnover_cr", "number", True, "Annual turnover, ₹ crore (synthetic)", prov="E", minimum=0),
            f("manufacturer", "boolean", True, "Business fact: manufactures products/packaging", prov="H"),
            f("importer", "boolean", True, "Business fact: imports products or packaging", prov="H"),
            f("brand_owner", "boolean", True, "Business fact: sells under own brand (registration need is a separate rule, DS-14)", prov="H"),
            f("msme_flag", "boolean", True, "Synthetic MSME attribute (not derived from official criteria)", prov="E"),
            f("states_operated", "array", True, "States where the company sells", prov="H", items="string"),
            f("headquarters_state", "string", True, "HQ state", prov="E"),
            f("hq_address_id", "string", True, "HQ address", prov="M", pattern=ID["address"], fk="addresses.address_id"),
            f("epr_registered", "boolean", True, "Declared EPR registration status (synthetic)", prov="H"),
            f("registration_status", "string", True, "Declared registration status", prov="H",
              enum=["registered", "application_pending", "not_registered", "unknown"]),
            f("waste_stream", "string", True, "EPR waste stream in scope", prov="H", enum=["plastic_packaging"]),
            f("business_description", "string", True, "Short synthetic description", prov="E"),
            f("annual_units", "integer", True, "Planned annual finished units (synthetic)", prov="E", minimum=0),
            f("active_products", "integer", True, "Count of active products", prov="M", minimum=0),
            f("created_at", "datetime", True, "Synthetic onboarding timestamp (deterministic, not generation time)", prov="M"),
            TEST_ENTITY, TEST_SCENARIO, SYN,
        ],
    },
    "products": {
        "title": "Product master",
        "primary_key": "product_id",
        "fields": [
            f("product_id", "string", True, "Product id", prov="M", pattern=ID["product"]),
            f("company_id", "string", True, "Owner company", prov="M", pattern=ID["company"], fk="companies.company_id"),
            f("product_name", "string", True, "Fictional product name", prov="E"),
            f("product_category", "string", True, "Product category", prov="E"),
            f("industry", "string", True, "Industry (denormalised)", prov="E", enum=INDUSTRIES),
            f("launch_date", "date", True, "Launch date", prov="E"),
            f("selling_unit", "string", True, "Unit in which the product is sold", prov="E"),
            f("units_per_case", "integer", True, "Units per shipping case", prov="E", minimum=1),
            f("active", "boolean", True, "False = discontinued", prov="M"),
            TEST_ENTITY, TEST_SCENARIO, SYN,
        ],
    },
    "packaging_components": {
        "title": "Packaging component master (one row per spec version)",
        "primary_key": "component_id",
        "fields": [
            f("component_id", "string", True, "Component id", prov="M", pattern=ID["component"]),
            f("product_id", "string", True, "Product", prov="M", pattern=ID["product"], fk="products.product_id"),
            f("component_name", "string", True, "e.g. 'PET bottle'", prov="E"),
            f("component_form", "string", True, "Physical form used for category declaration", prov="E", enum=FORMS),
            f("material", "string", True, "Material code", prov="E", enum=MATERIALS),
            f("synthetic_category", "string", True,
              "Synthetic modelling convention by component form (DS-09). NOT a legal classification.", prov="E", enum=CATEGORIES),
            f("category_basis", "string", True, "How the synthetic category was set", prov="M", enum=["synthetic_convention_by_form"]),
            f("category_confidence", "string", True, "declared | ambiguous", prov="E", enum=["declared", "ambiguous"]),
            f("legal_verification_status", "string", True, "Legal/official verification of the category (TBD until verified)",
              prov="M", enum=LEGAL_STATUS),
            f("plastic_epr_relevant", "boolean", True, "Plastic packaging per handbook scope (DS-02)", prov="H"),
            f("weight_per_unit_g", "number", True, "Grams per finished unit", prov="E", minimum=0),
            f("recycled_content_pct", "number", True, "Recycled content %", prov="H", minimum=0, maximum=100),
            f("hsn_code", "string", True, "Illustrative HSN heading (TBD verify)", prov="E", pattern=r"^\d{4,8}$"),
            f("supplier_id", "string", True, "Primary supplier", prov="M", pattern=ID["supplier"], fk="suppliers.supplier_id"),
            f("evidence_reference", "string", True, "Synthetic spec-sheet reference", prov="M"),
            f("spec_version", "integer", True, "Spec version (1, 2, …)", prov="M", minimum=1),
            f("effective_from", "date", True, "Weight valid from", prov="E"),
            f("effective_to", "date", False, "Weight valid to (null = current)", prov="E", nullable=True),
            TEST_ENTITY, TEST_SCENARIO, SYN,
        ],
    },
    "suppliers": {
        "title": "Supplier master",
        "primary_key": "supplier_id",
        "fields": [
            f("supplier_id", "string", True, "Supplier id", prov="M", pattern=ID["supplier"]),
            f("supplier_name", "string", True, "Fictional name", prov="E"),
            f("supplier_type", "string", True, "Type", prov="E", enum=SUPPLIER_TYPES),
            f("state", "string", True, "State", prov="E"),
            f("city", "string", True, "City", prov="E"),
            f("hq_address_id", "string", True, "Address", prov="M", pattern=ID["address"], fk="addresses.address_id"),
            f("fake_gstin", "string", True, "GSTIN-like, deliberately invalid checksum", prov="P", pattern=GSTIN_FORMAT),
            f("registration_status", "string", True, "Declared EPR registration of the vendor (handbook p.42)", prov="H",
              enum=["registered", "unregistered", "unknown"]),
            f("supported_materials", "array", True, "Materials supplied", prov="E", items="string"),
            f("supported_component_forms", "array", True, "Component forms supplied (empty for resin/raw-material suppliers)",
              prov="E", items="string"),
            f("min_order_quantity", "number", True, "Minimum order quantity in typical_unit", prov="E", minimum=0),
            f("typical_unit", "string", True, "Typical invoicing unit", prov="E", enum=UNITS),
            TEST_ENTITY, TEST_SCENARIO, SYN,
        ],
    },
    "buyers": {
        "title": "Customer / buyer master",
        "primary_key": "buyer_id",
        "fields": [
            f("buyer_id", "string", True, "Buyer id", prov="M", pattern=ID["buyer"]),
            f("buyer_name", "string", True, "Fictional name", prov="E"),
            f("buyer_type", "string", True, "Type", prov="E", enum=BUYER_TYPES),
            f("state", "string", True, "State", prov="E"),
            f("city", "string", True, "City", prov="E"),
            f("hq_address_id", "string", True, "Address", prov="M", pattern=ID["address"], fk="addresses.address_id"),
            f("fake_gstin", "string", False, "GSTIN-like; null if not GST-registered; BUY_TEST_001 deliberately malformed", prov="P", nullable=True),
            f("gst_registered", "boolean", True, "GST-registered (kept separate from epr_registered)", prov="E"),
            f("epr_registered", "boolean", True, "Declared EPR registration — drives liability shift (handbook p.42, DS-12)", prov="H"),
            f("company_size", "string", True, "Size band", prov="E", enum=["micro", "small", "medium", "large"]),
            TEST_ENTITY, TEST_SCENARIO, SYN,
        ],
    },
    "recyclers": {
        "title": "Recycler (plastic waste processor) master",
        "primary_key": "recycler_id",
        "fields": [
            f("recycler_id", "string", True, "Recycler id", prov="M", pattern=ID["recycler"]),
            f("recycler_name", "string", True, "Fictional name", prov="E"),
            f("state", "string", True, "State", prov="E"),
            f("city", "string", True, "City", prov="E"),
            f("hq_address_id", "string", True, "Address", prov="M", pattern=ID["address"], fk="addresses.address_id"),
            f("fake_gstin", "string", True, "GSTIN-like, invalid checksum", prov="P", pattern=GSTIN_FORMAT),
            f("registered", "boolean", True, "Registered in the synthetic world (unregistered ones exist for AN13)", prov="H"),
            f("fake_registration_number", "string", False, "Fictional SYN-PWP number; does NOT represent a CPCB authorization. For unregistered recyclers it is a *claimed* number", prov="E",
              nullable=True, pattern=r"^SYN-PWP-[A-Z]{2}-\d{4}-\d{4}$"),
            f("processing_type", "string", True, "Processing type", prov="H", enum=PROCESSING_TYPES),
            f("supported_materials", "array", True, "Materials accepted", prov="E", items="string"),
            f("monthly_capacity_kg", "number", True, "Illustrative capacity", prov="E", minimum=0),
            TEST_ENTITY, TEST_SCENARIO, SYN,
        ],
    },
    "addresses": {
        "title": "Fictional address master",
        "primary_key": "address_id",
        "fields": [
            f("address_id", "string", True, "Address id", prov="M", pattern=ID["address"]),
            f("entity_type", "string", True, "Owner type", prov="M", enum=["company", "supplier", "buyer", "recycler"]),
            f("entity_id", "string", True, "Owner id", prov="M", pattern=PARTY),
            f("address_kind", "string", True, "hq | plant | warehouse", prov="M", enum=["hq", "plant", "warehouse"]),
            f("address_line_1", "string", True, "Fictional plot/building", prov="E"),
            f("address_line_2", "string", True, "Fictional locality", prov="E"),
            f("city", "string", True, "City (real name, for tax logic)", prov="E"),
            f("state", "string", True, "State", prov="E"),
            f("state_code", "string", True, "GST state code (verify)", prov="E", pattern=r"^\d{2}$"),
            f("postal_code", "string", True, "6-digit PIN-like value, region-consistent first digit (DS-17)", prov="E", pattern=r"^[1-8]\d{5}$"),
            f("country", "string", True, "Country", prov="E", enum=["India"]),
            SYN,
        ],
    },
    "entity_relationships": {
        "title": "Entity relationships",
        "primary_key": "relationship_id",
        "fields": [
            f("relationship_id", "string", True, "Id", prov="M", pattern=ID["relationship"]),
            f("source_entity_type", "string", True, "Source type", prov="M", enum=ENTITY_TYPES),
            f("source_entity_id", "string", True, "Source id", prov="M"),
            f("relationship_type", "string", True, "Type", prov="M", enum=REL_TYPES),
            f("target_entity_type", "string", True, "Target type", prov="M", enum=ENTITY_TYPES),
            f("target_entity_id", "string", True, "Target id", prov="M"),
            f("start_date", "date", True, "Start", prov="E"),
            f("end_date", "date", False, "End (null = open)", prov="E", nullable=True),
            f("active", "boolean", True, "False if ended", prov="M"),
            SYN,
        ],
    },
    "test_users": {
        "title": "Test user / account fixtures (no passwords)",
        "primary_key": "user_id",
        "fields": [
            f("user_id", "string", True, "Id", prov="M", pattern=ID["user"]),
            f("display_name", "string", True, "Generic role-based placeholder", prov="M"),
            f("fake_email", "string", True, "@example.com only", prov="M", pattern=r"^[a-z0-9.]+@example\.com$"),
            f("role", "string", True, "Role (fixture only; D034 pending)", prov="M", enum=ROLES),
            f("company_id", "string", False, "Home company; null for consultant", prov="M", nullable=True,
              pattern=ID["company"], fk="companies.company_id"),
            f("company_scope", "array", True, "Companies the user may access", prov="M", items="string"),
            f("permissions", "array", True, "Fixture permission strings (not a production authorization model)", prov="M", items="string"),
            f("fixture_only", "boolean", True, "Always true: test fixture, not production auth (DS-25)", prov="M", enum=[True]),
            SYN,
        ],
    },
    # ------------------------------------------------------------- activity
    "transactions": {
        "title": "Internal transaction records (CSV upload format)",
        "primary_key": "transaction_id",
        "fields": [
            f("transaction_id", "string", True, "Id", prov="M", pattern=ID["transaction"]),
            f("company_id", "string", True, "Company", prov="M", pattern=ID["company"], fk="companies.company_id"),
            f("product_id", "string", False, "Product (sales)", prov="M", nullable=True, pattern=ID["product"], fk="products.product_id"),
            f("component_id", "string", False, "Component (purchases)", prov="M", nullable=True, pattern=ID["component"], fk="packaging_components.component_id"),
            f("date", "date", True, "Date", prov="M"),
            f("transaction_type", "string", True, "Type", prov="E",
              enum=["sale", "purchase", "import", "return", "export_sale", "credit_adjustment"]),
            f("units", "integer", False, "Units / pieces", prov="E", nullable=True, minimum=0),
            f("state", "string", True, "State of sale/receipt (state-wise reporting, handbook p.42)", prov="H"),
            f("buyer_id", "string", False, "Buyer", prov="M", nullable=True, pattern=ID["buyer"], fk="buyers.buyer_id"),
            f("buyer_epr_registered", "boolean", False, "Liability-shift input (p.42)", prov="H", nullable=True),
            f("supplier_id", "string", False, "Supplier", prov="M", nullable=True, pattern=ID["supplier"], fk="suppliers.supplier_id"),
            f("raw_quantity", "number", True, "As recorded", prov="E"),
            f("raw_unit", "string", True, "As recorded", prov="E", enum=UNITS),
            f("normalized_quantity_kg", "number", False, "Packaging kg; null if unconvertible", prov="E", nullable=True),
            f("plastic_kg", "number", False, "Plastic-relevant subset", prov="E", nullable=True),
            f("invoice_id", "string", False, "Linked invoice", prov="M", nullable=True, pattern=ID["invoice"], fk="invoices.invoice_id"),
            f("status", "string", True, "posted | cancelled", prov="E", enum=["posted", "cancelled"]),
            SYN,
        ],
    },
    "material_events": {
        "title": "Material-flow ledger events",
        "primary_key": "event_id",
        "fields": [
            f("event_id", "string", True, "Id", prov="M", pattern=ID["event"]),
            f("company_id", "string", True, "Company", prov="M", pattern=ID["company"], fk="companies.company_id"),
            f("product_id", "string", False, "Product", prov="M", nullable=True, pattern=ID["product"], fk="products.product_id"),
            f("component_id", "string", True, "Component", prov="M", pattern=ID["component"], fk="packaging_components.component_id"),
            f("material", "string", True, "Material", prov="E", enum=MATERIALS),
            f("synthetic_category", "string", True, "Synthetic category convention", prov="E", enum=CATEGORIES),
            f("event_type", "string", True, "Event type", prov="E", enum=EVENT_TYPES),
            f("date", "date", True, "Date", prov="M"),
            f("period", "month", True, "YYYY-MM", prov="M"),
            f("kg", "number", True, "Mass (≥0)", prov="E", minimum=0),
            f("direction", "string", True, "in | out | memo", prov="E", enum=["in", "out", "memo"]),
            f("source_document_id", "string", False, "Evidence", prov="M", nullable=True),
            f("source_line_id", "string", False, "Evidence line", prov="M", nullable=True),
            f("counterparty_id", "string", False, "Counterparty", prov="M", nullable=True, pattern=PARTY),
            f("status", "string", True, "Evidence status", prov="E",
              enum=["document_supported", "estimated", "declared", "unknown", "cancelled"]),
            f("supersedes_event_id", "string", False, "Correction chain", prov="M", nullable=True),
            SYN,
        ],
    },
    "invoices": {
        "title": "Invoice headers (DS-05 A)",
        "primary_key": "invoice_id",
        "fields": [
            f("invoice_id", "string", True, "Internal id", prov="M", pattern=ID["invoice"]),
            f("invoice_number", "string", True, "Printed number (≤ 5 may share, handbook p.41)", prov="P", pattern=r"^SY[A-Z0-9/-]{3,14}$"),
            f("invoice_type", "string", True, "Type", prov="P", enum=INVOICE_TYPES),
            f("company_id", "string", True, "EPRLens client", prov="M", pattern=ID["company"], fk="companies.company_id"),
            f("supplier_id", "string", True, "Issuer", prov="M", pattern=PARTY),
            f("buyer_id", "string", True, "Recipient", prov="M", pattern=PARTY),
            f("invoice_date", "date", True, "Date", prov="P"),
            f("place_of_supply_state", "string", True, "Place of supply", prov="P"),
            f("tax_mode", "string", True, "intra (CGST+SGST) | inter (IGST) | import", prov="P", enum=["intra", "inter", "import"]),
            f("currency", "string", True, "Currency", prov="P", enum=["INR", "USD"]),
            f("total_taxable_value", "number", True, "₹", prov="P"),
            f("gst", "number", True, "Σ tax heads ₹", prov="P"),
            f("total", "number", True, "Invoice total ₹", prov="P"),
            f("line_count", "integer", True, "Lines", prov="M", minimum=1, maximum=12),
            f("status", "string", True, "issued | cancelled", prov="P", enum=["issued", "cancelled"]),
            f("original_invoice_id", "string", False, "For credit notes / returns", prov="M", nullable=True, pattern=ID["invoice"]),
            f("document_id", "string", False, "PDF if rendered", prov="M", nullable=True, pattern=ID["document"]),
            f("is_anomaly", "boolean", True, "Ground truth", prov="GT"),
            f("anomaly_type", "string", False, "Primary anomaly", prov="GT", nullable=True, enum=ANOMALY_TYPES + [None]),
            SYN,
        ],
    },
    "invoice_lines": {
        "title": "Invoice lines (DS-05 A)",
        "primary_key": "invoice_line_id",
        "fields": [
            f("invoice_line_id", "string", True, "Id", prov="M", pattern=ID["invoice_line"]),
            f("invoice_id", "string", True, "Header", prov="M", pattern=ID["invoice"], fk="invoices.invoice_id"),
            f("line_no", "integer", True, "1–12", prov="P", minimum=1, maximum=12),
            f("item_description", "string", True, "Printed description", prov="P"),
            f("product_id", "string", False, "Product", prov="M", nullable=True, pattern=ID["product"], fk="products.product_id"),
            f("component_id", "string", False, "Component", prov="M", nullable=True, pattern=ID["component"], fk="packaging_components.component_id"),
            f("material", "string", False, "Material", prov="P", nullable=True, enum=MATERIALS + [None]),
            f("plastic_category", "string", False, "Category as printed on the synthetic document (convention, not legal)", prov="P",
              nullable=True, enum=CATEGORIES + [None]),
            f("hsn_code", "string", False, "HSN", prov="P", nullable=True),
            f("raw_quantity", "number", False, "Printed quantity", prov="P", nullable=True),
            f("raw_unit", "string", False, "Printed unit", prov="P", nullable=True, enum=UNITS + [None]),
            f("weight_per_unit_g", "number", False, "Printed or master g/unit", prov="P", nullable=True),
            f("normalized_quantity_kg", "number", False, "Normalised kg", prov="M", nullable=True),
            f("recorded_quantity_kg", "number", False, "Matching internal record kg", prov="M", nullable=True),
            f("rate", "number", True, "₹/unit", prov="P"),
            f("taxable_value", "number", True, "₹", prov="P"),
            f("gst_rate", "number", True, "%", prov="P", enum=[0, 5, 12, 18]),
            f("gst_amount", "number", True, "₹", prov="P"),
            f("transaction_id", "string", False, "Linked transaction", prov="M", nullable=True, pattern=ID["transaction"]),
            SYN,
        ],
    },
    "invoices_flat": {
        "title": "Flattened invoice view with exactly the brief's columns (one row per line, derived)",
        "primary_key": "invoice_line_id",
        "fields": [
            f("invoice_line_id", "string", True, "Line id", prov="M"),
            f("invoice_id", "string", True, "Header id", prov="M"),
            f("invoice_number", "string", True, "", prov="P"),
            f("invoice_type", "string", True, "", prov="P", enum=INVOICE_TYPES),
            f("company_id", "string", True, "", prov="M"),
            f("supplier_id", "string", True, "", prov="M"),
            f("buyer_id", "string", True, "", prov="M"),
            f("invoice_date", "date", True, "", prov="P"),
            f("material", "string", False, "", prov="P", nullable=True),
            f("plastic_category", "string", False, "", prov="P", nullable=True),
            f("raw_quantity", "number", False, "", prov="P", nullable=True),
            f("raw_unit", "string", False, "", prov="P", nullable=True),
            f("normalized_quantity_kg", "number", False, "", prov="M", nullable=True),
            f("recorded_quantity_kg", "number", False, "", prov="M", nullable=True),
            f("rate", "number", True, "", prov="P"),
            f("amount", "number", True, "taxable value", prov="P"),
            f("gst", "number", True, "", prov="P"),
            f("total", "number", True, "line total", prov="P"),
            f("is_anomaly", "boolean", True, "", prov="GT"),
            f("anomaly_type", "string", False, "", prov="GT", nullable=True),
            SYN,
        ],
    },
    "recycling": {
        "title": "Recycling proxy records (DS-11 A)",
        "primary_key": "recycling_record_id",
        "fields": [
            f("recycling_record_id", "string", True, "Id", prov="M", pattern=ID["recycling"]),
            f("company_id", "string", True, "Company", prov="M", pattern=ID["company"], fk="companies.company_id"),
            f("month", "month", True, "YYYY-MM", prov="M"),
            f("synthetic_category", "string", True, "Synthetic category convention", prov="E", enum=CATEGORIES),
            f("waste_generated_kg", "number", True, "SYNTHETIC PROXY of post-consumer waste", prov="E", minimum=0),
            f("waste_collected_kg", "number", True, "Collected", prov="E", minimum=0),
            f("waste_recycled_kg", "number", True, "Recycled", prov="E", minimum=0),
            f("recycler_id", "string", True, "Recycler", prov="M", pattern=ID["recycler"], fk="recyclers.recycler_id"),
            f("recycler_registered", "boolean", True, "Registry status", prov="H"),
            f("credits_documented_kg", "number", True, "Documented claims, not verified certificates", prov="E", minimum=0),
            f("basis", "string", True, "Proxy model version", prov="M", enum=["synthetic_proxy_v1"]),
            SYN,
        ],
    },
    "anomaly_ground_truth": {
        "title": "Anomaly ground truth (never visible to detectors)",
        "primary_key": "anomaly_instance_id",
        "fields": [
            f("anomaly_instance_id", "string", True, "Id", prov="GT", pattern=ID["anomaly"]),
            f("record_id", "string", True, "Affected record", prov="GT"),
            f("record_type", "string", True, "Table", prov="GT",
              enum=["invoice", "invoice_line", "transaction", "product_month", "recycling", "component"]),
            f("anomaly_type", "string", True, "AN01…AN20", prov="GT", enum=ANOMALY_TYPES),
            f("field", "string", False, "Mutated field", prov="GT", nullable=True),
            f("original_value", "string", False, "Before", prov="GT", nullable=True),
            f("modified_value", "string", False, "After", prov="GT", nullable=True),
            f("expected_detection_method", "string", True, "R | ML | R+ML", prov="GT", enum=["R", "ML", "R+ML"]),
            f("expected_rule_ids", "array", False, "Rules expected to fire", prov="GT", items="string"),
            f("severity", "string", True, "Severity", prov="GT", enum=["low", "medium", "high", "n/a"]),
            f("is_anomaly", "boolean", True, "False for hard negatives (AN17)", prov="GT"),
            f("test_case_type", "string", True, "Case type", prov="GT",
              enum=["routine", "targeted_anomaly", "targeted_legit_hard"]),
            f("split", "string", True, "train | validation | test", prov="GT", enum=["train", "validation", "test"]),
            f("seed", "integer", True, "Sub-seed used", prov="GT"),
            SYN,
        ],
    },
    "scenarios": {
        "title": "What-if scenario inputs",
        "primary_key": "scenario_id",
        "fields": [
            f("scenario_id", "string", True, "Id", prov="M", pattern=ID["scenario"]),
            f("company_id", "string", True, "Company", prov="M", pattern=ID["company"], fk="companies.company_id"),
            f("product_id", "string", True, "Product", prov="M", pattern=ID["product"], fk="products.product_id"),
            f("baseline_weight_g", "number", True, "Weight in force", prov="E", minimum=0),
            f("proposed_weight_g", "number", True, "Proposed weight", prov="E", minimum=0),
            f("units", "integer", True, "Units basis", prov="E", minimum=0),
            f("baseline_kg", "number", True, "units × baseline g / 1000", prov="E"),
            f("proposed_kg", "number", True, "units × proposed g / 1000", prov="E"),
            f("projected_reduction_kg", "number", True, "baseline − proposed", prov="E"),
            f("assumptions", "string", True, "Plain-text assumptions", prov="E"),
            SYN,
        ],
    },
    "scenario_results": {
        "title": "What-if calculated outputs (docs/scenario-formulas.md)",
        "primary_key": "scenario_id",
        "fields": [
            f("scenario_id", "string", True, "Id", prov="M", pattern=ID["scenario"], fk="scenarios.scenario_id"),
            f("company_id", "string", True, "", prov="M", pattern=ID["company"]),
            f("product_id", "string", True, "", prov="M", pattern=ID["product"]),
            f("baseline_kg", "number", True, "", prov="E"),
            f("proposed_kg", "number", True, "", prov="E"),
            f("projected_reduction_kg", "number", True, "", prov="E"),
            f("reduction_pct_effective", "number", True, "", prov="E"),
            f("plastic_baseline_kg", "number", True, "", prov="E"),
            f("plastic_proposed_kg", "number", True, "", prov="E"),
            f("plastic_reduction_kg", "number", True, "", prov="E"),
            f("units_basis", "string", True, "historical | forecast", prov="E", enum=["historical", "forecast"]),
            f("period", "string", True, "e.g. FY2025-26", prov="E"),
            f("disclaimer", "string", True, "Hypothetical; not a compliance or cost claim", prov="M"),
            SYN,
        ],
    },
    "business_descriptions": {
        "title": "Natural-language business descriptions with ground truth",
        "primary_key": "description_id",
        "fields": [
            f("description_id", "string", True, "Id", prov="M", pattern=ID["description"]),
            f("company_id", "string", True, "Company", prov="M", pattern=ID["company"], fk="companies.company_id"),
            f("description", "string", True, "Template-generated text", prov="E"),
            f("expected_manufacturer", "boolean", True, "", prov="GT"),
            f("expected_importer", "boolean", True, "", prov="GT"),
            f("expected_brand_owner", "boolean", True, "", prov="GT"),
            f("expected_industry", "string", True, "", prov="GT", enum=INDUSTRIES),
            f("difficulty", "string", True, "plain | vague | contradictory", prov="GT", enum=["plain", "vague", "contradictory"]),
            SYN,
        ],
    },
}

# Ground-truth JSON accompanying each PDF (one object per document).
INVOICE_DOCUMENT = {
    "title": "Invoice PDF ground truth",
    "required": [
        "document_id", "invoice_number", "invoice_type", "company_id", "supplier_id", "buyer_id",
        "expected_fields", "linked_transaction_ids", "is_anomaly", "anomaly_types", "template_id", "seed",
        "synthetic_flag",
    ],
}
