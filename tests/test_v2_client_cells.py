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

    def reject(self, cells=None, policy=None, catalog=None) -> None:
        with self.assertRaises(ValueError):
            VALIDATOR.validate(
                cells or copy.deepcopy(self.cells),
                policy or copy.deepcopy(self.policy),
                catalog or copy.deepcopy(self.catalog),
            )

    def test_exact_authority_passes(self) -> None:
        VALIDATOR.validate(self.cells, self.policy, self.catalog)

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
        catalog = copy.deepcopy(self.catalog)
        catalog["authorization_profiles"]["social"]["command_prefixes"] = ["social.", "sms."]
        self.reject(catalog=catalog)

    def test_activation_and_direct_access_are_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["active"] = True
        self.reject(catalog=catalog)
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["direct_service_access"] = True
        self.reject(catalog=catalog)


if __name__ == "__main__":
    unittest.main()
