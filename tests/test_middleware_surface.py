from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiddlewareSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.surface = json.loads(
            (ROOT / "contracts" / "middleware-surface.v1.json").read_text(encoding="utf-8")
        )

    def test_one_canonical_command_submission_path(self) -> None:
        commands = [
            operation
            for operation in self.surface["operations"]
            if operation["path"].endswith("/commands")
        ]
        self.assertEqual(1, len(commands))
        self.assertEqual("POST", commands[0]["method"])
        self.assertEqual("/v2/automation/commands", commands[0]["path"])
        self.assertEqual(
            "/v2/automation/commands",
            self.surface["invariants"]["canonical_command_path"],
        )

    def test_every_operation_declares_governance_semantics(self) -> None:
        required = {
            "method",
            "path",
            "purpose",
            "envelope_schema",
            "required_headers",
            "expected_responses",
            "idempotency",
            "timeout_reconciliation",
        }
        for operation in self.surface["operations"]:
            self.assertFalse(required - set(operation), operation["path"])

    def test_surface_remains_disabled_and_middleware_only(self) -> None:
        invariants = self.surface["invariants"]
        self.assertFalse(invariants["workflow_active_by_default"])
        self.assertFalse(invariants["external_effects_enabled_by_merge"])
        self.assertFalse(invariants["direct_business_system_access"])


if __name__ == "__main__":
    unittest.main()
