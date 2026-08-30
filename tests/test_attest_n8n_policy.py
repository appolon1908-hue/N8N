from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import attest_n8n_policy
from scripts.policy_n8n import validate_n8n_policy

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "config" / "n8n-policy.json").read_text(encoding="utf-8"))

REAL_HOST = "https://middleware-core.codestra.internal"


def _args(directory: Path, **overrides: object) -> list[str]:
    artifacts = {}
    for name in ("overall", "egress", "credential", "editor", "session"):
        path = directory / f"{name}.txt"
        path.write_text(f"verification artifact for {name}\n", encoding="utf-8")
        artifacts[name] = str(path)
    values: dict[str, object] = {
        "--edition": "n8n Community Edition 1.68.0",
        "--verified-by": "First Verifier",
        "--independent-reviewer": "Second Reviewer",
        "--approved-base-url": REAL_HOST,
        "--endpoint-strategy": "verified-fixed-private-dns",
        "--credential-strategy": "verified-n8n-credential",
        "--credential-type": "httpHeaderAuth",
        "--credential-name": "codestra-middleware-service-owner",
        "--editor-strategy": "verified-gateway-oidc-and-native-auth",
        "--evidence": artifacts["overall"],
        "--egress-evidence": artifacts["egress"],
        "--credential-evidence": artifacts["credential"],
        "--editor-evidence": artifacts["editor"],
        "--session-policy-evidence": artifacts["session"],
    }
    values.update(overrides)
    argv: list[str] = []
    for flag, value in values.items():
        argv.extend([flag, str(value)])
    return argv


class AttestationTests(unittest.TestCase):
    def _build(self, **overrides: object) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            args = attest_n8n_policy.parse_args(_args(directory, **overrides))
            return attest_n8n_policy.build_policy(POLICY, args)

    def test_a_complete_attestation_satisfies_the_shipped_validator(self) -> None:
        policy = self._build()
        errors, excluded = validate_n8n_policy(policy)
        self.assertEqual(errors, [])
        self.assertEqual(policy["status"], "VERIFIED")
        self.assertIn("n8n-nodes-base.executeCommand", excluded)

    def test_evidence_hashes_are_computed_from_the_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            argv = _args(directory)
            args = attest_n8n_policy.parse_args(argv)
            policy = attest_n8n_policy.build_policy(POLICY, args)
            expected = hashlib.sha256(
                Path(args.egress_evidence).read_bytes()
            ).hexdigest()
        self.assertEqual(
            policy["endpoint_binding"]["egress_policy_evidence_sha256"], expected
        )

    def test_one_person_cannot_be_both_verifier_and_reviewer(self) -> None:
        with self.assertRaises(attest_n8n_policy.AttestationError):
            self._build(**{"--verified-by": "Same Person", "--independent-reviewer": "same person"})

    def test_placeholder_endpoints_are_refused(self) -> None:
        for host in (
            "https://middleware.invalid",
            "https://middleware.example",
            "https://localhost",
            "https://10.0.0.5",
            "http://middleware-core.codestra.internal",
        ):
            with self.subTest(host=host):
                with self.assertRaises(attest_n8n_policy.AttestationError):
                    self._build(**{"--approved-base-url": host})

    def test_an_unnamed_edition_is_refused(self) -> None:
        with self.assertRaises(attest_n8n_policy.AttestationError):
            self._build(**{"--edition": "UNVERIFIED"})

    def test_missing_evidence_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            argv = _args(directory, **{"--evidence": str(directory / "absent.txt")})
            args = attest_n8n_policy.parse_args(argv)
            with self.assertRaises(attest_n8n_policy.AttestationError):
                attest_n8n_policy.build_policy(POLICY, args)

    def test_empty_evidence_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            blank = directory / "blank.txt"
            blank.write_text("   \n", encoding="utf-8")
            args = attest_n8n_policy.parse_args(
                _args(directory, **{"--egress-evidence": str(blank)})
            )
            with self.assertRaises(attest_n8n_policy.AttestationError):
                attest_n8n_policy.build_policy(POLICY, args)

    def test_the_dangerous_node_exclusions_are_carried_through_unchanged(self) -> None:
        policy = self._build()
        self.assertEqual(
            policy["security"]["dangerous_nodes_excluded"],
            POLICY["security"]["dangerous_nodes_excluded"],
        )
        self.assertIs(policy["security"]["public_api_enabled"], False)
        self.assertIs(policy["editor_access"]["publicly_routable"], False)

    def test_the_template_endpoint_is_never_rewritten(self) -> None:
        policy = self._build()
        self.assertEqual(
            policy["endpoint_binding"]["template_base_url"], "https://middleware.invalid"
        )

    def test_the_committed_policy_remains_unverified(self) -> None:
        # The repository must not ship a verified attestation produced by tooling
        # rather than by people. Flipping it is a deliberate, evidenced act.
        self.assertEqual(POLICY["status"], "UNVERIFIED")
        errors, _ = validate_n8n_policy(POLICY)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
