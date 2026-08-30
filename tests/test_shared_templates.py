from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import validate_workflows


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "workflows" / "_templates"
COMMAND_PATH = "/v2/automation/commands"
LEGACY_COMMAND_PATH = "/v1/integrations/n8n/commands"
REQUIRED_GATEWAY_HEADERS = {
    "authorization",
    "x-tenant-id",
    "x-request-id",
    "x-correlation-id",
    "idempotency-key",
}


def load_templates() -> list[tuple[Path, dict]]:
    return [
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(TEMPLATES.glob("*.json"))
    ]


def assignments(workflow: dict) -> dict[str, dict]:
    return {
        assignment["name"]: assignment
        for node in workflow["nodes"]
        for assignment in node.get("parameters", {})
        .get("assignments", {})
        .get("assignments", [])
    }


def request_node(workflow: dict) -> dict:
    return next(
        node
        for node in workflow["nodes"]
        if node["type"] == "n8n-nodes-base.httpRequest"
    )


def request_headers(node: dict) -> set[str]:
    return {
        header["name"].lower()
        for header in node["parameters"]["headerParameters"]["parameters"]
    }


class SharedTemplateTests(unittest.TestCase):
    def test_every_template_is_inactive_credential_free_and_surface_conformant(self) -> None:
        policy = validate_workflows.load_policy()
        for path, workflow in load_templates():
            self.assertFalse(workflow["active"], path.name)
            self.assertNotIn("credentials", workflow, path.name)
            self.assertTrue(
                all("credentials" not in node for node in workflow["nodes"]),
                path.name,
            )
            self.assertEqual([], validate_workflows.validate(path, policy), path.name)

    def test_timeout_never_retries_an_unknown_effect_without_reconciliation(self) -> None:
        for path, workflow in load_templates():
            metadata = workflow["meta"]["codestra"]
            self.assertFalse(metadata["automatic_retry_on_timeout"], path.name)
            self.assertRegex(metadata["timeout_semantics"], r"RECONCIL|READ_.*STATE")
            for node in workflow["nodes"]:
                self.assertIsNot(
                    node.get("retryOnFail"),
                    True,
                    f"{path.name}:{node.get('name')}",
                )

    def test_command_templates_shape_the_v2_envelope_and_headers(self) -> None:
        schema = json.loads(
            (ROOT / "contracts" / "command-envelope.schema.json").read_text()
        )
        required_fields = set(schema["required"])
        command_templates = 0
        for path, workflow in load_templates():
            serialized = json.dumps(workflow)
            command_nodes = [
                node
                for node in workflow["nodes"]
                if node.get("parameters", {}).get("url", "").endswith(COMMAND_PATH)
            ]
            if not command_nodes:
                self.assertNotIn(LEGACY_COMMAND_PATH, serialized, path.name)
                continue
            command_templates += 1
            template_assignments = assignments(workflow)
            self.assertFalse(required_fields - set(template_assignments), path.name)
            self.assertEqual(
                "string", template_assignments["command_version"]["type"]
            )
            self.assertNotRegex(
                str(template_assignments["command_type"]["value"]), r"\.v[0-9]+$"
            )
            self.assertNotIn(LEGACY_COMMAND_PATH, serialized, path.name)
            for node in command_nodes:
                self.assertTrue(node.get("disabled"), path.name)
                self.assertEqual(REQUIRED_GATEWAY_HEADERS, request_headers(node), path.name)
                body = node["parameters"]["body"]
                for field in required_fields:
                    self.assertIn(f"{field}:$json.{field}", body, path.name)
                for forbidden in (
                    "target:$json.target",
                    "capability:$json.capability",
                    "actor:$json.actor",
                ):
                    self.assertNotIn(forbidden, body, path.name)
        self.assertEqual(3, command_templates)

    def test_job_lifecycle_templates_match_v2_envelopes_and_headers(self) -> None:
        claim = json.loads((TEMPLATES / "claim-automation-run.v2.json").read_text())
        claim_assignments = assignments(claim)
        claim_request = request_node(claim)
        self.assertEqual(
            "https://middleware.invalid/v2/automation/jobs/claim",
            claim_request["parameters"]["url"],
        )
        self.assertFalse(
            {"job_id", "delivery_token", "workflow_key", "workflow_version", "execution_id"}
            - set(claim_assignments)
        )
        self.assertEqual(REQUIRED_GATEWAY_HEADERS, request_headers(claim_request))
        for field in (
            "job_id",
            "delivery_token",
            "workflow_key",
            "workflow_version",
            "execution_id",
        ):
            self.assertIn(
                f"{field}:$json.{field}", claim_request["parameters"]["body"]
            )

        complete = json.loads(
            (TEMPLATES / "report-automation-result.v2.json").read_text()
        )
        complete_assignments = assignments(complete)
        complete_request = request_node(complete)
        self.assertEqual(
            "https://middleware.invalid/v2/automation/jobs/{{$json.job_id}}/complete",
            complete_request["parameters"]["url"],
        )
        self.assertFalse(
            {"job_id", "lease_token", "execution_id", "result_code"}
            - set(complete_assignments)
        )
        self.assertEqual(REQUIRED_GATEWAY_HEADERS, request_headers(complete_request))
        for field in ("lease_token", "execution_id", "result_code", "safe_result"):
            self.assertIn(
                f"{field}:$json.{field}", complete_request["parameters"]["body"]
            )

        reconcile = json.loads(
            (TEMPLATES / "reconciliation-sweeper.v2.json").read_text()
        )
        reconcile_request = request_node(reconcile)
        self.assertEqual(
            "https://middleware.invalid/v2/automation/jobs/reconcile",
            reconcile_request["parameters"]["url"],
        )
        self.assertEqual(REQUIRED_GATEWAY_HEADERS, request_headers(reconcile_request))
        self.assertIn(
            "requested_by:$json.requested_by",
            reconcile_request["parameters"]["body"],
        )
        self.assertIn(
            "dry_run:$json.dry_run", reconcile_request["parameters"]["body"]
        )

    def test_odoo_template_uses_one_canonical_upsert_contract(self) -> None:
        workflow = json.loads(
            (TEMPLATES / "disabled-odoo-lead-via-middleware.json").read_text()
        )
        template_assignments = {
            name: assignment["value"]
            for name, assignment in assignments(workflow).items()
        }
        self.assertEqual("crm.lead.upsert", template_assignments["command_type"])
        self.assertEqual("1.0", template_assignments["command_version"])
        payload = str(template_assignments["payload"])
        for marker in (
            "source_record_id",
            "review_pending",
            "review_required",
            "allow_external_contact",
            "provenance",
            "consent",
        ):
            self.assertIn(marker, payload)
        self.assertNotIn("crm.lead.create", json.dumps(workflow))

    def test_error_template_has_recursive_guard_and_middleware_dlq_handoff(self) -> None:
        workflow = json.loads((TEMPLATES / "error-dead-letter.v2.json").read_text())
        metadata = workflow["meta"]["codestra"]
        self.assertTrue(metadata["recursive_error_guard"])
        self.assertEqual(
            "BOUNDED_RETRY_THEN_MIDDLEWARE_DLQ", metadata["failure_policy"]
        )
        self.assertTrue(
            any(
                node["type"] == "n8n-nodes-base.errorTrigger"
                for node in workflow["nodes"]
            )
        )
        report = next(
            node
            for node in workflow["nodes"]
            if node["name"] == "Report Failure Through Middleware"
        )
        self.assertIn("{{$json.job_id}}", report["parameters"]["url"])
        self.assertNotIn("template-job/fail", report["parameters"]["url"])
        self.assertEqual(
            {"lease_token", "execution_id", "error_code", "retryable"},
            {
                field
                for field in (
                    "lease_token",
                    "execution_id",
                    "error_code",
                    "retryable",
                )
                if f"{field}: $json.{field}" in report["parameters"]["body"]
            },
        )

    def test_failure_and_approval_templates_send_required_gateway_headers(self) -> None:
        for filename in ("error-dead-letter.v2.json", "human-approval.v2.json"):
            workflow = json.loads((TEMPLATES / filename).read_text())
            self.assertEqual(
                REQUIRED_GATEWAY_HEADERS,
                request_headers(request_node(workflow)),
                filename,
            )

    def test_only_simple_json_fields_are_allowed_in_dynamic_path_segments(self) -> None:
        surface = validate_workflows.load_middleware_surface()
        self.assertTrue(
            validate_workflows.middleware_target_allowed(
                "POST",
                "https://middleware.invalid/v2/automation/jobs/{{$json.job_id}}/fail",
                surface,
            )
        )
        for unsafe in (
            "{{$env.JOB_ID}}",
            "{{$json['job_id']}}",
            "{{$json.job_id + '/complete'}}",
        ):
            with self.subTest(unsafe=unsafe):
                url = f"https://middleware.invalid/v2/automation/jobs/{unsafe}/fail"
                self.assertFalse(
                    validate_workflows.middleware_target_allowed("POST", url, surface)
                )

    def test_human_approval_never_self_approves_or_waits_in_n8n(self) -> None:
        workflow = json.loads((TEMPLATES / "human-approval.v2.json").read_text())
        self.assertEqual(
            "MIDDLEWARE_OWNS_APPROVAL_STATE",
            workflow["meta"]["codestra"]["authority"],
        )
        serialized = json.dumps(workflow).lower()
        self.assertNotIn("approve=true", serialized)
        self.assertNotIn(
            "wait",
            [
                node["type"].rsplit(".", 1)[-1].lower()
                for node in workflow["nodes"]
            ],
        )


if __name__ == "__main__":
    unittest.main()
