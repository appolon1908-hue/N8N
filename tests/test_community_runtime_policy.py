from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.policy_community_runtime import validate_community_runtime_policy
from scripts.policy_n8n import validate_n8n_policy
from scripts import validate_workflows

ROOT = Path(__file__).resolve().parents[1]


class CommunityRuntimePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads((ROOT / "config" / "n8n-policy.json").read_text())
        self.runtime = json.loads(
            (ROOT / "config" / "n8n-community-runtime.v1.json").read_text()
        )
        self.egress = json.loads(
            (ROOT / "deploy" / "egress" / "n8n-egress-policy.v1.json").read_text()
        )

    def test_prepared_community_contract_is_canonical_but_not_verified(self) -> None:
        policy_errors, _ = validate_n8n_policy(self.policy)
        runtime_errors = validate_community_runtime_policy(
            self.policy, self.runtime, self.egress
        )
        self.assertEqual([], policy_errors)
        self.assertEqual([], runtime_errors)
        self.assertEqual("UNVERIFIED", self.policy["status"])
        self.assertFalse(self.runtime["activation_authorized"])
        self.assertFalse(self.egress["runtime_apply_authorized"])

    def test_staging_binding_contract_drift_is_rejected(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["staging_binding_contract"]["status"] = "DEFINED_NOT_APPLIED"
        errors, _ = validate_n8n_policy(policy)
        self.assertTrue(any("staging_binding_contract" in error for error in errors))

    def test_workflow_activation_cannot_be_enabled(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["activation_policy"]["workflow_activation_allowed"] = True
        errors, _ = validate_n8n_policy(policy)
        self.assertTrue(any("activation policy" in error for error in errors))

    def test_runtime_umbrella_controls_cannot_be_missing_or_enabled(self) -> None:
        runtime = copy.deepcopy(self.runtime)
        runtime["operations"]["umbrella_controls"][
            "N8N_EXTERNAL_PROVIDER_WRITES"
        ] = True
        errors = validate_community_runtime_policy(self.policy, runtime, self.egress)
        self.assertTrue(any("umbrella controls" in error for error in errors))

    def test_middleware_route_drift_is_rejected(self) -> None:
        runtime = copy.deepcopy(self.runtime)
        runtime["endpoint"]["routes"][0]["path"] = "/v2/automation/commands"
        errors = validate_community_runtime_policy(self.policy, runtime, self.egress)
        self.assertTrue(any("route contract" in error for error in errors))

    def test_personal_credential_owner_is_rejected(self) -> None:
        runtime = copy.deepcopy(self.runtime)
        runtime["credential"]["owner"] = "personal-admin"
        errors = validate_community_runtime_policy(self.policy, runtime, self.egress)
        self.assertTrue(any("credential owner" in error for error in errors))

    def test_egress_default_allow_is_rejected(self) -> None:
        egress = copy.deepcopy(self.egress)
        egress["default_action"] = "ALLOW"
        errors = validate_community_runtime_policy(self.policy, self.runtime, egress)
        self.assertTrue(any("default deny" in error for error in errors))

    def test_ssrf_allowlist_drift_is_rejected(self) -> None:
        egress = copy.deepcopy(self.egress)
        egress["application_ssrf"]["allowed_hostnames"].append("example.com")
        errors = validate_community_runtime_policy(self.policy, self.runtime, egress)
        self.assertTrue(any("hostname allowlist" in error for error in errors))

    def test_egress_destination_drift_is_rejected(self) -> None:
        egress = copy.deepcopy(self.egress)
        egress["runtime_network"]["allow"][0]["destination_dns"] = "example.com"
        errors = validate_community_runtime_policy(self.policy, self.runtime, egress)
        self.assertTrue(any("allow rules differ" in error for error in errors))

    def test_dangerous_node_cannot_be_reintroduced(self) -> None:
        runtime = copy.deepcopy(self.runtime)
        runtime["security"]["dangerous_nodes_excluded"].remove(
            "n8n-nodes-base.executeCommand"
        )
        errors = validate_community_runtime_policy(self.policy, runtime, self.egress)
        self.assertTrue(any("dangerous-node" in error for error in errors))

    def test_runtime_firewall_evidence_cannot_be_fabricated_in_prepared_source(self) -> None:
        egress = copy.deepcopy(self.egress)
        egress["runtime_network"]["evidence_sha256"] = "1" * 64
        errors = validate_community_runtime_policy(self.policy, self.runtime, egress)
        self.assertTrue(any("must not claim runtime evidence" in error for error in errors))

    def test_verified_policy_must_bind_fixed_runtime_contract(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["status"] = "VERIFIED"
        policy["endpoint_binding"].update(
            {
                "status": "VERIFIED",
                "production_strategy": "verified-fixed-private-dns",
                "approved_base_url": "https://evil.example.net",
            }
        )
        policy["credential_binding"].update(
            {
                "status": "VERIFIED",
                "strategy": "verified-n8n-credential",
                "approved_types": ["httpHeaderAuth"],
                "approved_names": ["Personal Credential"],
            }
        )
        policy["editor_access"].update(
            {
                "status": "VERIFIED",
                "strategy": "verified-private-admin-network",
                "publicly_routable": False,
            }
        )
        errors = validate_community_runtime_policy(policy, self.runtime, self.egress)
        self.assertTrue(any("community runtime gateway" in error for error in errors))
        self.assertTrue(any("service-owned credential" in error for error in errors))
        self.assertTrue(any("gateway OIDC plus native auth" in error for error in errors))
        self.assertTrue(any("runtime image evidence" in error for error in errors))

    def test_verified_runtime_image_cannot_be_below_minimum(self) -> None:
        runtime = copy.deepcopy(self.runtime)
        runtime["runtime_image"].update(
            {
                "status": "VERIFIED",
                "approved_image": "ghcr.io/appolon1908-hue/automation/n8n@sha256:" + ("1" * 64),
                "approved_image_version": "2.31.9",
                "image_digest_evidence_sha256": "1" * 64,
                "version_evidence_sha256": "2" * 64,
            }
        )
        errors = validate_community_runtime_policy(self.policy, runtime, self.egress)
        self.assertTrue(any("below the required minimum" in error for error in errors))

    def test_verified_workflow_targets_are_limited_to_community_routes(self) -> None:
        self.assertFalse(
            validate_workflows.community_runtime_target_allowed(
                "POST",
                "https://api.codestra.co/v2/automation/jobs/claim",
                self.runtime,
            )
        )
        self.assertTrue(
            validate_workflows.community_runtime_target_allowed(
                "POST",
                "https://api.codestra.co/v1/integrations/n8n/commands",
                self.runtime,
            )
        )


if __name__ == "__main__":
    unittest.main()
