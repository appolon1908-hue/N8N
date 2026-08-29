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
WORKFLOW_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*\.v[1-9][0-9]*$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
DATABASE_NODE_TOKENS = ("postgres", "mysql", "mariadb", "mongodb", "redis")
FORBIDDEN_DIRECT_NODE_TOKENS = DATABASE_NODE_TOKENS + (
    "odoo",
    "emailSend",
    "smtp",
    "smpp",
    "twilio",
)
MANIFEST_REQUIRED_KEYS = {
    "schema_version",
    "system",
    "repository",
    "lane",
    "risk_tier",
    "human_review_required",
    "authority",
    "integration_boundary",
    "n8n",
    "events",
    "commands",
    "workflows",
    "capabilities",
    "data_classification",
    "invariants",
}
MANIFEST_OPTIONAL_KEYS = {
    "legacy_repository",
    "frontend_repository",
    "canonical_source_state",
    "risk_review_status",
    "risk_review_reason",
}
DATA_CLASSIFICATION_KEYS = {
    "handles_pii",
    "handles_financial_data",
    "handles_health_data",
    "regulated_under",
    "retention_days",
}
HIGH_TOUCH_RISK_TIERS = {"critical", "high", "medium_high", "tbd"}


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
    event_owners: dict[str, str],
    command_owners: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    fixed_n8n = registry["fixed_n8n"]
    fixed_invariants = registry["fixed_invariants"]
    risk_tiers = set(registry["risk_tiers"])
    keys = set(manifest)
    allowed_keys = MANIFEST_REQUIRED_KEYS | MANIFEST_OPTIONAL_KEYS

    missing = sorted(MANIFEST_REQUIRED_KEYS - keys)
    extra = sorted(keys - allowed_keys)
    if missing:
        errors.append(f"{system}: missing manifest keys: {', '.join(missing)}")
    if extra:
        errors.append(f"{system}: unsupported manifest keys: {', '.join(extra)}")

    if manifest.get("schema_version") != "1.0":
        errors.append(f"{system}: schema_version must be 1.0")
    if manifest.get("system") != system:
        errors.append(f"{system}: manifest system does not match registry")
    repository = manifest.get("repository")
    if not isinstance(repository, str) or REPOSITORY_RE.fullmatch(repository) is None:
        errors.append(f"{system}: repository must be an owner/repo slug")
    for field in ("legacy_repository", "frontend_repository"):
        value = manifest.get(field)
        if value is not None and (not isinstance(value, str) or REPOSITORY_RE.fullmatch(value) is None):
            errors.append(f"{system}: {field} must be an owner/repo slug")
    if manifest.get("risk_tier") not in risk_tiers:
        errors.append(f"{system}: unsupported risk_tier {manifest.get('risk_tier')!r}")
    if manifest.get("integration_boundary") != "codestra-middleware-only":
        errors.append(f"{system}: integration_boundary must be codestra-middleware-only")
    if manifest.get("n8n") != fixed_n8n:
        errors.append(f"{system}: n8n block must match fixed registry baseline")
    elif not all(isinstance(value, bool) or key == "role" for key, value in manifest["n8n"].items()):
        errors.append(f"{system}: n8n guard fields must be booleans")
    if manifest.get("invariants") != fixed_invariants:
        errors.append(f"{system}: invariants block must match fixed registry baseline")
    elif not all(isinstance(value, bool) for value in manifest["invariants"].values()):
        errors.append(f"{system}: invariant fields must be booleans")

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
        elif len(values) != len(set(values)):
            errors.append(f"{system}: {field} must not contain duplicates")

    for field in ("events", "commands"):
        for value in manifest.get(field, []):
            if NAME_RE.fullmatch(value) is None or not value.startswith(system + "."):
                errors.append(f"{system}: invalid {field[:-1]} name {value!r}")
            owners = event_owners if field == "events" else command_owners
            owner = owners.setdefault(value, system)
            if owner != system:
                errors.append(f"{system}: {field[:-1]} {value!r} already owned by {owner}")

    for workflow in manifest.get("workflows", []):
        if WORKFLOW_RE.fullmatch(workflow) is None:
            errors.append(f"{system}: invalid workflow name {workflow!r}")
        owner = workflow_owners.setdefault(workflow, system)
        if owner != system:
            errors.append(f"{system}: workflow {workflow!r} already owned by {owner}")

    if manifest.get("risk_tier") in HIGH_TOUCH_RISK_TIERS and manifest.get("human_review_required") is not True:
        errors.append(f"{system}: high-touch risk manifests require human_review_required=true")
    if manifest.get("risk_tier") == "tbd":
        if manifest.get("risk_review_status") != "REQUIRES_ENUMERATION":
            errors.append(f"{system}: tbd risk requires risk_review_status=REQUIRES_ENUMERATION")
        if not isinstance(manifest.get("risk_review_reason"), str) or not manifest["risk_review_reason"].strip():
            errors.append(f"{system}: tbd risk requires risk_review_reason")

    classification = manifest.get("data_classification")
    if not isinstance(classification, dict):
        errors.append(f"{system}: data_classification must be an object")
    else:
        if set(classification) != DATA_CLASSIFICATION_KEYS:
            errors.append(f"{system}: data_classification keys do not match the standard")
        for field in ("handles_pii", "handles_financial_data", "handles_health_data"):
            if not isinstance(classification.get(field), bool):
                errors.append(f"{system}: data_classification.{field} must be boolean")
        if not isinstance(classification.get("regulated_under"), list):
            errors.append(f"{system}: data_classification.regulated_under must be a list")
        retention = classification.get("retention_days")
        if retention is not None and (not isinstance(retention, int) or retention <= 0):
            errors.append(f"{system}: data_classification.retention_days must be a positive integer or null")
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
    if workflow.get("active") is not False:
        errors.append(f"{path}: workflow active must be false")
    if "credentials" in workflow:
        errors.append(f"{path}: workflow must not contain credentials")

    for node in workflow.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type", ""))
        lowered = node_type.lower()
        if any(token.lower() in lowered for token in FORBIDDEN_DIRECT_NODE_TOKENS):
            errors.append(f"{path}: forbidden direct node type {node_type}")
        if "credentials" in node:
            errors.append(f"{path}: node {node.get('name', node.get('id', '<unnamed>'))} must not contain credentials")
        parameters = node.get("parameters", {})
        if not isinstance(parameters, dict):
            continue
        url = parameters.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            if parsed.scheme != "https":
                errors.append(f"{path}: HTTP node target must use https")
            if host not in allowed_http_hosts:
                errors.append(f"{path}: HTTP node targets non-Middleware host {host}")
            if "odoo" in host.lower():
                errors.append(f"{path}: workflow references Odoo directly through host {host}")
    return errors


def workflow_exports(root: Path) -> tuple[dict[str, Path], list[str]]:
    exports: dict[str, Path] = {}
    errors: list[str] = []
    for path in sorted((root / "workflows").rglob("*.json")):
        try:
            workflow = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: cannot parse workflow JSON while indexing exports: {exc}")
            continue
        if not isinstance(workflow, dict):
            errors.append(f"{path}: workflow root must be an object while indexing exports")
            continue
        name = workflow.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{path}: workflow export is missing a string name")
            continue
        owner = exports.setdefault(name, path)
        if owner != path:
            errors.append(f"{path}: workflow export name {name!r} already exists at {owner}")
    return exports, errors


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
    if len(domain_systems) != 14:
        errors.append("registry must list exactly 14 domain systems")
    if len(domain_systems) != len(set(domain_systems)):
        errors.append("registry domain systems must be unique")
    if sorted(registry.get("risk_tiers", [])) != sorted(["critical", "high", "medium_high", "medium", "low", "tbd"]):
        errors.append("registry risk_tiers must match the approved enum")

    exported_workflows, export_errors = workflow_exports(root)
    errors.extend(export_errors)
    workflow_owners: dict[str, str] = {}
    event_owners: dict[str, str] = {}
    command_owners: dict[str, str] = {}
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
                event_owners=event_owners,
                command_owners=command_owners,
            )
        )

    allowed_http_hosts = set(registry.get("tier3_http_hosts_allowed_from_n8n", []))
    for path in sorted((root / "workflows").rglob("*.json")):
        errors.extend(validate_workflow_file(path, allowed_http_hosts))
    for workflow, system in sorted(workflow_owners.items()):
        if workflow not in exported_workflows:
            errors.append(f"{system}: workflow {workflow!r} has no committed workflow export")
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
