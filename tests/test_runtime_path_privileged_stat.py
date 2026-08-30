from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations import runtime_path_privileged_stat


class PrivilegedRuntimeStatTests(unittest.TestCase):
    def test_metadata_reads_no_contents_and_reports_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            present = root / "present"
            missing = root / "missing"
            present.write_text("must not appear in evidence", encoding="utf-8")
            rows = runtime_path_privileged_stat.metadata((present, missing))
        self.assertEqual(str(present), rows[0]["path"])
        self.assertEqual("file", rows[0]["type"])
        self.assertNotIn("contents", rows[0])
        self.assertEqual("FileNotFoundError", rows[1]["error"])

    def test_allowlist_is_absolute_and_has_no_secret_files(self) -> None:
        self.assertTrue(all(path.as_posix().startswith("/") for path in runtime_path_privileged_stat.ALLOWLIST))
        forbidden_names = {"n8n_db_password", "n8n_encryption_key", "n8n_jwt_secret"}
        self.assertFalse(forbidden_names & {path.name for path in runtime_path_privileged_stat.ALLOWLIST})

    def test_module_does_not_open_machine_identity_content(self) -> None:
        source = Path(runtime_path_privileged_stat.__file__).read_text(encoding="utf-8")
        self.assertNotIn("/etc/machine-id", source)


if __name__ == "__main__":
    unittest.main()
