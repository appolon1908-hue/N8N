from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.policy_community_runtime import validate_community_runtime_policy
from scripts.policy_n8n import validate_n8n_policy

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


if __name__ == "__main__":
    unittest.main()
