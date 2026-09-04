#!/usr/bin/env python3
"""Fail-closed validation for the registered automation catalogs."""
from __future__ import annotations

import json
from typing import Any

try:
    from .catalog_core import (
        AUTOMATIONS_DIR, CatalogReconciliationError, ROOT, VALID_ROLES, WORKFLOWS_DIR,
        _duplicates, canonical_catalog_spec, catalog_document, catalog_product_references,
        catalog_specs, catalog_workflow_ids, pack_workflow_ids, product_rows, products_document,
        registered_product_ids, registry_document, workflow_domain_for_id, workflow_domain_rows,
        workflow_records,
    )
except ImportError:
    from catalog_core import (  # type: ignore
        AUTOMATIONS_DIR, CatalogReconciliationError, ROOT, VALID_ROLES, WORKFLOWS_DIR,
        _duplicates, canonical_catalog_spec, catalog_document, catalog_product_references,
        catalog_specs, catalog_workflow_ids, pack_workflow_ids, product_rows, products_document,
        registered_product_ids, registry_document, workflow_domain_for_id, workflow_domain_rows,
        workflow_records,
    )


def validate_catalog_reconciliation() -> list[str]:
    errors: list[str] = []
    try:
        registry, products = registry_document(), products_document()
        product_items, product_ids = product_rows(), registered_product_ids()
        domains, specs = workflow_domain_rows(), catalog_specs()
        canonical_ids = set(catalog_workflow_ids(canonical_catalog_spec()))
    except (OSError, json.JSONDecodeError, CatalogReconciliationError) as exc:
        return [f"catalog reconciliation source cannot be loaded: {exc}"]

    expected_policy = {
        "canonical_catalog_is_authoritative": True,
        "supplemental_catalogs_add_unique_designs": True,
        "compatibility_views_add_to_unique_count": False,
        "compatibility_aliases_resolve_before_comparison": True,
        "pack_inventory_relationship": "SEPARATE_NOT_ADDITIVE",
        "count_key": "workflow_id",
    }
    if (registry.get("schema_version"), registry.get("status")) != ("1.0", "SOURCE_ONLY"):
        errors.append("catalog registry must be schema 1.0 and SOURCE_ONLY")
    if registry.get("counting_policy") != expected_policy:
        errors.append("catalog counting policy differs from the reviewed model")
    if (products.get("schema_version"), products.get("status")) != ("2.0", "SOURCE_ONLY"):
        errors.append("product registry must be schema 2.0 and SOURCE_ONLY")
    if products.get("catalog_registry") != "config/catalog-registry.v1.json":
        errors.append("product registry must reference the catalog registry")

    namespaces: list[str] = []
    for row in product_items:
        product_id = row.get("id", "UNKNOWN")
        namespace = row.get("namespace")
        if not isinstance(namespace, str) or not namespace:
            errors.append(f"product {product_id} has an invalid namespace")
        else:
            namespaces.append(namespace)
        if row.get("status") != "DESIGN_ONLY" or not isinstance(row.get("domains"), list) or not row["domains"]:
            errors.append(f"product {product_id} must be DESIGN_ONLY with domains")
    for duplicate in sorted(_duplicates(namespaces)):
        errors.append(f"duplicate product namespace: {duplicate}")

    spec_ids, spec_paths = [s.catalog_id for s in specs], [s.relative_path for s in specs]
    for duplicate in sorted(_duplicates(spec_ids)):
        errors.append(f"duplicate catalog id: {duplicate}")
    for duplicate in sorted(_duplicates(spec_paths)):
        errors.append(f"duplicate catalog path: {duplicate}")
    if sum(spec.role == "CANONICAL" for spec in specs) != 1:
        errors.append("exactly one catalog must be CANONICAL")
    registered_paths = set(spec_paths)
    discovered_paths = {p.relative_to(ROOT).as_posix() for p in AUTOMATIONS_DIR.glob("*catalog*.json") if p.is_file()}
    for path in sorted(discovered_paths - registered_paths):
        errors.append(f"catalog file is not registered: {path}")
    for path in sorted(registered_paths - discovered_paths):
        errors.append(f"registered catalog file is missing: {path}")

    scoped_products: set[str] = set()
    authoritative_ids: set[str] = set()
    all_catalog_ids: list[str] = []
    for spec in specs:
        scoped_products.update(spec.product_ids)
        if spec.role not in VALID_ROLES:
            errors.append(f"catalog {spec.catalog_id} has invalid role {spec.role}")
        if spec.role == "CANONICAL" and not spec.contributes_to_unique_inventory:
            errors.append("canonical catalog must contribute to unique inventory")
        if spec.role == "COMPATIBILITY_VIEW" and spec.contributes_to_unique_inventory:
            errors.append(f"compatibility catalog {spec.catalog_id} must contribute zero")
        if spec.role != "COMPATIBILITY_VIEW" and spec.compatibility_aliases:
            errors.append(f"catalog {spec.catalog_id} may not declare aliases")
        for product_id in sorted(set(spec.product_ids) - product_ids):
            errors.append(f"catalog {spec.catalog_id} references unknown product {product_id}")
        try:
            document, records, ids = catalog_document(spec), workflow_records(spec), catalog_workflow_ids(spec)
        except (OSError, json.JSONDecodeError, CatalogReconciliationError) as exc:
            errors.append(f"catalog {spec.catalog_id} cannot be read: {exc}")
            continue
        all_catalog_ids.extend(ids)
        if str(document.get("schema_version")) != spec.schema_version:
            errors.append(f"catalog {spec.catalog_id} schema differs from registry")
        if document.get("default_activation") != "DISABLED":
            errors.append(f"catalog {spec.catalog_id} default activation must be DISABLED")
        if spec.role != "COMPATIBILITY_VIEW" and document.get("status") != "SOURCE_ONLY":
            errors.append(f"catalog {spec.catalog_id} must be SOURCE_ONLY")
        for duplicate in sorted(_duplicates(ids)):
            errors.append(f"catalog {spec.catalog_id} duplicates workflow id {duplicate}")
        observed = catalog_product_references(spec)
        for product_id in sorted(observed - set(spec.product_ids)):
            errors.append(f"catalog {spec.catalog_id} uses out-of-scope product {product_id}")
        if spec.role in {"CANONICAL", "COMPATIBILITY_VIEW"} and observed != set(spec.product_ids):
            errors.append(f"catalog {spec.catalog_id} product scope differs from records")
        for row in records:
            if isinstance(row, dict) and (
                row.get("state") != "DESIGN_ONLY" or row.get("active") is True
                or row.get("direct_service_access") is True
            ):
                errors.append(f"catalog {spec.catalog_id} workflow {row.get('id')} violates source-only safety")
        if spec.role == "COMPATIBILITY_VIEW":
            for item in ids:
                if spec.compatibility_aliases.get(item, item) not in canonical_ids:
                    errors.append(f"compatibility workflow {item} has no canonical resolution")
            for source, target in spec.compatibility_aliases.items():
                if source not in ids or target not in canonical_ids:
                    errors.append(f"compatibility alias {source} -> {target} is invalid")
        elif spec.role == "SUPPLEMENTAL" and set(ids) & canonical_ids:
            errors.append(f"supplemental catalog {spec.catalog_id} duplicates canonical ids")
        if spec.contributes_to_unique_inventory:
            for item in ids:
                if item in authoritative_ids:
                    errors.append(f"authoritative workflow id {item} is declared more than once")
                authoritative_ids.add(item)
    for product_id in sorted(product_ids - scoped_products):
        errors.append(f"registered product {product_id} has no catalog scope")

    domain_ids: list[str] = []
    prefixes: list[str] = []
    registered_directories: set[str] = set()
    for row in domains:
        domain_id, directory = row.get("id"), row.get("workflow_directory")
        domain_products, domain_prefixes = row.get("product_ids"), row.get("workflow_prefixes")
        if not isinstance(domain_id, str) or not domain_id:
            errors.append("workflow domain has an invalid id")
            continue
        domain_ids.append(domain_id)
        if not isinstance(directory, str) or not directory.startswith("workflows/"):
            errors.append(f"workflow domain {domain_id} has an invalid directory")
        else:
            registered_directories.add(directory)
            if not (ROOT / directory).is_dir():
                errors.append(f"workflow domain directory is missing: {directory}")
        if not isinstance(domain_products, list) or not domain_products or set(domain_products) - product_ids:
            errors.append(f"workflow domain {domain_id} has invalid product coverage")
        if not isinstance(domain_prefixes, list) or not domain_prefixes:
            errors.append(f"workflow domain {domain_id} has no prefixes")
        else:
            for prefix in domain_prefixes:
                if not isinstance(prefix, str) or not prefix.endswith("."):
                    errors.append(f"workflow domain {domain_id} has invalid prefix {prefix!r}")
                else:
                    prefixes.append(prefix)
        for design_path in row.get("design_paths", []):
            if not isinstance(design_path, str) or not (ROOT / design_path).is_file():
                errors.append(f"workflow domain {domain_id} design source is missing: {design_path}")
    for duplicate in sorted(_duplicates(domain_ids)):
        errors.append(f"duplicate workflow domain id: {duplicate}")
    for duplicate in sorted(_duplicates(prefixes)):
        errors.append(f"duplicate workflow prefix: {duplicate}")
    existing_directories = {
        path.relative_to(ROOT).as_posix() for path in WORKFLOWS_DIR.iterdir()
        if path.is_dir() and path.name != "_templates"
    }
    for path in sorted(existing_directories - registered_directories):
        errors.append(f"workflow directory is not registered: {path}")
    for path in sorted(registered_directories - existing_directories):
        errors.append(f"registered workflow directory is missing: {path}")

    try:
        pack_ids = pack_workflow_ids()
    except (OSError, json.JSONDecodeError, CatalogReconciliationError) as exc:
        errors.append(f"pack inventory cannot be loaded: {exc}")
        pack_ids = []
    for duplicate in sorted(_duplicates(pack_ids)):
        errors.append(f"pack workflow id is declared more than once: {duplicate}")
    for item in all_catalog_ids + pack_ids:
        try:
            workflow_domain_for_id(item)
        except CatalogReconciliationError as exc:
            errors.append(str(exc))
    if registry.get("pack_inventory") != {
        "directory": "automations/packs", "status": "IMPLEMENTATION_BACKLOG",
        "counting_relationship": "SEPARATE_NOT_ADDITIVE",
    }:
        errors.append("pack inventory policy differs from reviewed model")
    return errors
