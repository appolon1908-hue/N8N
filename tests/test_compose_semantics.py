from __future__ import annotations

import copy
import json
import unittest

from scripts import policy_compose
from scripts.policy_n8n import REQUIRED_DANGEROUS_NODES


class ComposeSemanticPolicyTests(unittest.TestCase):
    def valid_model(self) -> dict:
        excluded = json.dumps(sorted(REQUIRED_DANGEROUS_NODES), separators=(",", ":"))
        common_environment = {
            **policy_compose.REQUIRED_COMMON_ENV,
            "DB_POSTGRESDB_HOST": "postgres.invalid",
            "DB_POSTGRESDB_PORT": "5432",
            "DB_POSTGRESDB_DATABASE": "n8n_validation",
            "DB_POSTGRESDB_USER": "n8n_validation",
            "QUEUE_BULL_REDIS_HOST": "redis.invalid",
            "QUEUE_BULL_REDIS_PORT": "6379",
            "N8N_HOST": "n8n.invalid",
            "WEBHOOK_URL": "https://n8n.invalid/",
            "N8N_EDITOR_BASE_URL": "https://n8n.invalid/",
            "NODES_EXCLUDE": excluded,
        }
        common = {
            "image": "ghcr.io/codestra/n8n@sha256:" + ("1" * 64),
            "profiles": [policy_compose.PROFILE],
            "restart": "no",
            "user": "1000:1000",
            "read_only": True,
            "privileged": False,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "entrypoint": ["/bin/sh", policy_compose.UMBRELLA_GUARD_TARGET],
            "networks": {"middleware_network": None},
            "secrets": [
                {"source": name, "target": name}
                for name in sorted(policy_compose.EXPECTED_SECRETS)
            ],
            "configs": [
                {
                    "source": "umbrella_guard",
                    "target": policy_compose.UMBRELLA_GUARD_TARGET,
                    "mode": "0444",
                }
            ],
            "volumes": [
                {
                    "type": "volume",
                    "source": "n8n_data",
                    "target": "/home/node/.n8n",
                }
            ],
            "environment": common_environment,
        }
        main = {
            **copy.deepcopy(common),
            "healthcheck": {
                "test": [
                    "CMD",
                    "node",
                    "-e",
                    "fetch('http://127.0.0.1:5678/healthz/readiness')",
                ]
            },
        }
        worker = copy.deepcopy(common)
        worker["environment"] = {
            **worker["environment"],
            "QUEUE_HEALTH_CHECK_ACTIVE": "true",
            "QUEUE_HEALTH_CHECK_PORT": "5680",
        }
        worker["command"] = ["worker", "--concurrency=2"]
        worker["healthcheck"] = {
            "test": [
                "CMD",
                "node",
                "-e",
                "fetch('http://127.0.0.1:5680/healthz/readiness')",
            ]
        }
        return {
            "services": {"n8n-main": main, "n8n-worker": worker},
            "volumes": {"n8n_data": {"name": "n8n-data", "external": True}},
            "networks": {
                "middleware_network": {"name": "middleware", "external": True}
            },
            "secrets": {
                name: {"name": f"secret-{name}", "external": True}
                for name in policy_compose.EXPECTED_SECRETS
            },
            "configs": {
                "umbrella_guard": {
                    "file": str(policy_compose.UMBRELLA_GUARD_SOURCE.resolve())
                }
            },
        }

    def test_valid_semantic_model_passes(self) -> None:
        self.assertEqual(
            [],
            policy_compose.validate_rendered_compose(
                self.valid_model(), sorted(REQUIRED_DANGEROUS_NODES)
            ),
        )

    def test_external_data_volume_is_structurally_required(self) -> None:
        model = self.valid_model()
        model["volumes"]["n8n_data"].pop("external")
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(
            any("externally provisioned Compose volume" in error for error in errors)
        )

    def test_unreviewed_service_and_network_are_rejected(self) -> None:
        model = self.valid_model()
        model["services"]["sidecar"] = copy.deepcopy(model["services"]["n8n-main"])
        model["services"]["n8n-main"]["networks"]["public"] = None
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("services must be exactly" in error for error in errors))
        self.assertTrue(
            any("attach only to middleware_network" in error for error in errors)
        )

    def test_missing_node_exclusion_is_rejected(self) -> None:
        model = self.valid_model()
        model["services"]["n8n-worker"]["environment"]["NODES_EXCLUDE"] = "[]"
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("NODES_EXCLUDE misses" in error for error in errors))

    def test_ssrf_protection_cannot_be_disabled(self) -> None:
        model = self.valid_model()
        model["services"]["n8n-main"]["environment"][
            "N8N_SSRF_PROTECTION_ENABLED"
        ] = "false"
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(
            any("N8N_SSRF_PROTECTION_ENABLED" in error for error in errors)
        )

    def test_missing_or_enabled_umbrella_control_is_rejected(self) -> None:
        model = self.valid_model()
        main_environment = model["services"]["n8n-main"]["environment"]
        main_environment.pop("LIVE_ADVERTISING_ENABLED")
        model["services"]["n8n-worker"]["environment"][
            "N8N_EXTERNAL_PROVIDER_WRITES"
        ] = "true"
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("LIVE_ADVERTISING_ENABLED" in error for error in errors))
        self.assertTrue(
            any("N8N_EXTERNAL_PROVIDER_WRITES" in error for error in errors)
        )

    def test_umbrella_guard_cannot_be_bypassed(self) -> None:
        model = self.valid_model()
        model["services"]["n8n-main"].pop("entrypoint")
        model["services"]["n8n-worker"]["configs"] = []
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("start through the umbrella guard" in error for error in errors))
        self.assertTrue(any("mount the umbrella enforcement guard" in error for error in errors))

    def test_umbrella_guard_alias_cannot_resolve_to_another_file(self) -> None:
        model = self.valid_model()
        model["configs"]["umbrella_guard"]["file"] = "/tmp/no-op.sh"
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("reviewed source file" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
