"""Read-only lookup over the entity masters (one source of truth for later
generators, tests and fixtures). SYNTHETIC — EPRLens Demo."""
from pathlib import Path

from .tableio import read_csv_typed

TABLE_KEYS = {
    "companies": "company_id", "products": "product_id", "packaging_components": "component_id",
    "suppliers": "supplier_id", "buyers": "buyer_id", "recyclers": "recycler_id",
    "addresses": "address_id", "entity_relationships": "relationship_id",
}
PREFIX_TABLE = {"COMP": "companies", "PROD": "products", "PKGCOMP": "packaging_components", "SUP": "suppliers",
                "BUY": "buyers", "REC": "recyclers", "ADDR": "addresses", "REL": "entity_relationships"}


class EntityIndex:
    def __init__(self, masters_dir):
        self.dir = Path(masters_dir)
        self.tables = {t: read_csv_typed(self.dir / f"{t}.csv", t) for t in TABLE_KEYS}
        self.by_id = {t: {row[k]: row for row in self.tables[t]} for t, k in TABLE_KEYS.items()}

    def resolve(self, entity_id):
        """Row for any entity id, or None for unknown ids (unknown-supplier scenario)."""
        table = PREFIX_TABLE.get(entity_id.split("_", 1)[0])
        return self.by_id[table].get(entity_id) if table else None

    def relationships(self, source_id=None, rtype=None, active_on=None):
        out = []
        for r in self.tables["entity_relationships"]:
            if source_id and r["source_entity_id"] != source_id:
                continue
            if rtype and r["relationship_type"] != rtype:
                continue
            if active_on and not (r["start_date"] <= active_on and (r["end_date"] is None or r["end_date"] >= active_on)):
                continue
            out.append(r)
        return out

    def components_in_force(self, product_id, on: str):
        return [c for c in self.tables["packaging_components"] if c["product_id"] == product_id
                and c["effective_from"] <= on and (c["effective_to"] is None or c["effective_to"] >= on)]

    def weight_in_force(self, product_id, component_name, on: str):
        rows = [c for c in self.components_in_force(product_id, on) if c["component_name"] == component_name]
        return rows[0]["weight_per_unit_g"] if len(rows) == 1 else None
