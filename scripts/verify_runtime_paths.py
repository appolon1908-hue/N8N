#!/usr/bin/env python3
"""Validate the reviewed runtime-path state file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_PATH_STATES = {"UNVERIFIED", "CANDIDATE", "VERIFIED"}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--allow-unverified", action="store_true")
    group.add_argument("--require-verified", action="store_true")
    args = parser.parse_args()

    path = ROOT / "config" / "runtime-paths.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []

    status = data.get("status")
    if status not in {"UNVERIFIED", "VERIFIED"}:
        errors.append(f"invalid overall status {status!r}")

    seen: set[str] = set()
    for row in data.get("paths", []):
        path_id = row.get("id")
        if not path_id or path_id in seen:
            errors.append(f"duplicate or missing path id {path_id!r}")
        seen.add(path_id)
        row_status = row.get("status")
        if row_status not in ALLOWED_PATH_STATES:
            errors.append(f"path {path_id} has invalid status {row_status!r}")
        expected = row.get("expected")
        if expected is not None:
            if not isinstance(expected, str) or not expected.startswith("/"):
                errors.append(f"path {path_id} expected value must be absolute")
            if any(character in expected for character in ("\n", "\r", "\x00")):
                errors.append(f"path {path_id} expected value contains control characters")

    if args.require_verified:
        if status != "VERIFIED":
            errors.append("runtime paths are not VERIFIED")
        for field in ("verified_at", "verified_by", "independent_reviewer"):
            if not data.get(field):
                errors.append(f"verified runtime state requires {field}")
        if not SHA256.fullmatch(str(data.get("evidence_sha256", ""))):
            errors.append("verified runtime state requires an evidence SHA-256")
        server = data.get("server", {})
        if server.get("status") != "VERIFIED" or not server.get("expected_hostname"):
            errors.append("verified runtime state requires verified server hostname")
        for row in data.get("paths", []):
            if row.get("required") and row.get("status") != "VERIFIED":
                errors.append(f"required path {row.get('id')} is not VERIFIED")
            if row.get("required") and not row.get("expected"):
                errors.append(f"required path {row.get('id')} has no expected value")
            if row.get("required") and not SHA256.fullmatch(str(row.get("evidence_sha256", ""))):
                errors.append(f"required path {row.get('id')} lacks evidence SHA-256")
    else:
        if status == "UNVERIFIED":
            for field in ("verified_at", "verified_by", "independent_reviewer", "evidence_sha256"):
                if data.get(field) is not None:
                    errors.append(f"unverified runtime state must not claim {field}")

    if errors:
        print("RUNTIME_PATH_VALIDATION=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1
    print("RUNTIME_PATH_VALIDATION=PASS")
    print(f"RUNTIME_PATHS={status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
