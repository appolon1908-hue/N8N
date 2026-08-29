from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_observability_stack import EXPECTED_COMPONENTS, validate

ROOT = Path(__file__).resolve().parents[1]


def load_stack() -> dict:
    return json.loads((ROOT / "config/observability-stack.v1.json").read_text(encoding="utf-8"))


class ObservabilityStackTests(unittest.TestCase):
    def test_observability_stack_contract_passes(self) -> None:
        self.assertEqual([], validate(ROOT))

    def test_stack_is_not_counted_as_n8n_domain_systems(self) -> None:
        stack = load_stack()
        self.assertFalse(stack["n8n_domain_system"])
        self.assertEqual("infrastructure-control-plane", stack["classification"])
        self.assertEqual("PREPARED_NOT_APPLIED", stack["integration_state"])
        self.assertFalse(stack["production_changed"])

    def test_all_fourteen_components_are_declared_once(self) -> None:
        stack = load_stack()
        ids = [component["id"] for component in stack["components"]]
        self.assertEqual(EXPECTED_COMPONENTS, set(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_n8n_cannot_write_to_observability_or_openbao(self) -> None:
        stack = load_stack()
        for component in stack["components"]:
            self.assertNotIn(component["n8n_access"], {"WRITE", "ADMIN", "DIRECT_API"})
        forbidden = "\n".join(stack["forbidden_flows"]).lower()
        self.assertIn("n8n -> openbao api", forbidden)
        self.assertIn("n8n -> grafana write api", forbidden)
        self.assertIn("n8n -> prometheus write api", forbidden)
        self.assertIn("n8n embeds observability credentials", forbidden)

    def test_postgres_exporter_is_explicitly_blocked_until_repo_head_is_published(self) -> None:
        stack = load_stack()
        postgres = next(component for component in stack["components"] if component["id"] == "postgres_exporter")
        self.assertIsNone(postgres["remote_head"])
        self.assertEqual("BLOCKED_REPOSITORY_EMPTY_OR_NO_DEFAULT_BRANCH", postgres["status"])


if __name__ == "__main__":
    unittest.main()
