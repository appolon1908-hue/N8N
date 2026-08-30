from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class AutomationIntegrationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load("contracts/operation-policy.v2.json")
        self.surface = load("contracts/middleware-surface.v1.json")
        self.envelope = load("contracts/command-envelope.schema.json")
        self.layer = load("config/integration-layer.v2.json")
        self.branches = load("config/branch-dependency-map.v2.json")
        self.beyvra = load("automations/beyvra.catalog.v2.json")

    def test_generic_scopes_are_absent(self) -> None:
        all_scopes = {
            scope
            for client in self.policy["clients"].values()
            for scope in client["scopes"]
        }
        self.assertNotIn("automation.execute", all_scopes)
        self.assertNotIn("automation.command", all_scopes)
        self.assertFalse(self.policy["invariants"]["generic_execute_scope_allowed"])
        self.assertFalse(self.policy["invariants"]["generic_command_scope_allowed"])

    def test_postly_has_dedicated_client_and_family(self) -> None:
        client = self.policy["clients"]["n8n-social-automation"]
        self.assertIn("social.postly", client["workflow_families"])
        self.assertIn("social.codestra", client["workflow_families"])
        self.assertEqual(["social."], client["command_prefixes"])
        self.assertIn("automation.command.social", client["scopes"])
        messaging = self.policy["clients"]["n8n-messaging-automation"]
        self.assertNotIn("social.", messaging["command_prefixes"])
        self.assertNotIn("automation.command.social", messaging["scopes"])

    def test_beyvra_frontend_is_not_an_automation_client(self) -> None:
        repositories = {row["id"]: row for row in self.layer["repositories"]}
        self.assertIn("beyvra-backend", repositories)
        self.assertIn("beyvra-frontend", repositories)
        self.assertFalse(repositories["beyvra-frontend"]["is_n8n_client"])
        boundary = self.policy["product_boundaries"]["product.beyvra-nonfinancial"]
        self.assertFalse(boundary["frontend_is_automation_client"])
        self.assertFalse(self.beyvra["frontend_is_machine_client"])

    def test_beyvra_is_nonfinancial_and_prefix_limited(self) -> None:
        client = self.policy["clients"]["n8n-product-automation"]
        self.assertIn("product.beyvra-nonfinancial", client["workflow_families"])
        self.assertIn("beyvra.operations.", client["command_prefixes"])
        self.assertNotIn("beyvra.", client["command_prefixes"])
        self.assertEqual(["beyvra.operations."], self.beyvra["allowed_command_prefixes"])
        self.assertFalse(self.beyvra["invariants"]["financial_effects_allowed"])
        self.assertFalse(self.beyvra["invariants"]["demo_order_effects_allowed"])
        for forbidden in ("trade.", "wallet.", "payment.", "custody.", "chain."):
            self.assertIn(forbidden, self.beyvra["prohibited_command_prefixes"])

    def test_beyvra_workflows_are_inactive_and_middleware_only(self) -> None:
        self.assertGreaterEqual(len(self.beyvra["workflows"]), 5)
        for workflow in self.beyvra["workflows"]:
            self.assertFalse(workflow["active"])
            self.assertFalse(workflow["direct_service_access"])
            self.assertEqual("DESIGN_ONLY", workflow["state"])
            self.assertTrue(workflow["middleware_route"].startswith("/v2/automation/beyvra/"))
            self.assertTrue(workflow["command_types"])
            for command in workflow["command_types"]:
                self.assertTrue(command.startswith("beyvra.operations."))

    def test_branch_map_contains_postly_and_beyvra_contracts(self) -> None:
        stack = {(row["repository"], row["branch"]) for row in self.branches["contract_stack"]}
        self.assertIn(
            ("appolon1908-hue/social.codestra.co", "integration/n8n-postly-automation-v2-20260827"),
            stack,
        )
        self.assertIn(
            ("appolon1908-hue/beyvra-backend", "integration/n8n-automation-v2-20260827"),
            stack,
        )
        self.assertIn(
            ("appolon1908-hue/beyvra-frontend", "integration/automation-status-ui-v2-20260827"),
            stack,
        )
        self.assertIn(
            "automation/beyvra-operations-v2-20260827", self.branches["n8n_branches"]
        )
        self.assertIn(
            "phase-x1/roadmap-packs", self.branches["n8n_branches"]
        )

    def test_roadmap_packs_are_declared_and_inactive(self) -> None:
        expected = {
            "codestra.marketing": "automations/packs/codestra-marketing.v2.json",
            "codestra.ai": "automations/packs/codestra-ai.v2.json",
            "codestra.communication": "automations/packs/codestra-communication.v2.json",
            "codestra.social": "automations/packs/codestra-social.v2.json",
        }
        for pack_name, pack_path in expected.items():
            pack = load(pack_path)
            self.assertEqual(pack_name, pack["pack"])
            self.assertFalse(pack["active"])
            self.assertTrue(pack["workflows"])

    def test_ai_pack_is_advisory_only(self) -> None:
        pack = load("automations/packs/codestra-ai.v2.json")
        self.assertEqual("advisory-only", pack["ai_authority"])
        self.assertFalse(pack["may_authorize_spend"])
        self.assertFalse(pack["may_publish"])
        self.assertFalse(pack["may_send_customer_delivery"])
        self.assertTrue(pack["approval_required_after_ai_output"])

    def test_codestra_social_name_is_resolved(self) -> None:
        pack = load("automations/packs/codestra-social.v2.json")
        self.assertEqual("Codestra Social", pack["canonical_system"])
        self.assertEqual("appolon1908-hue/social.codestra.co", pack["canonical_repository"])
        self.assertIn("Postiz", pack["legacy_names"])

    def test_active_lease_context_is_required_for_steps_and_commands(self) -> None:
        operations = {
            (row["method"], row["path"]): row for row in self.policy["operations"]
        }
        steps = operations[("POST", "/v2/automation/jobs/{job_id}/steps")]
        commands = operations[("POST", "/v2/automation/commands")]
        self.assertIn("lease_token", steps["required_fields"])
        self.assertIn("execution_id", steps["required_fields"])
        for field in (
            "job_id",
            "lease_token",
            "execution_id",
            "workflow_key",
            "workflow_version",
            "step_key",
        ):
            self.assertIn(field, commands["required_fields"])

    def test_middleware_surface_has_one_canonical_command_path(self) -> None:
        invariants = self.surface["invariants"]
        self.assertEqual(1, invariants["command_paths_distinct"])
        self.assertEqual("/v2/automation/commands", invariants["canonical_command_path"])
        command_paths = {
            row["path"]
            for row in self.surface["operations"]
            if row["path"].endswith("/commands")
        }
        self.assertEqual({"/v2/automation/commands"}, command_paths)
        self.assertIn(
            "/internal/v1/automation/commands",
            invariants["legacy_command_paths_prohibited"],
        )
        self.assertIn(
            "/v1/integrations/n8n/commands",
            invariants["legacy_command_paths_prohibited"],
        )

    def test_command_envelope_requires_mirrored_headers_and_unversioned_type(self) -> None:
        headers = self.envelope["x-codestra-headers"]
        self.assertEqual(
            {
                "Authorization",
                "X-Tenant-ID",
                "X-Request-ID",
                "X-Correlation-ID",
                "Idempotency-Key",
            },
            set(headers["required"]),
        )
        self.assertEqual("/tenant_id", headers["mirrors"]["X-Tenant-ID"])
        pattern = re.compile(self.envelope["properties"]["type"]["pattern"])
        self.assertRegex("email.message.send", pattern)
        self.assertIsNone(pattern.fullmatch("email.message.send.v1"))

    def test_templates_send_surface_required_headers(self) -> None:
        operations = {row["path"]: row for row in self.surface["operations"]}
        template_dir = ROOT / "workflows" / "_templates"
        self.assertEqual(6, len(list(template_dir.glob("*.json"))))
        for path in template_dir.glob("*.json"):
            workflow = load(str(path.relative_to(ROOT)))
            for node in workflow["nodes"]:
                if str(node.get("type", "")).lower() != "n8n-nodes-base.httprequest":
                    continue
                parameters = node["parameters"]
                url = parameters["url"]
                route = "/" + url.split("https://middleware.invalid/", 1)[1]
                required = {
                    header.lower()
                    for header in operations[route]["required_headers"]
                }
                sent = {
                    row["name"].lower()
                    for row in parameters["headerParameters"]["parameters"]
                }
                self.assertLessEqual(required, sent, str(path))

    def test_roadmap_kill_switches_are_declared_false(self) -> None:
        capabilities = load("config/capabilities.json")["capabilities"]
        for flag in (
            "LIVE_ADVERTISING_ENABLED",
            "META_READ_SYNC_ENABLED",
            "EXTERNAL_MODEL_CALLS_ENABLED",
            "ENABLE_EXTERNAL_DELIVERY",
            "SOCIAL_READ_SYNC_ENABLED",
            "SOCIAL_PUBLISHING_ENABLED",
            "LIVE_WRITE",
            "ODOO_WRITE",
        ):
            self.assertIs(capabilities[flag], False)


if __name__ == "__main__":
    unittest.main()
