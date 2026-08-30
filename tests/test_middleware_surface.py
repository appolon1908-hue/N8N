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
            if operation["purpose"] == "Submit one durable governed command"
        ]
        self.assertEqual(1, len(commands))
        self.assertEqual("POST", commands[0]["method"])
        self.assertEqual("/v1/integrations/n8n/commands", commands[0]["path"])

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

    def test_surface_remains_disabled_and_middleware_only(self) -> None:
        self.assertEqual(0, self.surface["safety"]["active_workflows"])
        self.assertFalse(self.surface["safety"]["external_effects_enabled"])
        self.assertFalse(self.surface["safety"]["production_changed"])
        self.assertFalse(self.surface["safety"]["direct_provider_access"])


if __name__ == "__main__":
    unittest.main()
