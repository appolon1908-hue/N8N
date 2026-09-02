from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.policy_n8n import REQUIRED_RUNTIME_EXCLUDED_NODES
from scripts.readback_umbrella_controls import (
    CONTROL_NAMES,
    GUARD_DIGEST_LABEL,
    GUARD_PATH,
    GUARD_TARGET,
    WRITE_BOUNDARY_LABEL,
    main,
    read_controls,
    validate_identity,
    validate_egress_controls,
    validate_runtime_node_exclusions,
)


class UmbrellaReadbackTests(unittest.TestCase):
    def valid_inspection(self) -> dict:
        return {
            "Image": "sha256:" + ("2" * 64),
            "Config": {
                "Image": "ghcr.io/codestra/n8n@sha256:" + ("1" * 64),
                "Entrypoint": ["/bin/sh", GUARD_TARGET],
                "Env": [
                    *(f"{name}=false" for name in CONTROL_NAMES),
                    "NODES_EXCLUDE=" + json.dumps(sorted(REQUIRED_RUNTIME_EXCLUDED_NODES)),
                    "N8N_SSRF_PROTECTION_ENABLED=true",
                    "N8N_SSRF_ALLOWED_HOSTNAMES=api.codestra.co,auth.codestra.co",
                    "N8N_SSRF_BLOCKED_IP_RANGES=0.0.0.0/0,::/0",
                ],
                "Labels": {
                    "com.docker.compose.project": "codestra-n8n-staging-template",
                    "com.docker.compose.service": "n8n-main",
                    GUARD_DIGEST_LABEL: hashlib.sha256(GUARD_PATH.read_bytes()).hexdigest(),
                    WRITE_BOUNDARY_LABEL: "disabled-source-only",
                },
            },
            "Mounts": [{"Destination": GUARD_TARGET, "RW": False}],
            "State": {"Running": True, "Status": "running", "Health": {"Status": "healthy"}},
        }

    def test_exact_false_controls_pass(self) -> None:
        controls, missing, non_false = read_controls(
            [*(f"{name}=false" for name in CONTROL_NAMES), "UNRELATED_SETTING=redacted"]
        )
        self.assertEqual({name: False for name in CONTROL_NAMES}, controls)
        self.assertEqual([], missing)
        self.assertEqual([], non_false)

    def test_missing_is_not_false(self) -> None:
        controls, missing, non_false = read_controls([])
        self.assertEqual({name: None for name in CONTROL_NAMES}, controls)
        self.assertEqual(list(CONTROL_NAMES), missing)
        self.assertEqual([], non_false)

    def test_true_malformed_and_duplicate_values_fail(self) -> None:
        entries = [f"{name}=false" for name in CONTROL_NAMES]
        entries[0] = f"{CONTROL_NAMES[0]}=true"
        entries[1] = f"{CONTROL_NAMES[1]}=FALSE"
        entries.append(f"{CONTROL_NAMES[2]}=false")
        controls, missing, non_false = read_controls(entries)
        self.assertEqual([], missing)
        self.assertEqual(
            [CONTROL_NAMES[0], CONTROL_NAMES[1], CONTROL_NAMES[2]], non_false
        )
        self.assertIs(controls[CONTROL_NAMES[0]], True)
        self.assertIsNone(controls[CONTROL_NAMES[1]])
        self.assertIsNone(controls[CONTROL_NAMES[2]])

    def test_inspection_launch_failures_remain_machine_readable(self) -> None:
        failures = (
            OSError("docker unavailable"),
            subprocess.TimeoutExpired(["docker", "inspect"], 15),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                output = io.StringIO()
                with (
                    patch(
                        "scripts.readback_umbrella_controls.subprocess.run",
                        side_effect=failure,
                    ),
                    patch.object(
                        sys,
                        "argv",
                        [
                            "readback",
                            "n8n-test",
                            "ghcr.io/codestra/n8n@sha256:" + ("1" * 64),
                            "sha256:" + ("2" * 64),
                        ],
                    ),
                    redirect_stdout(output),
                ):
                    result = main()
                payload = json.loads(output.getvalue())
                self.assertEqual(1, result)
                self.assertIs(payload["pass"], False)
                self.assertEqual(list(CONTROL_NAMES), payload["missing"])
                self.assertEqual(
                    "container inspection unavailable", payload["error"]
                )

    def test_exact_deployment_identity_and_node_exclusions_pass(self) -> None:
        inspection = self.valid_inspection()
        identity, errors = validate_identity(
            inspection, inspection["Config"]["Image"], inspection["Image"]
        )
        self.assertEqual([], errors)
        self.assertEqual("n8n-main", identity["compose_service"])
        self.assertEqual(
            [], validate_runtime_node_exclusions(inspection["Config"]["Env"])
        )
        self.assertEqual([], validate_egress_controls(inspection["Config"]["Env"]))

    def test_unowned_container_or_effect_node_availability_fails(self) -> None:
        inspection = self.valid_inspection()
        inspection["Config"]["Labels"]["com.docker.compose.service"] = "lookalike"
        inspection["Config"]["Entrypoint"] = ["/docker-entrypoint.sh"]
        inspection["Mounts"][0]["RW"] = True
        _, errors = validate_identity(
            inspection, inspection["Config"]["Image"], inspection["Image"]
        )
        self.assertTrue(any("Compose service" in error for error in errors))
        self.assertTrue(any("start through" in error for error in errors))
        self.assertTrue(any("mounted read-only" in error for error in errors))

        entries = inspection["Config"]["Env"]
        node_index = next(
            index for index, value in enumerate(entries) if value.startswith("NODES_EXCLUDE=")
        )
        entries[node_index] = "NODES_EXCLUDE=[]"
        self.assertTrue(validate_runtime_node_exclusions(entries))

    def test_main_emits_pass_only_for_bound_runtime_identity(self) -> None:
        output = io.StringIO()
        result = subprocess.CompletedProcess(
            args=["docker", "inspect"],
            returncode=0,
            stdout=json.dumps(self.valid_inspection()),
            stderr="",
        )
        with (
            patch("scripts.readback_umbrella_controls.subprocess.run", return_value=result),
            patch.object(
                sys,
                "argv",
                [
                    "readback",
                    "n8n-main-1",
                    self.valid_inspection()["Config"]["Image"],
                    self.valid_inspection()["Image"],
                ],
            ),
            redirect_stdout(output),
        ):
            exit_code = main()
        payload = json.loads(output.getvalue())
        self.assertEqual(0, exit_code)
        self.assertIs(payload["pass"], True)
        self.assertEqual([], payload["identity_errors"])
        self.assertNotIn("Env", payload)

    def test_wrong_release_stopped_container_and_egress_drift_fail(self) -> None:
        inspection = self.valid_inspection()
        _, errors = validate_identity(
            inspection,
            "ghcr.io/codestra/n8n@sha256:" + ("3" * 64),
            "sha256:" + ("4" * 64),
        )
        self.assertTrue(any("approved release" in error for error in errors))
        inspection["State"] = {"Running": False, "Status": "exited"}
        _, errors = validate_identity(
            inspection, inspection["Config"]["Image"], inspection["Image"]
        )
        self.assertTrue(any("not running" in error for error in errors))
        self.assertTrue(any("not healthy" in error for error in errors))

        entries = inspection["Config"]["Env"]
        entries[-1] = "N8N_SSRF_BLOCKED_IP_RANGES=10.0.0.0/8"
        self.assertTrue(validate_egress_controls(entries))

    def test_non_string_node_exclusion_is_machine_readable_failure(self) -> None:
        inspection = self.valid_inspection()
        entries = inspection["Config"]["Env"]
        node_index = next(
            index for index, value in enumerate(entries) if value.startswith("NODES_EXCLUDE=")
        )
        entries[node_index] = 'NODES_EXCLUDE=[{}]'
        self.assertEqual(
            ["NODES_EXCLUDE must contain only string node types"],
            validate_runtime_node_exclusions(entries),
        )


if __name__ == "__main__":
    unittest.main()
