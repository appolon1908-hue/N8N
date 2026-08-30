from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiddlewareSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.surface = json.loads(
            (ROOT / "contracts" / "middleware-surface.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.operations = {
            (operation["method"], operation["path"]): operation
            for operation in self.surface["operations"]
        }

    def test_one_canonical_command_submission_path(self) -> None:
        commands = [
            operation
            for operation in self.surface["operations"]
            if operation["purpose"] == "Submit one durable governed command"
        ]
        self.assertEqual(1, len(commands))
        self.assertEqual("POST", commands[0]["method"])
        self.assertEqual("/v2/automation/commands", commands[0]["path"])
        self.assertEqual(
            "/v2/automation/commands", self.surface["command_endpoint"]
        )
        self.assertEqual(1, self.surface["invariants"]["command_paths_distinct"])

    def test_surface_matches_all_thirteen_automation_operations(self) -> None:
        expected = {
            ("POST", "/v2/automation/jobs/claim"),
            ("GET", "/v2/automation/jobs/{job_id}"),
            ("POST", "/v2/automation/jobs/{job_id}/heartbeat"),
            ("POST", "/v2/automation/jobs/{job_id}/steps"),
            ("POST", "/v2/automation/jobs/{job_id}/complete"),
            ("POST", "/v2/automation/jobs/{job_id}/fail"),
            ("POST", "/v2/automation/commands"),
            ("GET", "/v2/automation/commands/{command_id}"),
            ("POST", "/v2/automation/approvals"),
            ("GET", "/v2/automation/approvals/{approval_id}"),
            ("POST", "/v2/automation/dead-letters/{dead_letter_id}/replay"),
            ("POST", "/v2/automation/jobs/reconcile"),
            ("GET", "/v2/automation/capabilities/{capability}"),
        }
        self.assertEqual(expected, set(self.operations))

    def test_claim_response_requires_non_null_lease_fields(self) -> None:
        openapi = (ROOT / "contracts" / "automation-control-api.v2.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("$ref: '#/components/schemas/ClaimedAutomationJob'", openapi)
        self.assertIn("ClaimedAutomationJob:", openapi)
        self.assertIn("required: [lease_token, lease_expires_at]", openapi)
        self.assertIn("lease_token: {type: string, minLength: 1}", openapi)
        self.assertIn("lease_expires_at: {type: string, format: date-time}", openapi)

    def test_legacy_command_routes_are_not_allowed_for_new_workflows(self) -> None:
        self.assertNotIn(
            ("POST", "/v1/integrations/n8n/commands"), self.operations
        )
        self.assertNotIn(
            ("GET", "/v1/integrations/n8n/operations/{command_id}"),
            self.operations,
        )
        self.assertEqual(
            [
                "/v1/integrations/n8n/commands",
                "/v1/integrations/n8n/operations/{command_id}",
            ],
            self.surface["invariants"]["legacy_command_paths_prohibited_in_new_templates"],
        )

    def test_every_operation_declares_governance_semantics(self) -> None:
        required = {
            "method",
            "path",
            "purpose",
            "envelope_schema",
            "required_headers",
            "responses",
            "idempotency",
            "timeout",
        }
        for operation in self.surface["operations"]:
            self.assertFalse(required - set(operation), operation["path"])
            self.assertIn("Authorization", operation["required_headers"])
            self.assertTrue(operation["responses"])
            self.assertTrue(operation["idempotency"])
            self.assertTrue(operation["timeout"])

    def test_surface_remains_disabled_and_middleware_only(self) -> None:
        self.assertEqual(0, self.surface["safety"]["active_workflows"])
        self.assertFalse(self.surface["safety"]["external_effects_enabled"])
        self.assertFalse(self.surface["safety"]["production_changed"])
        self.assertFalse(self.surface["safety"]["direct_provider_access"])
        self.assertFalse(self.surface["safety"]["ODOO_WRITE"])
        self.assertTrue(
            self.surface["invariants"]["unknown_outcome_requires_reconciliation"]
        )


if __name__ == "__main__":
    unittest.main()
