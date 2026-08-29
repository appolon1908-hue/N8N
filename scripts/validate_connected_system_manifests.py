#!/usr/bin/env python3
"""Validate n8n connected-system manifests and workflow boundaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "n8n-connected-systems.v1.json"
NAME_RE = re.compile(r"^[a-z0-9_]+\.[a-z_]+\.[a-z_]+$")
DATABASE_NODE_TOKENS = ("postgres", "mysql", "mariadb", "mongodb", "redis")
FORBIDDEN_DIRECT_NODE_TOKENS = DATABASE_NODE_TOKENS + ("odoo", "emailSend")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_path(system: str) -> Path:
    return ROOT / "systems" / system / "integrations" / "n8n" / "manifest.v1.json"


def validate_manifest(
    manifest: dict[str, Any],
    *,
    system: str,
    registry: dict[str, Any],
    workflow_owners: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    fixed_n8n = registry["fixed_n8n"]
    fixed_invariants = registry["fixed_invariants"]
    risk_tiers = set(registry["risk_tiers"])

    if manifest.get("schema_version") != "1.0":
        errors.append(f"{system}: schema_version must be 1.0")
    if manifest.get("system") != system:
        errors.append(f"{system}: manifest system does not match registry")
    if manifest.get("risk_tier") not in risk_tiers:
        errors.append(f"{system}: unsupported risk_tier {manifest.get('risk_tier')!r}")
    if manifest.get("integration_boundary") != "codestra-middleware-only":
        errors.append(f"{system}: integration_boundary must be codestra-middleware-only")
    if manifest.get("n8n") != fixed_n8n:
        errors.append(f"{system}: n8n block must match fixed registry baseline")
    if manifest.get("invariants") != fixed_invariants:
        errors.append(f"{system}: invariants block must match fixed registry baseline")

    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        errors.append(f"{system}: capabilities must be a non-empty object")
    else:
        enabled = sorted(name for name, value in capabilities.items() if value is not False)
        if enabled:
            errors.append(f"{system}: capabilities default true/non-false: {', '.join(enabled)}")

    for field in ("events", "commands", "workflows"):
        values = manifest.get(field)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):
            errors.append(f"{system}: {field} must be a non-empty string array")

    for field in ("events", "commands"):
        for value in manifest.get(field, []):
            if NAME_RE.fullmatch(value) is None or not value.startswith(system + "."):
                errors.append(f"{system}: invalid {field[:-1]} name {value!r}")

    for workflow in manifest.get("workflows", []):
        owner = workflow_owners.setdefault(workflow, system)
        if owner != system:
            errors.append(f"{system}: workflow {workflow!r} already owned by {owner}")

    if manifest.get("risk_tier") in {"critical", "high"} and manifest.get("human_review_required") is not True:
        errors.append(f"{system}: critical/high risk manifests require human_review_required=true")

    classification = manifest.get("data_classification")
    if not isinstance(classification, dict):
        errors.append(f"{system}: data_classification must be an object")
    else:
        required = {
            "handles_pii",
            "handles_financial_data",
            "handles_health_data",
            "regulated_under",
            "retention_days",
        }
        if set(classification) != required:
            errors.append(f"{system}: data_classification keys do not match the standard")
        if classification.get("handles_financial_data") is True and classification.get("retention_days") is None:
            errors.append(f"{system}: financial data requires retention_days")

    return errors


def validate_workflow_file(path: Path, allowed_http_hosts: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        workflow = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: cannot parse workflow JSON: {exc}"]
    if not isinstance(workflow, dict):
        return [f"{path}: workflow root must be an object"]
    if "credentials" in workflow:
        errors.append(f"{path}: workflow must not contain credentials")

    for node in workflow.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type", ""))
        lowered = node_type.lower()
        if any(token.lower() in lowered for token in FORBIDDEN_DIRECT_NODE_TOKENS):
            errors.append(f"{path}: forbidden direct node type {node_type}")
        parameters = node.get("parameters", {})
        if not isinstance(parameters, dict):
            continue
        url = parameters.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            if host not in allowed_http_hosts:
                errors.append(f"{path}: HTTP node targets non-Middleware host {host}")
            if "odoo" in host.lower():
                errors.append(f"{path}: workflow references Odoo directly through host {host}")
    return errors


def validate(root: Path = ROOT) -> list[str]:
    registry = load_json(root / REGISTRY_PATH.relative_to(ROOT))
    if not isinstance(registry, dict):
        return ["registry root must be an object"]
    errors: list[str] = []
    if registry.get("trunk") != "main":
        errors.append("N8N trunk must be main")
    if registry.get("broadcast_pushes_allowed") is not False:
        errors.append("broadcast pushes must be disallowed in the registry")

    domain_systems = registry.get("tiers", {}).get("domain_systems")
    if not isinstance(domain_systems, list) or not domain_systems:
        errors.append("registry must list domain systems")
        return errors

    workflow_owners: dict[str, str] = {}
    for system in domain_systems:
        path = root / "systems" / system / "integrations" / "n8n" / "manifest.v1.json"
        if not path.is_file():
            errors.append(f"{system}: missing manifest at {path.relative_to(root)}")
            continue
        try:
            manifest = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{system}: cannot read manifest: {exc}")
            continue
        if not isinstance(manifest, dict):
            errors.append(f"{system}: manifest root must be an object")
            continue
        errors.extend(
            validate_manifest(
                manifest,
                system=system,
                registry=registry,
                workflow_owners=workflow_owners,
            )
        )

    allowed_http_hosts = set(registry.get("tier3_http_hosts_allowed_from_n8n", []))
    for path in sorted((root / "workflows").rglob("*.json")):
        errors.extend(validate_workflow_file(path, allowed_http_hosts))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print("CONNECTED_SYSTEM_MANIFESTS=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1
    print("CONNECTED_SYSTEM_MANIFESTS=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
