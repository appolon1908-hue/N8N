#!/usr/bin/env python3
"""Emit a non-secret, fail-closed read-back of effective n8n controls."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Iterable


CONTROL_NAMES = (
    "LIVE_ADVERTISING_ENABLED",
    "EXTERNAL_DELIVERY_ENABLED",
    "SOCIAL_PUBLISHING_ENABLED",
    "EXTERNAL_MODEL_CALLS_ENABLED",
    "N8N_EXTERNAL_PROVIDER_WRITES",
)


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


def emit_inspection_failure(container: str, error: str) -> None:
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "container": container,
                "source": "docker.inspect.Config.Env",
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
            ["docker", "inspect", "--format", "{{json .Config.Env}}", args.container],
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
        entries = json.loads(result.stdout)
    except json.JSONDecodeError:
        entries = None
    if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
        emit_inspection_failure(args.container, "container environment is malformed")
        return 1
    controls, missing, non_false = read_controls(entries)
    passed = not missing and not non_false
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "container": args.container,
                "source": "docker.inspect.Config.Env",
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
