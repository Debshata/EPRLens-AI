"""CSV/JSON writing, typed reading and schema validation. SYNTHETIC — EPRLens Demo.

CSV conventions: arrays are "|"-joined, booleans are true/false, null is an empty
string, line endings are "\n" (byte-identical across operating systems).
"""
import csv
import hashlib
import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def load_schema(table):
    return json.loads((SCHEMA_DIR / f"{table}.schema.json").read_text(encoding="utf-8"))


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "|".join(str(x) for x in v)
    if isinstance(v, float):
        return repr(round(v, 6))
    return str(v)


def write_csv(rows, path, table):
    fields = list(load_schema(table)["properties"])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(fields)
        for row in rows:
            w.writerow([_cell(row.get(k)) for k in fields])


def _types(prop):
    t = prop.get("type", "string")
    return t if isinstance(t, list) else [t]


def coerce(value, prop):
    types = _types(prop)
    if value == "" and "null" in types:
        return None
    if "array" in types:
        return [] if value == "" else value.split("|")
    if "boolean" in types:
        return {"true": True, "false": False}.get(value, value)
    if "integer" in types:
        try:
            return int(value)
        except ValueError:
            return value
    if "number" in types:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def read_csv_typed(path, table):
    props = load_schema(table)["properties"]
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return [{k: coerce(v, props[k]) for k, v in row.items()} for row in csv.DictReader(fh)]


def write_json(obj, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_rows(rows, table):
    """Raises on the first invalid row (jsonschema required)."""
    import jsonschema

    schema = load_schema(table)
    validator = jsonschema.Draft202012Validator(schema)
    for row in rows:
        errors = sorted(validator.iter_errors(row), key=lambda e: e.path)
        if errors:
            e = errors[0]
            raise ValueError(f"{table}: {row.get(schema['x-primary-key'])}: {list(e.path)} {e.message}")
