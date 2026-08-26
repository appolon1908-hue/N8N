#!/usr/bin/env python3
"""Fail-closed validation for the Codestra n8n identity and webhook contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "codestra-integration.json"
ISSUER = "https://auth.codestra.co/realms/codestra"
EXPECTED_PROHIBITED = [
    "odoo-integration",
    "vicidial-adapter",
    "telnexa-gateway",
    "klyrow-gateway",
    "kyqra-gateway",
    "postly-adapter",
]
REQUIRED_HEADERS = {
    "Authorization",
    "Content-Type",
    "Idempotency-Key",
    "X-Codestra-Event-Id",
    "X-Codestra-Event-Type",
    "X-Codestra-Source",
    "X-Codestra-Tenant-Id",
    "X-Codestra-Timestamp",
    "X-Codestra-Signature",
    "X-Correlation-Id",
}
SCOPE = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")
EVENT = re.compile(r"^codestra\.n8n\.workflow\.(?:completed|failed)$")


class ContractError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ContractError(message)


def sorted_unique(values: object, label: str) -> list[str]:
    if not isinstance(values, list) or not values or not all(isinstance(item, str) for item in values):
        fail(f"{label} must be a non-empty string array")
    if values != sorted(values) or len(values) != len(set(values)):
        fail(f"{label} must be sorted and unique")
    return values


def validate() -> None:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"unable to load contract: {exc}")
    if not isinstance(contract, dict) or contract.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if contract.get("sourceState") != "workflow-source-missing":
        fail("sourceState must remain honest until workflow exports are committed")
    if contract.get("issuer") != ISSUER:
        fail("canonical Codestra issuer is required")
    expected_values = {
        "clientId": "n8n-automation",
        "clientType": "confidential",
        "grantType": "client_credentials",
        "serviceAccountsEnabled": True,
        "standardFlowEnabled": False,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "fullScopeAllowed": False,
    }
    for key, expected in expected_values.items():
        if contract.get(key) != expected:
            fail(f"{key} must equal {expected!r}")
    lifetime = contract.get("maximumAccessTokenLifetimeSeconds")
    if not isinstance(lifetime, int) or not 1 <= lifetime <= 300:
        fail("machine-token lifetime must be 1..300 seconds")

    inbound = contract.get("inboundApi")
    if not isinstance(inbound, dict):
        fail("inboundApi must be an object")
    if inbound.get("baseUrlEnvironment") != "N8N_AUTOMATION_BASE_URL":
        fail("n8n API location must use N8N_AUTOMATION_BASE_URL")
    if inbound.get("audience") != "n8n-automation":
        fail("inbound n8n audience must be n8n-automation")
    expected_callers = [
        {
            "clientId": "middleware-api",
            "scopes": ["workflow.status.read", "workflow.trigger"],
        },
        {
            "clientId": "monitoring-readonly",
            "scopes": ["health.read", "metrics.read"],
        },
    ]
    if inbound.get("allowedCallers") != expected_callers:
        fail("allowed n8n callers or scopes changed")

    outbound = contract.get("outboundMiddleware")
    if not isinstance(outbound, dict):
        fail("outboundMiddleware must be an object")
    if outbound.get("baseUrlEnvironment") != "MIDDLEWARE_API_BASE_URL":
        fail("middleware location must use MIDDLEWARE_API_BASE_URL")
    if outbound.get("audience") != "middleware-api":
        fail("n8n result tokens must target middleware-api")
    scopes = sorted_unique(outbound.get("scopes"), "outbound middleware scopes")
    if scopes != ["workflow.result.publish"]:
        fail("n8n may publish results only")
    if outbound.get("resultPath") != "/api/v1/n8n/results":
        fail("canonical n8n result path changed")
    if not all(SCOPE.fullmatch(scope) for scope in scopes):
        fail("invalid outbound scope")

    if contract.get("prohibitedDirectTargets") != EXPECTED_PROHIBITED:
        fail("direct provider prohibition changed")

    security = contract.get("webhookSecurity")
    if not isinstance(security, dict):
        fail("webhookSecurity must be an object")
    expected_security = {
        "authorization": "oidc_bearer",
        "signatureAlgorithm": "hmac-sha256",
        "signatureVersion": "v1",
        "maximumClockSkewSeconds": 300,
        "replayRetentionSeconds": 86400,
        "delivery": "at_least_once",
        "idempotencyHeader": "X-Codestra-Event-Id",
    }
    for key, expected in expected_security.items():
        if security.get(key) != expected:
            fail(f"webhookSecurity.{key} must equal {expected!r}")
    if set(security.get("requiredHeaders", [])) != REQUIRED_HEADERS:
        fail("webhook required headers changed")

    event_types = sorted_unique(contract.get("resultEventTypes"), "resultEventTypes")
    if not all(EVENT.fullmatch(event_type) for event_type in event_types):
        fail("non-canonical result event type")
    if contract.get("secretStorage") != "n8n-credential-store-and-protected-runtime-only":
        fail("n8n credentials must remain outside Git")

    workflow_files = list((ROOT / "workflows").glob("*.json")) if (ROOT / "workflows").is_dir() else []
    if workflow_files:
        fail("workflow exports require a separate reviewed implementation PR")

    print("N8N_IDENTITY_POLICY=PASS")
    print("N8N_API_AUDIENCE_POLICY=PASS")
    print("N8N_WEBHOOK_POLICY=PASS")
    print("WORKFLOW_SOURCE_STATE=NOT_YET_IMPORTED")


if __name__ == "__main__":
    try:
        validate()
    except ContractError as exc:
        print(f"N8N_CONTRACT_ERROR={exc}", file=sys.stderr)
        raise SystemExit(1)
