from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import verify_runtime_paths


ROOT = Path(__file__).resolve().parents[1]


class RuntimePathTargetPolicyTests(unittest.TestCase):
    def test_committed_runtime_paths_are_verified_for_each_deployment_target(self) -> None:
        data = json.loads((ROOT / "config" / "runtime-paths.json").read_text())
        for target in ("production", "staging"):
            with self.subTest(target=target):
                self.assertEqual(
                    [],
                    verify_runtime_paths.validate(
                        data,
                        require_verified=True,
                        target=target,
                    ),
                )

    def test_staging_target_rejects_missing_staging_compose_evidence(self) -> None:
        data = json.loads((ROOT / "config" / "runtime-paths.json").read_text())
        data["paths"] = [
            row for row in data["paths"] if row["id"] != "staging_n8n_compose"
        ]
        errors = verify_runtime_paths.validate(
            data,
            require_verified=True,
            target="staging",
        )
        self.assertIn(
            "target staging lacks required path staging_n8n_compose",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
