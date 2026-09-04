#!/usr/bin/env python3
"""Reconcile catalog authority, product coverage, domains, and counts."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
AUTOMATIONS_DIR = ROOT / "automations"
PACKS_DIR = AUTOMATIONS_DIR / "packs"
WORKFLOWS_DIR = ROOT / "workflows"
REGISTRY_PATH = ROOT / "config/catalog-registry.v1.json"
PRODUCTS_PATH = ROOT / "config/products.json"
VALID_ROLES = {"CANONICAL", "COMPATIBILITY_VIEW", "SUPPLEMENTAL"}


class CatalogReconciliationError(ValueError):
    pass


@dataclass(frozen=True)
class CatalogSpec:
    catalog_id: str
    relative_path: str
    role: str
    schema_version: str
    record_key: str
    contributes_to_unique_inventory: bool
    product_ids: tuple[str, ...]
    compatibility_aliases: dict[str, str]

    @property
    def path(self) -> Path:
        return ROOT / self.relative_path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _duplicates(values: Iterable[str]) -> set[str]:
    return {value for value, count in Counter(values).items() if count > 1}


def registry_document() -> dict[str, Any]:
    value = load_json(REGISTRY_PATH)
    if not isinstance(value, dict):
        raise CatalogReconciliationError("catalog registry must be an object")
    return value


def products_document() -> dict[str, Any]:
    value = load_json(PRODUCTS_PATH)
    if not isinstance(value, dict):
        raise CatalogReconciliationError("product registry must be an object")
    return value


def product_rows() -> list[dict[str, Any]]:
    rows = products_document().get("products")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise CatalogReconciliationError("products must be object rows")
    return rows


def registered_product_ids() -> set[str]:
    ids = [row.get("id") for row in product_rows()]
    if any(not isinstance(item, str) or not item for item in ids) or _duplicates(ids):
        raise CatalogReconciliationError("product ids must be unique non-empty strings")
    return set(ids)


def workflow_domain_rows() -> list[dict[str, Any]]:
    rows = registry_document().get("workflow_domains")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise CatalogReconciliationError("workflow_domains must be object rows")
    return rows


def catalog_specs() -> list[CatalogSpec]:
    rows = registry_document().get("catalogs")
    if not isinstance(rows, list) or not rows:
        raise CatalogReconciliationError("catalogs must be a non-empty list")
    specs: list[CatalogSpec] = []
    for row in rows:
        if not isinstance(row, dict):
            raise CatalogReconciliationError("catalog rows must be objects")
        aliases = row.get("compatibility_aliases", {})
        product_ids = row.get("product_ids")
        contributes = row.get("contributes_to_unique_inventory")
        required = [row.get(key) for key in ("id", "path", "role", "schema_version", "record_key")]
        if any(not isinstance(item, str) or not item for item in required):
            raise CatalogReconciliationError("catalog identity fields must be non-empty strings")
        if not isinstance(aliases, dict) or any(
            not isinstance(k, str) or not k or not isinstance(v, str) or not v
            for k, v in aliases.items()
        ):
            raise CatalogReconciliationError("catalog aliases must map non-empty strings")
        if not isinstance(product_ids, list) or not product_ids or any(
            not isinstance(item, str) or not item for item in product_ids
        ):
            raise CatalogReconciliationError("catalog product_ids must be non-empty strings")
        if not isinstance(contributes, bool):
            raise CatalogReconciliationError("catalog contribution flag must be boolean")
        specs.append(
            CatalogSpec(
                catalog_id=required[0], relative_path=required[1], role=required[2],
                schema_version=required[3], record_key=required[4],
                contributes_to_unique_inventory=contributes,
                product_ids=tuple(product_ids), compatibility_aliases=dict(aliases),
            )
        )
    return specs


def canonical_catalog_spec() -> CatalogSpec:
    canonical_id = registry_document().get("canonical_catalog_id")
    matches = [spec for spec in catalog_specs() if spec.catalog_id == canonical_id]
    if len(matches) != 1 or matches[0].role != "CANONICAL":
        raise CatalogReconciliationError("canonical_catalog_id must identify one CANONICAL catalog")
    return matches[0]


def catalog_document(spec: CatalogSpec) -> dict[str, Any]:
    value = load_json(spec.path)
    if not isinstance(value, dict):
        raise CatalogReconciliationError(f"{spec.catalog_id} must be an object")
    return value


def workflow_records(spec: CatalogSpec) -> list[Any]:
    rows = catalog_document(spec).get(spec.record_key)
    if not isinstance(rows, list):
        raise CatalogReconciliationError(f"{spec.catalog_id}.{spec.record_key} must be a list")
    return rows


def catalog_workflow_ids(spec: CatalogSpec) -> list[str]:
    ids: list[str] = []
    for row in workflow_records(spec):
        value = row if isinstance(row, str) else row.get("id") if isinstance(row, dict) else None
        if not isinstance(value, str) or not value:
            raise CatalogReconciliationError(f"{spec.catalog_id} has an invalid workflow id")
        ids.append(value)
    return ids


def catalog_product_references(spec: CatalogSpec) -> set[str]:
    document = catalog_document(spec)
    values = [document.get("product")]
    values += [row.get("product") for row in workflow_records(spec) if isinstance(row, dict)]
    return {item for item in values if isinstance(item, str) and item}


def pack_workflow_ids() -> list[str]:
    ids: list[str] = []
    for path in sorted(PACKS_DIR.glob("*.json")):
        document = load_json(path)
        rows = document.get("workflows") if isinstance(document, dict) else None
        if not isinstance(rows, list) or any(not isinstance(item, str) or not item for item in rows):
            raise CatalogReconciliationError(f"{path.name} has invalid workflows")
        ids.extend(rows)
    return ids


def _domain_rules() -> list[tuple[str, str, str]]:
    rules: list[tuple[str, str, str]] = []
    for row in workflow_domain_rows():
        domain_id, directory, prefixes = row.get("id"), row.get("workflow_directory"), row.get("workflow_prefixes")
        if not isinstance(domain_id, str) or not isinstance(directory, str) or not isinstance(prefixes, list):
            raise CatalogReconciliationError("workflow domain identity is invalid")
        rules.extend((prefix, directory, domain_id) for prefix in prefixes if isinstance(prefix, str))
    return rules


def workflow_domain_for_id(workflow_id: str) -> dict[str, str]:
    matches = [rule for rule in _domain_rules() if workflow_id.startswith(rule[0])]
    if not matches:
        raise CatalogReconciliationError(f"workflow id {workflow_id!r} has no domain mapping")
    longest = max(len(rule[0]) for rule in matches)
    winners = [rule for rule in matches if len(rule[0]) == longest]
    if len({(rule[1], rule[2]) for rule in winners}) != 1:
        raise CatalogReconciliationError(f"workflow id {workflow_id!r} has an ambiguous domain mapping")
    prefix, directory, domain_id = winners[0]
    return {"prefix": prefix, "directory": directory, "domain_id": domain_id}


def workflow_directory_for_id(workflow_id: str) -> Path:
    return ROOT / workflow_domain_for_id(workflow_id)["directory"]


def catalog_reconciliation_snapshot() -> dict[str, Any]:
    specs = catalog_specs()
    canonical_ids = set(catalog_workflow_ids(canonical_catalog_spec()))
    authoritative: set[str] = set()
    raw = compatibility = 0
    catalog_rows: list[dict[str, Any]] = []
    alias_rows: list[dict[str, str]] = []
    for spec in specs:
        ids = catalog_workflow_ids(spec)
        raw += len(ids)
        before = len(authoritative)
        if spec.contributes_to_unique_inventory:
            authoritative.update(ids)
        if spec.role == "COMPATIBILITY_VIEW":
            compatibility += len(ids)
        alias_rows.extend(
            {"catalog_id": spec.catalog_id, "source": source, "target": target}
            for source, target in sorted(spec.compatibility_aliases.items())
        )
        catalog_rows.append({
            "catalog_id": spec.catalog_id, "path": spec.relative_path, "role": spec.role,
            "schema_version": spec.schema_version, "workflow_count": len(ids),
            "exact_canonical_overlap": 0 if spec.role == "CANONICAL" else len(set(ids) & canonical_ids),
            "alias_count": sum(item in spec.compatibility_aliases for item in ids),
            "unique_contribution": len(authoritative) - before,
        })
    pack_ids = pack_workflow_ids()
    built = sum((workflow_directory_for_id(item) / f"{item}.json").is_file() for item in pack_ids)
    active = 0
    for path in WORKFLOWS_DIR.rglob("*.json"):
        if "_templates" in path.parts:
            continue
        try:
            document = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        active += int(isinstance(document, dict) and document.get("active") is True)
    return {
        "registered_products": len(product_rows()), "registered_workflow_domains": len(workflow_domain_rows()),
        "registered_catalogs": len(specs), "raw_catalog_entries": raw,
        "canonical_designs": len(canonical_ids),
        "supplemental_unique_designs": len(authoritative - canonical_ids),
        "compatibility_view_entries": compatibility,
        "deduplicated_intended_designs": len(authoritative),
        "pack_workflows_declared": len(pack_ids), "pack_workflows_built": built,
        "active_workflows": active, "catalog_rows": catalog_rows, "alias_rows": alias_rows,
    }


