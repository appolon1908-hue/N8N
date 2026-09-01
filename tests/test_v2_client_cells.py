from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_v2_client_cells", ROOT / "scripts" / "validate_v2_client_cells.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class V2ClientCellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cells = VALIDATOR.load(VALIDATOR.CELLS)
        self.policy = VALIDATOR.load(VALIDATOR.POLICY)
        self.catalog = VALIDATOR.load(VALIDATOR.CATALOG)
        self.packs = VALIDATOR.load(VALIDATOR.PACKS)
        self.pack_docs = [
            VALIDATOR.load(path) for path in sorted(VALIDATOR.PACK_DOCS.glob("*.json"))
        ]
        self.product_catalogs = [VALIDATOR.load(path) for path in VALIDATOR.PRODUCT_CATALOGS]

    def reject(self, cells=None, policy=None, catalog=None, packs=None, pack_docs=None, product_catalogs=None) -> None:
        with self.assertRaises(ValueError):
            VALIDATOR.validate(
                cells or copy.deepcopy(self.cells),
                policy or copy.deepcopy(self.policy),
                catalog or copy.deepcopy(self.catalog),
                packs or copy.deepcopy(self.packs),
                pack_docs or copy.deepcopy(self.pack_docs),
                product_catalogs or copy.deepcopy(self.product_catalogs),
            )

    def test_exact_authority_passes(self) -> None:
        VALIDATOR.validate(
            self.cells, self.policy, self.catalog, self.packs, self.pack_docs,
            self.product_catalogs,
        )

    def test_legacy_aggregate_client_is_rejected(self) -> None:
        cells = copy.deepcopy(self.cells)
        cells["cells"][0]["machine_client"] = "n8n-core-automation"
        self.reject(cells=cells)

    def test_unknown_and_shared_clients_are_rejected(self) -> None:
        cells = copy.deepcopy(self.cells)
        cells["cells"][0]["machine_clients"][0] = "n8n-generic-automation"
        self.reject(cells=cells)
        cells = copy.deepcopy(self.cells)
        cells["cells"][1]["machine_clients"].append("n8n-platform-runtime")
        self.reject(cells=cells)

    def test_family_outside_client_authority_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][-1]["workflow_family_override"] = "product.unreviewed"
        self.reject(catalog=catalog)

    def test_scope_or_prefix_expansion_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["authorization_profiles"]["social"]["additional_scopes"].append(
            "automation.command.telephony"
        )
        self.reject(catalog=catalog)

    def test_prefix_from_another_family_of_same_client_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["authorization_profiles"]["identity"]["command_prefixes"] = [
            "provisioning."
        ]
        self.reject(catalog=catalog)

    def test_command_family_policy_drift_is_rejected(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["command_families"][0]["workflow_families"] = ["provisioning"]
        self.reject(policy=policy)

    def test_common_scope_drift_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["common_runtime_scopes"].append("automation.approval.read")
        self.reject(catalog=catalog)

    def test_unknown_pack_cell_is_rejected(self) -> None:
        packs = copy.deepcopy(self.packs)
        packs["packs"][-1]["cell"] = "n8n-retired-cell"
        self.reject(packs=packs)
        pack_docs = copy.deepcopy(self.pack_docs)
        pack_docs[0]["cell"] = "n8n-retired-cell"
        self.reject(pack_docs=pack_docs)

    def test_product_catalog_authority_drift_is_rejected(self) -> None:
        products = copy.deepcopy(self.product_catalogs)
        products[0]["required_scopes"].append("automation.command.telephony")
        self.reject(product_catalogs=products)
        products = copy.deepcopy(self.product_catalogs)
        products[1]["authorization"]["workflow_family"] = "product.unreviewed"
        self.reject(product_catalogs=products)
        catalog = copy.deepcopy(self.catalog)
        catalog["authorization_profiles"]["social"]["command_prefixes"] = ["social.", "sms."]
        self.reject(catalog=catalog)

    def test_activation_and_direct_access_are_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["default_activation"] = "ENABLED"
        self.reject(catalog=catalog)
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["active"] = True
        self.reject(catalog=catalog)
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["direct_service_access"] = True
        self.reject(catalog=catalog)


if __name__ == "__main__":
    unittest.main()
