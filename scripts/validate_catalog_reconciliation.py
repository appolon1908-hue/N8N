#!/usr/bin/env python3
"""Validate catalog authority, product coverage, and non-additive inventory counts."""

from __future__ import annotations

try:
    from .catalog_reconciliation import (
        CatalogReconciliationError,
        catalog_reconciliation_snapshot,
        validate_catalog_reconciliation,
    )
except ImportError:
    from catalog_reconciliation import (  # type: ignore
        CatalogReconciliationError,
        catalog_reconciliation_snapshot,
        validate_catalog_reconciliation,
    )


def main() -> int:
    errors = validate_catalog_reconciliation()
    if errors:
        print("CATALOG_RECONCILIATION=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1

    try:
        snapshot = catalog_reconciliation_snapshot()
    except CatalogReconciliationError as exc:
        print("CATALOG_RECONCILIATION=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("CATALOG_RECONCILIATION=PASS")
    print(f"REGISTERED_PRODUCTS={snapshot['registered_products']}")
    print(f"REGISTERED_WORKFLOW_DOMAINS={snapshot['registered_workflow_domains']}")
    print(f"REGISTERED_CATALOGS={snapshot['registered_catalogs']}")
    print(f"RAW_CATALOG_ENTRIES={snapshot['raw_catalog_entries']}")
    print(f"CANONICAL_DESIGNS={snapshot['canonical_designs']}")
    print(f"SUPPLEMENTAL_UNIQUE_DESIGNS={snapshot['supplemental_unique_designs']}")
    print(f"COMPATIBILITY_VIEW_ENTRIES={snapshot['compatibility_view_entries']}")
    print(
        "DEDUPLICATED_INTENDED_DESIGNS="
        f"{snapshot['deduplicated_intended_designs']}"
    )
    print(f"PACK_WORKFLOWS_DECLARED={snapshot['pack_workflows_declared']}")
    print(f"PACK_WORKFLOWS_BUILT={snapshot['pack_workflows_built']}")
    print(f"ACTIVE_WORKFLOWS={snapshot['active_workflows']}")
    print("CATALOG_COUNTS_ARE_ADDITIVE=false")
    print("PACK_COUNTS_ARE_ADDITIVE_TO_DESIGNS=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
