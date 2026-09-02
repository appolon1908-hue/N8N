#!/usr/bin/env python3
"""Validate exact n8n v2 family-client ownership across source contracts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELLS = ROOT / "config" / "automation-cells.v2.json"
POLICY = ROOT / "contracts" / "operation-policy.v2.json"
CATALOG = ROOT / "automations" / "catalog.v2.json"
PACKS = ROOT / "config" / "workflow-packs.v2.json"
PACK_DOCS = ROOT / "automations" / "packs"
PRODUCT_CATALOGS = (
    ROOT / "automations" / "beyvra.catalog.v2.json",
    ROOT / "automations" / "trading.catalog.v1.json",
)
APPROVED_CELL_EGRESS = {
    "n8n-core": {"middleware-core.internal.invalid"},
    "n8n-products": {"middleware-products.internal.invalid"},
    "n8n-contact-center": {"middleware-telephony.internal.invalid"},
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(
    cells: dict,
    policy: dict,
    catalog: dict,
    packs: dict,
    pack_docs: list[dict],
    product_catalogs: list[dict],
) -> None:
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
    command_families = policy.get("command_families")
    if not isinstance(command_families, list) or not command_families:
        raise ValueError("canonical command-family policy is missing")
    family_prefixes: dict[tuple[str, str], set[str]] = {}
    seen_prefixes: set[str] = set()
    for command_family in command_families:
        prefix = command_family.get("prefix")
        scope = command_family.get("scope")
        client_id = command_family.get("client")
        families = command_family.get("workflow_families")
        if (
            not isinstance(prefix, str)
            or not prefix
            or client_id not in clients
            or not isinstance(scope, str)
            or not scope
            or not isinstance(families, list)
            or not families
        ):
            raise ValueError("invalid command-family authority")
        if prefix in seen_prefixes:
            raise ValueError(f"duplicate command prefix {prefix}")
        seen_prefixes.add(prefix)
        if prefix not in clients[client_id].get("command_prefixes", []):
            raise ValueError(f"command prefix {prefix} is outside {client_id} authority")
        if scope not in clients[client_id].get("scopes", []):
            raise ValueError(f"command scope {scope} is outside {client_id} authority")
        for family in families:
            if family not in clients[client_id].get("workflow_families", []):
                raise ValueError(f"command family {family} is outside {client_id} authority")
            family_prefixes.setdefault((client_id, family), set()).add(prefix)
    owners: dict[str, str] = {}
    declared_families: set[str] = set()
    rows = cells.get("cells")
    if not isinstance(rows, list) or not rows:
        raise ValueError("automation cells are missing")
    cell_ids: set[str] = set()
    family_owners: dict[str, str] = {}
    for cell in rows:
        cell_id = cell.get("id")
        machine_clients = cell.get("machine_clients")
        families = cell.get("workflow_families")
        if not isinstance(cell_id, str) or not isinstance(machine_clients, list) or not machine_clients:
            raise ValueError("cell must own an explicit non-empty machine_clients list")
        if cell_id in cell_ids:
            raise ValueError(f"duplicate cell {cell_id}")
        cell_ids.add(cell_id)
        if set(cell.get("allowed_egress", [])) != APPROVED_CELL_EGRESS.get(cell_id):
            raise ValueError(f"cell {cell_id} egress differs from its middleware boundary")
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
            client_families = clients[client_id].get("workflow_families", [])
            for family in client_families:
                prior_owner = family_owners.get(family)
                if prior_owner is not None and prior_owner != client_id:
                    raise ValueError(
                        f"workflow family {family} is owned by both {prior_owner} and {client_id}"
                    )
                family_owners[family] = client_id
            expected_families.update(client_families)
        if set(families) != expected_families:
            raise ValueError(f"workflow family/client drift in {cell_id}")
        overlap = declared_families.intersection(families)
        if overlap:
            raise ValueError(f"workflow families shared across cells: {sorted(overlap)}")
        declared_families.update(families)
    if set(owners) != set(clients):
        raise ValueError("not every canonical client has exactly one cell owner")

    if catalog.get("default_activation") != "DISABLED":
        raise ValueError("main catalog activation default must remain DISABLED")
    profiles = catalog.get("authorization_profiles", {})
    for profile_name, profile in profiles.items():
        client_id = profile.get("machine_client")
        if client_id not in clients:
            raise ValueError(f"profile {profile_name} references unknown client")
        effective_scopes = set(catalog.get("common_runtime_scopes", [])) | set(
            profile.get("additional_scopes", [])
        )
        if effective_scopes != set(clients[client_id].get("scopes", [])):
            raise ValueError(f"profile {profile_name} effective scopes drift from client policy")
        profile_family = profile.get("workflow_family")
        if profile_family == "product.allowlisted":
            authorized_families = set(clients[client_id].get("workflow_families", []))
        else:
            authorized_families = {profile_family}
        expected_prefixes = set().union(
            *(family_prefixes.get((client_id, family), set()) for family in authorized_families)
        )
        if set(profile.get("command_prefixes", [])) != expected_prefixes:
            raise ValueError(f"profile {profile_name} command prefixes drift from workflow family")

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

    for pack in packs.get("packs", []):
        target = pack.get("cell")
        if target != "all" and target not in cell_ids:
            raise ValueError(f"workflow pack {pack.get('id')} references unknown cell {target}")
    for pack in pack_docs:
        targets = str(pack.get("cell", "")).split("+")
        if not targets or any(target not in cell_ids for target in targets):
            raise ValueError(f"pack document {pack.get('pack')} references unknown cell")
        if pack.get("active") is not False:
            raise ValueError(f"pack document {pack.get('pack')} is active")

    if len(product_catalogs) != len(PRODUCT_CATALOGS):
        raise ValueError("product-specific catalog coverage is incomplete")
    for product in product_catalogs:
        authority = product.get("authorization", product)
        client_id = authority.get("machine_client")
        family = authority.get("workflow_family")
        if client_id not in clients or family not in clients[client_id].get("workflow_families", []):
            raise ValueError("product catalog family/client authority drift")
        if set(authority.get("required_scopes", [])) != set(clients[client_id].get("scopes", [])):
            raise ValueError("product catalog scope authority drift")
        expected_product_prefixes = family_prefixes.get((client_id, family), set())
        if set(authority.get("allowed_command_prefixes", [])) != expected_product_prefixes:
            raise ValueError("product catalog command-prefix authority drift")
        if product.get("default_activation") != "DISABLED":
            raise ValueError("product catalog activation default drift")
        if product.get("financial_effects_allowed", False) is not False:
            raise ValueError("product catalog permits financial effects")
        for workflow in product.get("workflows", []):
            if workflow.get("active") is not False or workflow.get("state") != "DESIGN_ONLY":
                raise ValueError("product workflow is not inactive DESIGN_ONLY")
            if workflow.get("direct_service_access") is not False:
                raise ValueError("product workflow permits direct service access")


def main() -> int:
    validate(
        load(CELLS),
        load(POLICY),
        load(CATALOG),
        load(PACKS),
        [load(path) for path in sorted(PACK_DOCS.glob("*.json"))],
        [load(path) for path in PRODUCT_CATALOGS],
    )
    print("N8N_V2_FAMILY_CLIENT_AUTHORITY=PASS")
    print("N8N_V2_RUNTIME_APPLY_AUTHORIZED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
