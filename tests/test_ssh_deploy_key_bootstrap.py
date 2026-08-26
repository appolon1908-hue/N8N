from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "bootstrap_github_deploy_key.sh"


class SshDeployKeyBootstrapSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_shell_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.returncode)

    def test_deploy_key_is_explicitly_read_only(self) -> None:
        self.assertIn("-F read_only=true", self.text)
        self.assertNotIn("read_only=false", self.text)
        self.assertIn("DEPLOY_KEY_MODE=READ_ONLY", self.text)

    def test_private_key_is_not_uploaded_or_printed(self) -> None:
        self.assertIn('-f "key=${PUBLIC_KEY}"', self.text)
        self.assertNotIn('cat "$KEY_PATH"', self.text)
        self.assertNotIn('printf \'%s\\n\' "$PUBLIC_KEY"', self.text)

    def test_github_host_key_is_pinned_and_strict(self) -> None:
        self.assertIn(
            "SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU",
            self.text,
        )
        self.assertIn("StrictHostKeyChecking yes", self.text)
        self.assertIn("IdentitiesOnly yes", self.text)
        self.assertIn("ForwardAgent no", self.text)

    def test_script_does_not_deploy_or_change_a_checkout(self) -> None:
        lowered = self.text.lower()
        for prohibited in (
            "git clone",
            "git pull",
            "git remote set-url",
            "docker compose up",
            "systemctl",
            "kubectl apply",
            "rsync ",
            "scp ",
            "workflow import",
        ):
            self.assertNotIn(prohibited, lowered)
        self.assertIn("git ls-remote", lowered)
        self.assertIn("LIVE_APPLICATION_DEPLOYMENT=NO", self.text)


if __name__ == "__main__":
    unittest.main()
