"""Write JSON Schema (draft 2020-12) files from spec.py.

Usage:  python synthetic-data/schemas/build_schemas.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spec  # noqa: E402

TYPE_MAP = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "number": {"type": "number"},
    "boolean": {"type": "boolean"},
    "date": {"type": "string", "format": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
    "month": {"type": "string", "pattern": r"^\d{4}-\d{2}$"},
    "datetime": {"type": "string", "format": "date-time"},
}


def field_schema(type_, description, extras):
    if type_ == "array":
        s = {"type": "array", "items": TYPE_MAP[extras.get("items", "string")].copy()}
    else:
        s = TYPE_MAP[type_].copy()
    s["description"] = description
    for key in ("pattern", "minimum", "maximum"):
        if key in extras:
            s[key] = extras[key]
    if "enum" in extras:
        s["enum"] = extras["enum"]
    if extras.get("nullable"):
        t = s["type"]
        s["type"] = [t, "null"] if isinstance(t, str) else t + ["null"]
        if "enum" in s and None not in s["enum"]:
            s["enum"] = s["enum"] + [None]
    if "prov" in extras:
        s["x-provenance"] = extras["prov"]
    if "fk" in extras:
        s["x-foreign-key"] = extras["fk"]
    return s


def table_schema(name, table):
    props, required = {}, []
    for fname, type_, req, desc, extras in table["fields"]:
        props[fname] = field_schema(type_, desc, extras)
        if req:
            required.append(fname)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://eprlens.example/schemas/{name}.schema.json",
        "title": table["title"],
        "description": "SYNTHETIC — EPRLens Demo. PROPOSED schema; see docs/DECISIONS-REQUIRED.md.",
        "x-schema-version": spec.SCHEMA_VERSION,
        "x-primary-key": table["primary_key"],
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": props,
    }


def invoice_document_schema():
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://eprlens.example/schemas/invoice_document.schema.json",
        "title": spec.INVOICE_DOCUMENT["title"],
        "description": "SYNTHETIC — EPRLens Demo. One JSON per PDF; values must equal what is printed.",
        "x-schema-version": spec.SCHEMA_VERSION,
        "type": "object",
        "required": spec.INVOICE_DOCUMENT["required"],
        "properties": {
            "document_id": {"type": "string", "pattern": spec.ID["document"]},
            "invoice_id": {"type": "string", "pattern": spec.ID["invoice"]},
            "invoice_number": {"type": "string"},
            "invoice_type": {"type": "string", "enum": spec.INVOICE_TYPES},
            "company_id": {"type": "string", "pattern": spec.ID["company"]},
            "supplier_id": {"type": "string", "pattern": spec.PARTY},
            "buyer_id": {"type": "string", "pattern": spec.PARTY},
            "expected_fields": {
                "type": "object",
                "required": ["invoice_number", "invoice_date", "vendor", "buyer", "lines", "gst", "invoice_total"],
                "properties": {
                    "lines": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 12,
                        "items": {
                            "type": "object",
                            "required": ["line_reference", "page_number", "item_description", "quantity", "unit",
                                         "normalized_quantity_kg", "rate", "amount"],
                        },
                    }
                },
            },
            "linked_transaction_ids": {"type": "array", "items": {"type": "string"}},
            "is_anomaly": {"type": "boolean"},
            "anomaly_types": {"type": "array", "items": {"type": "string", "enum": spec.ANOMALY_TYPES}},
            "test_case_type": {"type": "string", "enum": ["routine", "targeted_anomaly", "targeted_legit_hard", "illustrative"]},
            "template_id": {"type": "string", "pattern": r"^L\d{2}$"},
            "seed": {"type": "integer"},
            "synthetic_flag": {"const": True},
        },
    }


def main():
    out = HERE
    for name, table in spec.TABLES.items():
        path = out / f"{name}.schema.json"
        path.write_text(json.dumps(table_schema(name, table), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (out / "invoice_document.schema.json").write_text(
        json.dumps(invoice_document_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(spec.TABLES) + 1} schemas to {out}")


if __name__ == "__main__":
    main()
