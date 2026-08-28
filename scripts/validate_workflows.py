#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = sorted((ROOT / "workflows").glob("*.json"))
assert files, "at least one workflow contract is required"

allowed_schemas = {
    "codestra.n8n.workflow-contract.v1",
    "codestra.n8n.workflow-contract.v2",
}
allowed_step_types = {"validation", "middleware-command", "conditional"}
for path in files:
    workflow = json.loads(path.read_text())
    assert workflow["schema"] in allowed_schemas
    assert workflow["active"] is False, f"{path.name} must remain inactive"

    safety = workflow.get("safety", {})
    for flag in (
        "directOdooAccess",
        "directKlyrowAccess",
        "directPostalAccess",
        "keycloakAdminAccess",
        "directProviderAccess",
        "sendsSecurityEmail",
        "changesKeycloakVerificationState",
        "securityEmailSynchronousPath",
        "duplicateBaseCrmProjection",
    ):
        if flag in safety:
            assert safety[flag] is False, f"{path.name} safety.{flag} must be false"
    assert safety.get("productionActivation") == "requires-separate-reviewed-deployment"

    if workflow["schema"].endswith(".v2"):
        ownership = workflow.get("ownership", {})
        assert ownership.get("workflowOwner") == "n8n"
        assert ownership.get("baseCrmProjectionOwner") == "middleware"
        assert ownership.get("baseCrmProjectionCommand") == "crm.contact.upsert.v1"
        assert ownership.get("mayRequestBaseCrmProjection") is False

    for step in workflow.get("steps", []):
        step_type = step.get("type")
        assert step_type in allowed_step_types, f"{path.name} has unsupported step type {step_type!r}"
        if step_type == "middleware-command":
            assert step.get("target") == "middleware-api"
            assert step.get("requiredScope") == "workflow.result.publish"
            assert step.get("command") != "crm.contact.sync.requested.v1", (
                f"{path.name} must not duplicate Middleware-owned base CRM projection"
            )
        else:
            assert "target" not in step, f"{path.name} non-command steps may not target external systems"

    serialized = json.dumps(workflow).lower()
    for forbidden in (
        "password",
        "verification_code",
        "reset_token",
        "reset_url",
        "postal admin",
        "keycloak admin credential",
    ):
        if forbidden in serialized:
            prohibited_fields = json.dumps(workflow.get("input", {}).get("prohibitedFields", [])).lower()
            step_prohibitions = json.dumps(
                [step.get("prohibitedFields", []) for step in workflow.get("steps", [])]
            ).lower()
            assert forbidden in prohibited_fields or forbidden in step_prohibitions

print(f"N8N_WORKFLOW_CONTRACTS=PASS count={len(files)}")
