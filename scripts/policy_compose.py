"""Static fail-closed checks for the non-applying n8n Compose template."""

from __future__ import annotations

import re
from pathlib import Path

REQUIRED_TOKENS = {
    "${N8N_IMAGE:?": "explicit immutable image input",
    "staging-after-runtime-verification": "verification-only profile",
    'restart: "no"': "non-autostarting source template",
    "EXECUTIONS_MODE: queue": "queue execution mode",
    'read_only: true': "read-only root filesystem",
    'user: "1000:1000"': "non-root numeric user",
    "cap_drop:": "Linux capability drop",
    "- ALL": "all Linux capabilities dropped",
    "no-new-privileges:true": "no-new-privileges",
    'N8N_BLOCK_ENV_ACCESS_IN_NODE: "true"': "blocked workflow environment access",
    'N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES: "true"': "blocked n8n-file access",
    'N8N_PUBLIC_API_DISABLED: "true"': "disabled public API",
    'N8N_PUBLIC_API_SWAGGERUI_DISABLED: "true"': "disabled API playground",
    'N8N_COMMUNITY_PACKAGES_ENABLED: "false"': "disabled community packages",
    "N8N_DEFAULT_BINARY_DATA_MODE: database": "queue-compatible binary storage",
    'OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS: "true"': "worker-only manual execution",
    'QUEUE_HEALTH_CHECK_ACTIVE: "true"': "worker readiness endpoint",
    'QUEUE_HEALTH_CHECK_PORT: "5680"': "dedicated worker health-check port",
    "http://127.0.0.1:5678/healthz/readiness": "main readiness check",
    "http://127.0.0.1:5680/healthz/readiness": "worker database/Redis readiness check",
    "external: true": "externally provisioned network/secrets",
}
PROHIBITED = (
    (r"^\s*ports:\s*$", "host-published ports"),
    (r"^\s*privileged:\s*true\s*$", "privileged containers"),
    (r"^\s*(?:network_mode|pid|ipc):\s*host\s*$", "host namespace access"),
    (r"docker\.sock", "Docker socket mount"),
    (r"^\s*env_file:\s*", "unreviewed env_file loading"),
    (r"^\s*build:\s*", "source image build"),
    (r"image:\s*[^\n]+:latest(?:\s|$)", "mutable latest image tag"),
)


def validate_compose(path: Path, excluded_nodes: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors = [
        f"Compose template lacks {label}"
        for token, label in REQUIRED_TOKENS.items()
        if token not in text
    ]
    for pattern, label in PROHIBITED:
        if re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE):
            errors.append(f"Compose template contains prohibited {label}")
    missing = sorted(node for node in excluded_nodes if node not in text)
    if missing:
        errors.append("Compose NODES_EXCLUDE misses: " + ", ".join(missing))
    return errors
