from __future__ import annotations

import unittest

from scripts.catalog_reconciliation import (
    catalog_reconciliation_snapshot,
    catalog_specs,
    catalog_workflow_ids,
    canonical_catalog_spec,
    pack_workflow_ids,
    registered_product_ids,
    validate_catalog_reconciliation,
    workflow_domain_for_id,
)


class CatalogReconciliationTests(unittest.TestCase):
    def test_registry_and_catalogs_reconcile(self) -> None:
        self.assertEqual(validate_catalog_reconciliation(), [])

    def test_exactly_one_canonical_catalog_is_authoritative(self) -> None:
        specs = catalog_specs()
        canonical = canonical_catalog_spec()
        self.assertEqual(sum(spec.role == "CANONICAL" for spec in specs), 1)
        self.assertTrue(canonical.contributes_to_unique_inventory)

    def test_compatibility_views_never_add_to_the_unique_count(self) -> None:
        snapshot = catalog_reconciliation_snapshot()
        compatibility_rows = [
            row for row in snapshot["catalog_rows"] if row["role"] == "COMPATIBILITY_VIEW"
        ]
        self.assertTrue(compatibility_rows)
        self.assertTrue(all(row["unique_contribution"] == 0 for row in compatibility_rows))

    def test_deduplicated_design_count_has_one_formula(self) -> None:
        snapshot = catalog_reconciliation_snapshot()
        self.assertEqual(
            snapshot["deduplicated_intended_designs"],
            snapshot["canonical_designs"] + snapshot["supplemental_unique_designs"],
        )
        self.assertEqual(
            snapshot["raw_catalog_entries"],
            sum(row["workflow_count"] for row in snapshot["catalog_rows"]),
        )

    def test_compatibility_aliases_resolve_to_canonical_ids(self) -> None:
        canonical_ids = set(catalog_workflow_ids(canonical_catalog_spec()))
        for spec in catalog_specs():
            if spec.role != "COMPATIBILITY_VIEW":
                continue
            for workflow_id in catalog_workflow_ids(spec):
                target = spec.compatibility_aliases.get(workflow_id, workflow_id)
                self.assertIn(target, canonical_ids)

    def test_every_registered_product_has_catalog_scope(self) -> None:
        scoped_products = {
            product_id for spec in catalog_specs() for product_id in spec.product_ids
        }
        self.assertEqual(scoped_products, registered_product_ids())

    def test_every_catalog_and_pack_id_resolves_to_one_domain(self) -> None:
        workflow_ids = {
            workflow_id
            for spec in catalog_specs()
            for workflow_id in catalog_workflow_ids(spec)
        }
        workflow_ids.update(pack_workflow_ids())
        for workflow_id in sorted(workflow_ids):
            resolution = workflow_domain_for_id(workflow_id)
            self.assertTrue(resolution["directory"].startswith("workflows/"))
            self.assertTrue(resolution["prefix"])
            self.assertTrue(resolution["domain_id"])


if __name__ == "__main__":
    unittest.main()
