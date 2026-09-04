#!/usr/bin/env python3
"""Validate the source-only, read-only deploy-key bootstrap contract."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "config" / "ssh-deploy-key-bootstrap.v1.json"
SCRIPT_PATH = ROOT / "ops" / "bootstrap_github_deploy_key.sh"
DOC_PATH = ROOT / "docs" / "ssh-deploy-key-bootstrap.md"
TEST_PATH = ROOT / "tests" / "test_ssh_deploy_key_bootstrap.py"

EXPECTED_FINGERPRINT = "SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU"
EXPECTED_REPOSITORY = "appolon1908-hue/N8N"
EXPECTED_MARKERS = {
    "SSH_DEPLOY_KEY_BOOTSTRAP=PASS",
    "DEPLOY_KEY_MODE=READ_ONLY",
    "SSH_AUTH_IDENTITY=appolon1908-hue/N8N",
    "PRIVATE_KEY_MODE=0600",
    "PUBLIC_KEY_MODE=0644",
    "IDENTITIES_ONLY=yes",
    "STRICT_HOST_KEY_CHECKING=yes",
    "PRIVATE_KEY_EXPORTED=NO",
    "LIVE_APPLICATION_DEPLOYMENT=NO",
    "WORKFLOW_IMPORT=NO",
    "SERVICE_RESTART=NO",
    "LIVE_CAPABILITY_ACTIVATION=NO",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def validate() -> list[str]:
    errors: list[str] = []
    required_paths = (MANIFEST_PATH, SCRIPT_PATH, DOC_PATH, TEST_PATH)
    for path in required_paths:
        if not path.is_file():
            errors.append(f"required deploy-key source is missing: {path.relative_to(ROOT)}")
    if errors:
        return errors

    try:
        manifest = load_json(MANIFEST_PATH)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"deploy-key manifest cannot be loaded: {exc}"]

    if manifest.get("schema_version") != "1.0":
        errors.append("deploy-key manifest schema_version must be 1.0")
    if manifest.get("status") != "SOURCE_READY_SERVER_UNVERIFIED":
        errors.append("deploy-key manifest must remain SOURCE_READY_SERVER_UNVERIFIED")
    if manifest.get("repository") != EXPECTED_REPOSITORY:
        errors.append("deploy-key manifest repository differs from the repository authority")
    if manifest.get("tracking_issue") != 3:
        errors.append("deploy-key manifest must reference issue #3")

    github_ssh = manifest.get("github_ssh")
    if not isinstance(github_ssh, dict):
        errors.append("deploy-key manifest github_ssh section is missing")
    else:
        if github_ssh.get("expected_ed25519_fingerprint") != EXPECTED_FINGERPRINT:
            errors.append("GitHub ED25519 fingerprint differs from the reviewed value")
        if github_ssh.get("strict_host_key_checking") is not True:
            errors.append("strict host-key checking must be required")
        if github_ssh.get("dedicated_known_hosts") is not True:
            errors.append("a dedicated known-hosts file must be required")

    deploy_key = manifest.get("deploy_key")
    if not isinstance(deploy_key, dict):
        errors.append("deploy-key manifest deploy_key section is missing")
    else:
        expected = {
            "repository_scoped": True,
            "read_only": True,
            "private_key_generated_on_target": True,
            "private_key_export_prohibited": True,
            "private_key_mode": "0600",
            "public_key_mode": "0644",
            "identities_only": True,
            "agent_forwarding": False,
        }
        if any(deploy_key.get(key) != value for key, value in expected.items()):
            errors.append("deploy-key security properties differ from the reviewed contract")

    server_validation = manifest.get("server_validation")
    if not isinstance(server_validation, dict):
        errors.append("server_validation section is missing")
    else:
        if server_validation.get("status") != "UNVERIFIED":
            errors.append("server installation may not be claimed before host evidence exists")
        markers = server_validation.get("required_markers")
        if not isinstance(markers, list) or set(markers) != EXPECTED_MARKERS:
            errors.append("server validation markers differ from the reviewed contract")

    runtime_effects = manifest.get("runtime_effects")
    if not isinstance(runtime_effects, dict) or not runtime_effects:
        errors.append("runtime_effects section is missing")
    elif any(value is not False for value in runtime_effects.values()):
        errors.append("deploy-key source may not authorize runtime or external effects")

    script = SCRIPT_PATH.read_text(encoding="utf-8")
    required_script_fragments = {
        'EXPECTED_REPOSITORY="appolon1908-hue/N8N"',
        "-F read_only=true",
        EXPECTED_FINGERPRINT,
        "ssh-keyscan",
        "IdentitiesOnly yes",
        "IdentityAgent none",
        "StrictHostKeyChecking yes",
        "UserKnownHostsFile",
        "ForwardAgent no",
        'chmod 0600 "$KEY_PATH"',
        'chmod 0644 "$PUBLIC_KEY_PATH"',
        "git ls-remote",
        'grep -Fq "Hi ${REPOSITORY}!"',
        "existing GitHub deploy key has write access",
        "PRIVATE_KEY_EXPORTED=NO",
        "LIVE_APPLICATION_DEPLOYMENT=NO",
    }
    for fragment in sorted(required_script_fragments):
        if fragment not in script:
            errors.append(f"bootstrap script lacks reviewed fragment: {fragment}")

    forbidden_patterns = {
        r"\bread_only=false\b": "write-enabled deploy key",
        r'cat\s+["\']?\$KEY_PATH': "private-key output",
        r"\bgit\s+clone\b": "repository clone",
        r"\bgit\s+pull\b": "checkout pull",
        r"\bgit\s+remote\s+set-url\b": "checkout remote mutation",
        r"\bdocker\s+compose\s+up\b": "container deployment",
        r"\bsystemctl\s+(?:start|stop|restart|reload)\b": "service mutation",
        r"\bkubectl\s+(?:apply|delete|patch|replace)\b": "Kubernetes mutation",
        r"\bn8n\s+(?:import|execute)\b": "n8n workflow mutation",
    }
    for pattern, description in forbidden_patterns.items():
        if re.search(pattern, script, flags=re.IGNORECASE):
            errors.append(f"bootstrap script contains prohibited {description}")

    syntax = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if syntax.returncode != 0:
        errors.append(f"bootstrap shell syntax failed: {syntax.stderr.strip()}")

    mode = SCRIPT_PATH.stat().st_mode & 0o777
    if mode != 0o755:
        errors.append(f"bootstrap script repository mode is {mode:04o}, expected 0755")

    documentation = DOC_PATH.read_text(encoding="utf-8")
    documentation_lower = documentation.lower()
    for phrase in (
        "SOURCE_READY_SERVER_UNVERIFIED",
        "one-time `GH_TOKEN`",
        "do not paste, print, upload, or copy the private key",
        "does not clone, pull, restart, import, activate, or deploy",
        "ssh -T",
        "git ls-remote",
    ):
        if phrase.lower() not in documentation_lower:
            errors.append(f"deploy-key documentation lacks required statement: {phrase}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("SSH_DEPLOY_KEY_BOOTSTRAP_SOURCE=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1

    print("SSH_DEPLOY_KEY_BOOTSTRAP_SOURCE=PASS")
    print("REPOSITORY=appolon1908-hue/N8N")
    print("DEPLOY_KEY_MODE=READ_ONLY")
    print("PRIVATE_KEY_GENERATION=TARGET_HOST_ONLY")
    print("SERVER_INSTALLATION=UNVERIFIED")
    print("LIVE_APPLICATION_DEPLOYMENT=NO")
    print("WORKFLOW_ACTIVATION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
