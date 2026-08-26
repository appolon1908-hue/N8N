#!/usr/bin/env python3
"""Verify an immutable, independently approved release tuple; never deploy it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST = re.compile(r"^[^\s]+@sha256:[0-9a-f]{64}$")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--target", choices=("staging", "production"), required=True)
    args = parser.parse_args()

    manifest_path = args.path if args.path.is_absolute() else ROOT / args.path
    if not manifest_path.exists():
        print("RELEASE_PREFLIGHT=FAIL")
        print(f"ERROR=release manifest does not exist: {manifest_path}")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if manifest.get("deployment_mode") != "preflight-only":
        errors.append("deployment_mode must be preflight-only in this repository")
    if manifest.get("target") != args.target:
        errors.append("manifest target does not match requested target")

    source_sha = str(manifest.get("source_sha", ""))
    if not GIT_SHA.fullmatch(source_sha):
        errors.append("source_sha is not a full Git SHA")
    actual_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()
    if source_sha != actual_sha:
        errors.append(f"source_sha {source_sha!r} does not match checked-out SHA {actual_sha!r}")

    if not IMAGE_DIGEST.fullmatch(str(manifest.get("image", ""))):
        errors.append("image must be an immutable sha256 digest reference")
    for field in ("sbom_sha256", "provenance_sha256"):
        value = str(manifest.get(field, ""))
        if not SHA256.fullmatch(value) or set(value) == {"0"}:
            errors.append(f"{field} must be a non-placeholder SHA-256")
    if manifest.get("signature_verified") is not True:
        errors.append("signature verification is not recorded as true")

    runtime_path = ROOT / "config" / "runtime-paths.json"
    capabilities_path = ROOT / "config" / "capabilities.json"
    if manifest.get("runtime_paths_sha256") != digest(runtime_path):
        errors.append("runtime_paths_sha256 does not match the reviewed file")
    if manifest.get("capabilities_sha256") != digest(capabilities_path):
        errors.append("capabilities_sha256 does not match the reviewed file")

    requested_by = manifest.get("requested_by")
    approved_by = manifest.get("approved_by")
    if manifest.get("approval_status") != "APPROVED":
        errors.append("approval_status is not APPROVED")
    if not requested_by or not approved_by or requested_by in {"UNSET", approved_by}:
        errors.append("release requires an independent approver distinct from requester")
    if not IMAGE_DIGEST.fullmatch(str(manifest.get("rollback_release", ""))):
        errors.append("rollback_release must be a previously approved immutable digest")

    capabilities = json.loads(capabilities_path.read_text(encoding="utf-8"))["capabilities"]
    enabled = sorted(name for name, value in capabilities.items() if value is not False)
    if enabled:
        errors.append("preflight scaffold requires all external-effect capabilities false")

    if errors:
        print("RELEASE_PREFLIGHT=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1
    print("RELEASE_PREFLIGHT=PASS")
    print("DEPLOYMENT_PERFORMED=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
