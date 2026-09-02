#!/usr/bin/env python3
"""Emit a non-secret, fail-closed read-back of effective n8n controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Iterable

try:
    from .policy_n8n import REQUIRED_DANGEROUS_NODES
except ImportError:
    from policy_n8n import REQUIRED_DANGEROUS_NODES  # type: ignore


CONTROL_NAMES = (
    "LIVE_ADVERTISING_ENABLED",
    "EXTERNAL_DELIVERY_ENABLED",
    "SOCIAL_PUBLISHING_ENABLED",
    "EXTERNAL_MODEL_CALLS_ENABLED",
    "N8N_EXTERNAL_PROVIDER_WRITES",
)
ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "umbrella_runtime_guard.sh"
GUARD_TARGET = "/run/configs/codestra_umbrella_guard"
GUARD_DIGEST_LABEL = "com.codestra.n8n.umbrella-guard-sha256"
WRITE_BOUNDARY_LABEL = "com.codestra.n8n.write-boundary"
EXPECTED_PROJECT = "codestra-n8n-staging-template"
EXPECTED_SERVICES = {"n8n-main", "n8n-worker"}
CONFIGURED_IMAGE = re.compile(r"^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$")
RUNTIME_IMAGE = re.compile(r"^sha256:[0-9a-f]{64}$")


def read_controls(entries: Iterable[str]) -> tuple[dict[str, bool | None], list[str], list[str]]:
    selected: dict[str, list[str]] = {name: [] for name in CONTROL_NAMES}
    for entry in entries:
        name, separator, value = entry.partition("=")
        if separator and name in selected:
            selected[name].append(value)

    controls: dict[str, bool | None] = {}
    missing: list[str] = []
    non_false: list[str] = []
    for name in CONTROL_NAMES:
        values = selected[name]
        if not values:
            controls[name] = None
            missing.append(name)
        elif len(values) != 1 or values[0] != "false":
            controls[name] = True if values == ["true"] else None
            non_false.append(name)
        else:
            controls[name] = False
    return controls, missing, non_false


def validate_identity(inspection: dict) -> tuple[dict[str, str | None], list[str]]:
    config = inspection.get("Config")
    mounts = inspection.get("Mounts")
    if not isinstance(config, dict) or not isinstance(mounts, list):
        return {}, ["container inspection identity is malformed"]
    labels = config.get("Labels")
    labels = labels if isinstance(labels, dict) else {}
    service = labels.get("com.docker.compose.service")
    configured_image = config.get("Image")
    runtime_image = inspection.get("Image")
    expected_guard_digest = hashlib.sha256(GUARD_PATH.read_bytes()).hexdigest()
    errors: list[str] = []
    if labels.get("com.docker.compose.project") != EXPECTED_PROJECT:
        errors.append("unexpected Compose project")
    if service not in EXPECTED_SERVICES:
        errors.append("unexpected Compose service")
    if labels.get(GUARD_DIGEST_LABEL) != expected_guard_digest:
        errors.append("umbrella guard digest is not the reviewed source")
    if labels.get(WRITE_BOUNDARY_LABEL) != "disabled-source-only":
        errors.append("write boundary is not disabled-source-only")
    if not isinstance(configured_image, str) or not CONFIGURED_IMAGE.fullmatch(configured_image):
        errors.append("configured image is not immutable")
    if not isinstance(runtime_image, str) or not RUNTIME_IMAGE.fullmatch(runtime_image):
        errors.append("runtime image ID is not immutable")
    if config.get("Entrypoint") != ["/bin/sh", GUARD_TARGET]:
        errors.append("container does not start through the umbrella guard")
    if not any(
        isinstance(mount, dict)
        and mount.get("Destination") == GUARD_TARGET
        and mount.get("RW") is False
        for mount in mounts
    ):
        errors.append("umbrella guard is not mounted read-only")
    return {
        "compose_service": service if isinstance(service, str) else None,
        "configured_image": configured_image if isinstance(configured_image, str) else None,
        "runtime_image_id": runtime_image if isinstance(runtime_image, str) else None,
        "guard_sha256": expected_guard_digest,
    }, errors


def validate_runtime_node_exclusions(entries: Iterable[str]) -> list[str]:
    selected = [entry.partition("=")[2] for entry in entries if entry.startswith("NODES_EXCLUDE=")]
    if len(selected) != 1:
        return ["NODES_EXCLUDE is missing or duplicated"]
    try:
        excluded = json.loads(selected[0])
    except json.JSONDecodeError:
        return ["NODES_EXCLUDE is malformed"]
    if not isinstance(excluded, list) or set(excluded) != REQUIRED_DANGEROUS_NODES:
        return ["effect-capable runtime node exclusions differ from reviewed policy"]
    return []


def emit_inspection_failure(container: str, error: str) -> None:
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "container": container,
                "source": "docker.inspect.Config.Env",
                "identity": {},
                "identity_errors": [error],
                "controls": {name: None for name in CONTROL_NAMES},
                "missing": list(CONTROL_NAMES),
                "non_false": [],
                "pass": False,
                "error": error,
            },
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("container", help="exact n8n container name or ID")
    args = parser.parse_args()
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{json .}}", args.container],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        emit_inspection_failure(args.container, "container inspection unavailable")
        return 1
    if result.returncode != 0:
        emit_inspection_failure(args.container, "container inspection failed")
        return 1
    try:
        inspection = json.loads(result.stdout)
    except json.JSONDecodeError:
        inspection = None
    if not isinstance(inspection, dict):
        emit_inspection_failure(args.container, "container inspection is malformed")
        return 1
    config = inspection.get("Config")
    entries = config.get("Env") if isinstance(config, dict) else None
    if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
        emit_inspection_failure(args.container, "container environment is malformed")
        return 1
    identity, identity_errors = validate_identity(inspection)
    identity_errors.extend(validate_runtime_node_exclusions(entries))
    controls, missing, non_false = read_controls(entries)
    passed = not missing and not non_false and not identity_errors
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "container": args.container,
                "source": "docker.inspect.Config.Env",
                "identity": identity,
                "identity_errors": identity_errors,
                "controls": controls,
                "missing": missing,
                "non_false": non_false,
                "pass": passed,
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
