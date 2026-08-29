#!/usr/bin/env python3
"""Validate the prepared observability and secrets integration contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STACK_PATH = ROOT / "config" / "observability-stack.v1.json"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_COMPONENTS = {
    "grafana",
    "prometheus",
    "alertmanager",
    "loki",
    "tempo",
    "opentelemetry",
    "superset",
    "node_exporter",
    "cadvisor",
    "postgres_exporter",
    "redis_exporter",
    "blackbox_exporter",
    "alloy",
    "openbao",
}
FORBIDDEN_N8N_ACCESS = {"DENY", "DENY_WRITE", "DENY_DIRECT_API", "NO_DIRECT_PUSH"}
LIMITED_N8N_ACCESS = {"READ_ONLY_METRICS", "LOCAL_INSTRUMENTATION_ONLY"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    path = root / STACK_PATH.relative_to(ROOT)
    try:
        stack = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"observability stack cannot be read: {exc}"]
    if not isinstance(stack, dict):
        return ["observability stack root must be an object"]

    if stack.get("schema_version") != "1.0":
        errors.append("observability stack schema_version must be 1.0")
    if stack.get("classification") != "infrastructure-control-plane":
        errors.append("observability stack must be infrastructure-control-plane")
    if stack.get("n8n_domain_system") is not False:
        errors.append("observability stack must not be counted as n8n domain systems")
    if stack.get("integration_state") != "PREPARED_NOT_APPLIED":
        errors.append("observability stack must remain PREPARED_NOT_APPLIED until runtime proof")
    if stack.get("production_changed") is not False:
        errors.append("observability stack cannot mark production_changed=true from source prep")

    requirements = stack.get("runtime_requirements")
    if not isinstance(requirements, dict):
        errors.append("runtime_requirements must be an object")
    else:
        for required in (
            "n8n_metrics_enabled",
            "n8n_direct_provider_logs_forbidden",
            "credentials_in_git",
            "tenant_label_required",
            "workflow_group_label_required",
            "correlation_id_required",
        ):
            if required not in requirements:
                errors.append(f"runtime requirement missing: {required}")
        if requirements.get("credentials_in_git") is not False:
            errors.append("observability credentials must not be stored in Git")
        if requirements.get("secrets_authority") != "openbao":
            errors.append("OpenBao must be the declared secrets authority")

    for field in ("allowed_flows", "forbidden_flows", "required_dashboards", "required_alerts", "blockers"):
        value = stack.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must be a non-empty list")

    components = stack.get("components")
    if not isinstance(components, list):
        errors.append("components must be a list")
        return errors
    ids = [component.get("id") for component in components if isinstance(component, dict)]
    if set(ids) != EXPECTED_COMPONENTS:
        errors.append("observability components must match the approved 14-component stack")
    if len(ids) != len(set(ids)):
        errors.append("observability component ids must be unique")

    for component in components:
        if not isinstance(component, dict):
            errors.append("observability component row must be an object")
            continue
        component_id = component.get("id")
        repository = component.get("repository")
        if not isinstance(repository, str) or REPOSITORY_RE.fullmatch(repository) is None:
            errors.append(f"{component_id}: repository must be an owner/repo slug")
        head = component.get("remote_head")
        status = component.get("status")
        if head is None:
            if status != "BLOCKED_REPOSITORY_UNREACHABLE":
                errors.append(f"{component_id}: null remote_head requires BLOCKED_REPOSITORY_UNREACHABLE")
        elif not isinstance(head, str) or SHA_RE.fullmatch(head) is None:
            errors.append(f"{component_id}: remote_head must be a 40-character SHA")
        access = component.get("n8n_access")
        if access not in FORBIDDEN_N8N_ACCESS | LIMITED_N8N_ACCESS:
            errors.append(f"{component_id}: n8n_access is not an approved value")
        if access == "READ_ONLY_METRICS" and component_id != "prometheus":
            errors.append(f"{component_id}: only Prometheus may read n8n metrics")
        if access == "LOCAL_INSTRUMENTATION_ONLY" and component_id not in {"opentelemetry", "alloy"}:
            errors.append(f"{component_id}: local instrumentation access is limited to OpenTelemetry/Alloy")
        if component.get("secret_source") not in {"openbao", "none", "self"}:
            errors.append(f"{component_id}: secret_source must be openbao, none, or self")

    forbidden = "\n".join(str(item).lower() for item in stack.get("forbidden_flows", []))
    for token in ("openbao api", "grafana write api", "loki push api", "tempo push api"):
        if token not in forbidden:
            errors.append(f"forbidden_flows must explicitly block n8n -> {token}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print("OBSERVABILITY_STACK=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1
    print("OBSERVABILITY_STACK=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
