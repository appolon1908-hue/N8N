#!/usr/bin/env python3
"""Validate exact n8n v2 family-client ownership across source contracts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELLS = ROOT / "config" / "automation-cells.v2.json"
POLICY = ROOT / "contracts" / "operation-policy.v2.json"
CATALOG = ROOT / "automations" / "catalog.v2.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(cells: dict, policy: dict, catalog: dict) -> None:
    if cells.get("schema_version") != "2.0" or cells.get("state") != "DESIGN_ONLY":
        raise ValueError("automation cells must remain v2 DESIGN_ONLY")
    invariants = cells.get("invariants", {})
    required_false = {
        "direct_provider_access", "direct_database_access", "public_n8n_webhooks",
        "workflows_active_in_git", "credentials_in_git",
    }
    if set(invariants) != required_false or any(value is not False for value in invariants.values()):
        raise ValueError("automation cell safety invariants must be exact and false")

    clients = policy.get("clients", {})
    if not isinstance(clients, dict) or not clients:
        raise ValueError("canonical client policy is missing")
    owners: dict[str, str] = {}
    declared_families: set[str] = set()
    rows = cells.get("cells")
    if not isinstance(rows, list) or not rows:
        raise ValueError("automation cells are missing")
    for cell in rows:
        cell_id = cell.get("id")
        machine_clients = cell.get("machine_clients")
        families = cell.get("workflow_families")
        if not isinstance(cell_id, str) or not isinstance(machine_clients, list) or not machine_clients:
            raise ValueError("cell must own an explicit non-empty machine_clients list")
        if "machine_client" in cell:
            raise ValueError(f"legacy aggregate machine_client remains in {cell_id}")
        if len(machine_clients) != len(set(machine_clients)):
            raise ValueError(f"duplicate client in {cell_id}")
        if not isinstance(families, list) or len(families) != len(set(families)):
            raise ValueError(f"invalid workflow family inventory in {cell_id}")
        expected_families: set[str] = set()
        for client_id in machine_clients:
            if client_id not in clients:
                raise ValueError(f"unknown machine client {client_id}")
            if client_id in owners:
                raise ValueError(f"machine client {client_id} is shared by multiple cells")
            owners[client_id] = cell_id
            expected_families.update(clients[client_id].get("workflow_families", []))
        if set(families) != expected_families:
            raise ValueError(f"workflow family/client drift in {cell_id}")
        overlap = declared_families.intersection(families)
        if overlap:
            raise ValueError(f"workflow families shared across cells: {sorted(overlap)}")
        declared_families.update(families)
    if set(owners) != set(clients):
        raise ValueError("not every canonical client has exactly one cell owner")

    profiles = catalog.get("authorization_profiles", {})
    for profile_name, profile in profiles.items():
        client_id = profile.get("machine_client")
        if client_id not in clients:
            raise ValueError(f"profile {profile_name} references unknown client")
        if not set(profile.get("additional_scopes", [])).issubset(set(clients[client_id].get("scopes", []))):
            raise ValueError(f"profile {profile_name} grants scope outside client policy")
        if not set(profile.get("command_prefixes", [])).issubset(set(clients[client_id].get("command_prefixes", []))):
            raise ValueError(f"profile {profile_name} grants command prefix outside client policy")

    workflows = catalog.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        raise ValueError("workflow catalog is missing")
    for workflow in workflows:
        workflow_id = workflow.get("id")
        profile_name = workflow.get("authorization_profile")
        if profile_name not in profiles:
            raise ValueError(f"workflow {workflow_id} references unknown profile")
        profile = profiles[profile_name]
        family = workflow.get("workflow_family_override", profile.get("workflow_family"))
        client_id = profile["machine_client"]
        if family not in clients[client_id].get("workflow_families", []):
            raise ValueError(f"workflow {workflow_id} family is outside {client_id} authority")
        if workflow.get("active") is not False or workflow.get("state") != "DESIGN_ONLY":
            raise ValueError(f"workflow {workflow_id} is not inactive DESIGN_ONLY")
        if workflow.get("direct_service_access") is not False:
            raise ValueError(f"workflow {workflow_id} permits direct service access")


def main() -> int:
    validate(load(CELLS), load(POLICY), load(CATALOG))
    print("N8N_V2_FAMILY_CLIENT_AUTHORITY=PASS")
    print("N8N_V2_RUNTIME_APPLY_AUTHORIZED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
