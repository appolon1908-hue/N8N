from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_connected_system_manifests import validate

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ConnectedSystemManifestTests(unittest.TestCase):
    def test_connected_system_manifest_gate_passes(self) -> None:
        self.assertEqual([], validate(ROOT))

    def test_registry_names_main_as_trunk_and_blocks_broadcast_pushes(self) -> None:
        registry = load("config/n8n-connected-systems.v1.json")
        self.assertEqual("main", registry["trunk"])
        self.assertFalse(registry["broadcast_pushes_allowed"])
        self.assertTrue(registry["branch_reconciliation_required_before_more_stage4_work"])

    def test_beyvra_and_trading_have_non_overlapping_contracts(self) -> None:
        beyvra = load("systems/beyvra/integrations/n8n/manifest.v1.json")
        trading = load("systems/trading/integrations/n8n/manifest.v1.json")
        self.assertEqual(set(), set(beyvra["events"]) & set(trading["events"]))
        self.assertEqual(set(), set(beyvra["commands"]) & set(trading["commands"]))
        self.assertEqual("tbd", beyvra["risk_tier"])
        self.assertEqual("tbd", trading["risk_tier"])

    def test_odoo_is_manifested_as_system_of_record_not_direct_target(self) -> None:
        odoo = load("systems/odoo/integrations/n8n/manifest.v1.json")
        self.assertEqual("crm-system-of-record", odoo["authority"])
        self.assertFalse(odoo["n8n"]["direct_odoo_access"])
        self.assertEqual("codestra-middleware-only", odoo["integration_boundary"])

    def test_kyqra_manifest_targets_future_canonical_repo_with_scrapper_lineage(self) -> None:
        kyqra = load("systems/kyqra/integrations/n8n/manifest.v1.json")
        self.assertEqual("appolon1908-hue/kyqra-crawler", kyqra["repository"])
        self.assertEqual("appolon1908-hue/scrapper", kyqra["legacy_repository"])
        self.assertIn("scrapper-lineage-preserved", kyqra["canonical_source_state"])


if __name__ == "__main__":
    unittest.main()
