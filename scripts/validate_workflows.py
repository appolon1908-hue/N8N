#!/usr/bin/env python3
"""Validate committed n8n workflow exports against the middleware-only policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*\.v[1-9][0-9]*$")
FORBIDDEN_NODE_FRAGMENTS = (
    "postgres",
    "mysql",
    "mariadb",
    "redis",
    "mongodb",
    "odoo",
    "ssh",
    "ftp",
    "twilio",
    "emailsend",
)
IP_LITERAL = re.compile(r"(?<![A-Za-z0-9])(?:\d{1,3}\.){3}\d{1,3}(?![A-Za-z0-9])")


def strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot parse JSON: {exc}"]

    name = workflow.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        errors.append("workflow name must match <namespace>.<domain>.<action>.v<major>")
    if workflow.get("active") is not False:
        errors.append("workflow active must be false")
    if workflow.get("pinData") not in ({}, None):
        errors.append("pinData must be empty")
    if "credentials" in workflow:
        errors.append("top-level credential references are prohibited")

    codestra_meta = workflow.get("meta", {}).get("codestra", {})
    if codestra_meta.get("network_policy") != "MIDDLEWARE_ONLY":
        errors.append("meta.codestra.network_policy must be MIDDLEWARE_ONLY")
    if codestra_meta.get("activation_state") != "DISABLED":
        errors.append("meta.codestra.activation_state must be DISABLED")

    nodes = workflow.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty list")
        return errors

    node_ids: set[str] = set()
    node_names: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node {index} is not an object")
            continue
        node_id = node.get("id")
        node_name = node.get("name")
        node_type = str(node.get("type", ""))
        if not node_id or node_id in node_ids:
            errors.append(f"node {index} has a missing or duplicate id")
        node_ids.add(node_id)
        if not node_name or node_name in node_names:
            errors.append(f"node {index} has a missing or duplicate name")
        node_names.add(node_name)

        lowered_type = node_type.lower()
        if any(fragment in lowered_type for fragment in FORBIDDEN_NODE_FRAGMENTS):
            errors.append(f"node {node_name!r} uses prohibited direct-access type {node_type!r}")
        if "webhook" in lowered_type:
            errors.append(f"node {node_name!r} exposes a webhook; callbacks must terminate at middleware")
        if "credentials" in node:
            errors.append(f"node {node_name!r} contains credential references")

        if lowered_type.endswith(".httprequest") or "httprequest" in lowered_type:
            values = list(strings(node.get("parameters", {})))
            urls = [value for value in values if "http" in value.lower() or "MIDDLEWARE_BASE_URL" in value]
            if not urls:
                errors.append(f"HTTP node {node_name!r} has no visible URL expression")
            for value in urls:
                if "MIDDLEWARE_BASE_URL" not in value:
                    errors.append(f"HTTP node {node_name!r} does not use MIDDLEWARE_BASE_URL")
                if IP_LITERAL.search(value):
                    errors.append(f"HTTP node {node_name!r} contains an IP literal")

    serialized = json.dumps(workflow, sort_keys=True).lower()
    for token in ("vicidial", "jasmin", "postal", "keycloak", "kong_admin", "postgresql://", "redis://"):
        if token in serialized:
            errors.append(f"workflow contains prohibited direct-service token {token!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    files = sorted(args.directory.rglob("*.json"))
    if not files:
        print("WORKFLOW_VALIDATION=FAIL")
        print("ERROR=no workflow JSON files found")
        return 1

    failures = 0
    for path in files:
        errors = validate(path)
        if errors:
            failures += 1
            for error in errors:
                print(f"ERROR={path}:{error}")
        else:
            print(f"WORKFLOW_PASS={path}")

    if failures:
        print("WORKFLOW_VALIDATION=FAIL")
        return 1
    print("WORKFLOW_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
