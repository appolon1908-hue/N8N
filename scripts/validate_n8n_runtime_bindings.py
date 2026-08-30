#!/usr/bin/env python3
"""Validate the server-facing n8n runtime binding state."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = ROOT / "config" / "n8n-runtime-bindings.env"

EXPECTED_BINDINGS = {
    "N8N_ENDPOINT_BINDING": "UNVERIFIED",
    "N8N_CREDENTIAL_BINDING": "UNVERIFIED",
    "N8N_EDITOR_BINDING": "UNVERIFIED",
    "N8N_POLICY_BINDING": "PENDING_RUNTIME_VALIDATION",
    "N8N_WORKFLOW_ACTIVATION": "false",
}


def parse_env(text: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    errors: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            errors.append(f"line {line_number} is not KEY=VALUE")
            continue
        key, value = line.split("=", 1)
        if key != key.strip() or value != value.strip():
            errors.append(f"line {line_number} contains surrounding whitespace")
        key = key.strip()
        value = value.strip()
        if not key.startswith("N8N_"):
            errors.append(f"line {line_number} contains non-n8n key {key!r}")
        if key in values:
            errors.append(f"line {line_number} duplicates {key}")
        if any(marker in value.lower() for marker in ("secret", "token", "password", "keycloak", "smtp://")):
            errors.append(f"line {line_number} may contain a credential-bearing value")
        values[key] = value
    return values, errors


def validate(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    missing = sorted(set(EXPECTED_BINDINGS) - set(values))
    extra = sorted(set(values) - set(EXPECTED_BINDINGS))
    if missing:
        errors.append("missing runtime bindings: " + ", ".join(missing))
    if extra:
        errors.append("unexpected runtime bindings: " + ", ".join(extra))
    for key, expected in EXPECTED_BINDINGS.items():
        actual = values.get(key)
        if actual != expected:
            errors.append(f"{key} must remain {expected}, got {actual!r}")
    return errors


def main() -> int:
    try:
        text = BINDINGS_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        print("N8N_RUNTIME_BINDINGS=FAIL")
        print(f"ERROR=runtime binding file cannot be read: {exc}")
        return 1

    values, errors = parse_env(text)
    errors.extend(validate(values))
    if errors:
        print("N8N_RUNTIME_BINDINGS=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1

    print("N8N_RUNTIME_BINDINGS=PASS")
    for key in EXPECTED_BINDINGS:
        print(f"{key}={values[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
