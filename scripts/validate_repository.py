#!/usr/bin/env python3
"""Validate repository-wide safety invariants without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEX_SHA = re.compile(r"^[0-9a-f]{40}$")
USES_LINE = re.compile(r"^\s*-?\s*uses:\s*[^#\s]+@([^\s#]+)")
BANNED_WORKFLOW_PATTERNS = {
    r"\bssh\b": "remote shell",
    r"\bscp\b": "remote copy",
    r"\brsync\b": "remote synchronization",
    r"docker\s+compose\s+up": "Compose apply",
    r"docker\s+stack\s+deploy": "Docker stack apply",
    r"\bsystemctl\b": "service mutation",
    r"kubectl\s+(?:apply|delete|patch|replace)": "Kubernetes mutation",
    r"docker\.sock": "Docker socket access",
    r"appleboy/ssh-action": "third-party SSH action",
}


def load_json(path: str) -> Any:
    with (ROOT / path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    errors: list[str] = []

    runtime = load_json("config/runtime-paths.json")
    capabilities = load_json("config/capabilities.json")
    services = load_json("config/services.json")
    products = load_json("config/products.json")
    catalog = load_json("automations/catalog.json")

    runtime_status = runtime.get("status")
    if runtime_status not in {"UNVERIFIED", "VERIFIED"}:
        errors.append(f"runtime status is invalid: {runtime_status!r}")

    capability_map = capabilities.get("capabilities", {})
    if not isinstance(capability_map, dict) or not capability_map:
        errors.append("capability map is missing or empty")
    if runtime_status != "VERIFIED":
        enabled = sorted(name for name, value in capability_map.items() if value is not False)
        if enabled:
            errors.append(
                "runtime paths are unverified but capabilities are not false: " + ", ".join(enabled)
            )
        if capabilities.get("safety_mode") != "SOURCE_ONLY":
            errors.append("unverified runtime requires safety_mode=SOURCE_ONLY")

    service_rows = services.get("services", [])
    allowed = [row for row in service_rows if row.get("access_from_n8n") != "DENY_DIRECT"]
    if len(allowed) != 1 or allowed[0].get("id") != "codestra-middleware":
        errors.append("only codestra-middleware may be reachable directly from n8n")
    for row in service_rows:
        if row.get("direct_database_access") is not False:
            errors.append(f"service {row.get('id')} permits direct database access")
        if row.get("runtime_status") not in {"UNVERIFIED", "VERIFIED"}:
            errors.append(f"service {row.get('id')} has invalid runtime status")

    product_ids = {row.get("id") for row in products.get("products", [])}
    for row in products.get("products", []):
        if row.get("status") != "DESIGN_ONLY":
            errors.append(f"product {row.get('id')} is not DESIGN_ONLY")

    if catalog.get("default_activation") != "DISABLED":
        errors.append("automation catalog default activation must be DISABLED")
    seen_automation_ids: set[str] = set()
    for row in catalog.get("automations", []):
        automation_id = row.get("id")
        if not automation_id or automation_id in seen_automation_ids:
            errors.append(f"duplicate or missing automation id: {automation_id!r}")
        seen_automation_ids.add(automation_id)
        if row.get("product") not in product_ids:
            errors.append(f"automation {automation_id} references an unknown product")
        if row.get("state") != "DESIGN_ONLY":
            errors.append(f"automation {automation_id} is not DESIGN_ONLY")
        route = row.get("middleware_route", "")
        if not isinstance(route, str) or not route.startswith("/v1/"):
            errors.append(f"automation {automation_id} lacks a versioned middleware route")

    workflow_dir = ROOT / ".github" / "workflows"
    for workflow_path in sorted(workflow_dir.glob("*.yml")):
        text = workflow_path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            match = USES_LINE.match(line)
            if match and not HEX_SHA.fullmatch(match.group(1)):
                errors.append(
                    f"{workflow_path.relative_to(ROOT)}:{number} action is not pinned to a 40-char SHA"
                )
        lowered = text.lower()
        for pattern, label in BANNED_WORKFLOW_PATTERNS.items():
            if re.search(pattern, lowered):
                errors.append(
                    f"{workflow_path.relative_to(ROOT)} contains prohibited {label} capability"
                )

    compose_path = ROOT / "deploy" / "compose" / "compose.staging.yml"
    compose_text = compose_path.read_text(encoding="utf-8")
    if "${N8N_IMAGE:?" not in compose_text:
        errors.append("Compose template does not require an explicit image reference")
    if re.search(r"^\s*ports:\s*$", compose_text, flags=re.MULTILINE):
        errors.append("Compose template must not publish a host port before runtime verification")
    if "profiles:" not in compose_text or "staging-after-runtime-verification" not in compose_text:
        errors.append("Compose template is not protected by the verification-only profile")

    if errors:
        print("REPOSITORY_VALIDATION=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1

    print("REPOSITORY_VALIDATION=PASS")
    print(f"RUNTIME_PATHS={runtime_status}")
    print("LIVE_SERVER_MUTATION_CAPABILITY=ABSENT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
