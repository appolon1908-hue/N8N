from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_connected_system_manifests import (
    validate,
    validate_manifest,
    validate_workflow_file,
    workflow_exports,
)

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
        self.assertEqual("REQUIRES_ENUMERATION", beyvra["risk_review_status"])
        self.assertEqual("REQUIRES_ENUMERATION", trading["risk_review_status"])

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

    def test_manifest_workflow_references_resolve_to_committed_exports(self) -> None:
        registry = load("config/n8n-connected-systems.v1.json")
        exports, errors = workflow_exports(ROOT)
        self.assertEqual([], errors)
        for system in registry["tiers"]["domain_systems"]:
            manifest = load(f"systems/{system}/integrations/n8n/manifest.v1.json")
            for workflow in manifest["workflows"]:
                self.assertIn(workflow, exports)

    def test_manifest_rejects_direct_n8n_access(self) -> None:
        registry = load("config/n8n-connected-systems.v1.json")
        manifest = load("systems/odoo/integrations/n8n/manifest.v1.json")
        manifest["n8n"]["direct_api_access"] = True
        errors = validate_manifest(
            manifest,
            system="odoo",
            registry=registry,
            workflow_owners={},
            event_owners={},
            command_owners={},
        )
        self.assertIn("odoo: n8n block must match fixed registry baseline", errors)

    def test_tbd_risk_requires_review_metadata(self) -> None:
        registry = load("config/n8n-connected-systems.v1.json")
        manifest = load("systems/beyvra/integrations/n8n/manifest.v1.json")
        del manifest["risk_review_status"]
        manifest["risk_review_reason"] = ""
        errors = validate_manifest(
            manifest,
            system="beyvra",
            registry=registry,
            workflow_owners={},
            event_owners={},
            command_owners={},
        )
        self.assertIn("beyvra: tbd risk requires risk_review_status=REQUIRES_ENUMERATION", errors)
        self.assertIn("beyvra: tbd risk requires risk_review_reason", errors)

    def test_financial_data_requires_positive_retention(self) -> None:
        registry = load("config/n8n-connected-systems.v1.json")
        manifest = load("systems/trading/integrations/n8n/manifest.v1.json")
        manifest["data_classification"]["retention_days"] = 0
        errors = validate_manifest(
            manifest,
            system="trading",
            registry=registry,
            workflow_owners={},
            event_owners={},
            command_owners={},
        )
        self.assertIn(
            "trading: data_classification.retention_days must be a positive integer or null",
            errors,
        )

    def test_duplicate_workflow_and_event_ownership_are_rejected(self) -> None:
        registry = load("config/n8n-connected-systems.v1.json")
        owners = {"shared.workflow.name.v1": "odoo"}
        event_owners = {"shared.event.created": "odoo"}
        manifest = load("systems/beyvra/integrations/n8n/manifest.v1.json")
        manifest["events"] = ["shared.event.created"]
        manifest["workflows"] = ["shared.workflow.name.v1"]
        errors = validate_manifest(
            manifest,
            system="beyvra",
            registry=registry,
            workflow_owners=owners,
            event_owners=event_owners,
            command_owners={},
        )
        self.assertIn("beyvra: event 'shared.event.created' already owned by odoo", errors)
        self.assertIn("beyvra: workflow 'shared.workflow.name.v1' already owned by odoo", errors)

    def test_workflow_file_rejects_active_direct_url_and_node_credentials(self) -> None:
        workflow = {
            "name": "bad",
            "active": True,
            "nodes": [
                {
                    "name": "Direct Odoo",
                    "type": "n8n-nodes-base.httpRequest",
                    "credentials": {"httpHeaderAuth": {"id": "secret", "name": "secret"}},
                    "parameters": {"url": "http://odoo.example.test/jsonrpc"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inline-bad-workflow.json"
            path.write_text(json.dumps(workflow), encoding="utf-8")
            errors = validate_workflow_file(path, {"middleware.invalid"})
        joined = "\n".join(errors)
        self.assertIn("workflow active must be false", joined)
        self.assertIn("must not contain credentials", joined)
        self.assertIn("HTTP node target must use https", joined)
        self.assertIn("HTTP node targets non-Middleware host odoo.example.test", joined)
        self.assertIn("workflow references Odoo directly through host odoo.example.test", joined)


if __name__ == "__main__":
    unittest.main()
