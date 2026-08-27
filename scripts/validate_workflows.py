#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = sorted((ROOT / "workflows").glob("*.json"))
assert files, "at least one workflow contract is required"
for path in files:
    workflow = json.loads(path.read_text())
    assert workflow["schema"] == "codestra.n8n.workflow-contract.v1"
    assert workflow["active"] is False, f"{path.name} must remain inactive"
    serialized = json.dumps(workflow).lower()
    for forbidden in (
        "postal admin",
        "keycloak admin credential",
        "direct-odoo",
        "direct-klyrow",
    ):
        assert forbidden not in serialized
    for step in workflow.get("steps", []):
        if step.get("type") == "middleware-command":
            assert step.get("target") == "middleware-api"
print(f"N8N_WORKFLOW_CONTRACTS=PASS count={len(files)}")
