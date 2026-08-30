from __future__ import annotations

import unittest
from pathlib import Path

from scripts import validate_n8n_runtime_bindings

ROOT = Path(__file__).resolve().parents[1]


class N8nRuntimeBindingTests(unittest.TestCase):
    def test_committed_runtime_bindings_are_prepare_only(self) -> None:
        text = (ROOT / "config" / "n8n-runtime-bindings.env").read_text(encoding="utf-8")
        values, parse_errors = validate_n8n_runtime_bindings.parse_env(text)
        self.assertEqual([], parse_errors)
        self.assertEqual([], validate_n8n_runtime_bindings.validate(values))
        self.assertEqual("UNVERIFIED", values["N8N_ENDPOINT_BINDING"])
        self.assertEqual("UNVERIFIED", values["N8N_CREDENTIAL_BINDING"])
        self.assertEqual("UNVERIFIED", values["N8N_EDITOR_BINDING"])
        self.assertEqual("PENDING_RUNTIME_VALIDATION", values["N8N_POLICY_BINDING"])
        self.assertEqual("false", values["N8N_WORKFLOW_ACTIVATION"])

    def test_runtime_bindings_cannot_claim_activation_or_verified_state(self) -> None:
        values = dict(validate_n8n_runtime_bindings.EXPECTED_BINDINGS)
        values["N8N_WORKFLOW_ACTIVATION"] = "true"
        values["N8N_ENDPOINT_BINDING"] = "VERIFIED"
        errors = validate_n8n_runtime_bindings.validate(values)
        self.assertTrue(any("N8N_WORKFLOW_ACTIVATION" in error for error in errors))
        self.assertTrue(any("N8N_ENDPOINT_BINDING" in error for error in errors))

    def test_runtime_binding_file_rejects_extra_credential_like_values(self) -> None:
        values, parse_errors = validate_n8n_runtime_bindings.parse_env(
            "N8N_ENDPOINT_BINDING=UNVERIFIED\n"
            "N8N_CREDENTIAL_BINDING=UNVERIFIED\n"
            "N8N_EDITOR_BINDING=UNVERIFIED\n"
            "N8N_POLICY_BINDING=PENDING_RUNTIME_VALIDATION\n"
            "N8N_WORKFLOW_ACTIVATION=false\n"
            "N8N_SMTP_TOKEN=secret-token\n"
        )
        errors = parse_errors + validate_n8n_runtime_bindings.validate(values)
        self.assertTrue(any("credential-bearing" in error for error in errors))
        self.assertTrue(any("unexpected runtime bindings" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
