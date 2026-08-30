from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from operations import runtime_path_audit


class RuntimePathAuditTests(unittest.TestCase):
    def test_component_filter_excludes_unrelated_compose_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            n8n = root / "n8n-staging"
            odoo = root / "odoo-staging"
            n8n.mkdir()
            odoo.mkdir()
            (n8n / "compose.yaml").touch()
            (odoo / "compose.yaml").touch()
            with mock.patch.object(runtime_path_audit, "SEARCH_ROOTS", (root,)):
                candidates = runtime_path_audit.find_candidates(component="n8n")
        self.assertEqual([str(n8n / "compose.yaml")], [row["path"] for row in candidates])

    def test_candidate_limit_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(3):
                candidate = root / f"n8n-{index}"
                candidate.mkdir()
                (candidate / "compose.yaml").touch()
            with mock.patch.object(runtime_path_audit, "SEARCH_ROOTS", (root,)):
                candidates = runtime_path_audit.find_candidates(
                    component="n8n",
                    max_results=2,
                )
        self.assertEqual(2, len(candidates))

    def test_explicit_active_compose_paths_survive_component_filter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generic = root / "compose.yaml"
            generic.touch()
            with mock.patch.object(runtime_path_audit, "SEARCH_ROOTS", (root,)):
                candidates = runtime_path_audit.find_candidates(
                    component="n8n", explicit_paths=(generic,)
                )
        self.assertEqual([str(generic)], [row["path"] for row in candidates])

    def test_non_n8n_component_excludes_n8n_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".n8n").mkdir()
            with mock.patch.object(runtime_path_audit, "SEARCH_ROOTS", (root,)):
                candidates = runtime_path_audit.find_candidates(component="odoo")
        self.assertEqual([], candidates)

    def test_active_compose_paths_come_from_container_labels(self) -> None:
        inventory = {"containers": [{"compose_labels": {
            "com.docker.compose.project.config_files": "/opt/app/compose.yaml,/opt/app/override.yaml"
        }}]}
        self.assertEqual(
            (Path("/opt/app/compose.yaml"), Path("/opt/app/override.yaml")),
            runtime_path_audit.active_compose_paths(inventory),
        )

    def test_component_container_filter_uses_name_not_incidental_image_tag(self) -> None:
        listing = "\n".join(
            (
                "one\tcodestra-n8n-1\tn8nio/n8n:2.36.8\tUp 1 hour",
                "two\tcodestra-worker-1\tcodestra/middleware:preflight-n8n-auth\tUp 1 hour",
                "three\tcodestra-n8n-old\tn8nio/n8n:old\tExited (0) 1 day ago",
            )
        )

        def fake_run(command: list[str], timeout: int = 10) -> tuple[int, str]:
            if command[:3] == ["docker", "ps", "-a"]:
                return 0, listing
            return 1, "unavailable"

        with mock.patch.object(runtime_path_audit, "run", side_effect=fake_run):
            inventory = runtime_path_audit.docker_inventory("n8n", running_only=True)
        self.assertEqual(["codestra-n8n-1"], [row["name"] for row in inventory["containers"]])


if __name__ == "__main__":
    unittest.main()
