#!/usr/bin/env python3
"""Validate the N8N side of the four-repository platform control plane."""

from __future__ import annotations

import json
from pathlib import Path

from policy_n8n import validate_n8n_policy

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "platform-control-plane.v1.json"
POLICY = ROOT / "config" / "n8n-policy.json"
TEMPLATE = ROOT / "workflows" / "_templates" / "disabled-odoo-lead-via-middleware.json"
SENTINEL_BASE = "https://middleware.invalid"


def fail(message: str) -> None:
    raise SystemExit(f"PLATFORM_CONTROL_PLANE=FAIL {message}")


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    workflow = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    repositories = contract.get("repositories", {})
    expected = {
        "orchestration": "appolon1908-hue/N8N",
        "write_authority": "appolon1908-hue/Middleware-",
        "business_authority": "appolon1908-hue/Odoo",
        "gateway_authority": "appolon1908-hue/Kong",
    }
    if repositories != expected:
        fail("repository authority map drifted")

    edge = contract.get("n8n_to_middleware", {})
    if edge.get("gateway_host") != "api.codestra.co":
        fail("canonical gateway host drifted")
    if edge.get("submit_path") != "/v1/integrations/n8n/commands":
        fail("command submit path drifted")
    if edge.get("read_path") != "/v1/integrations/n8n/operations/{command_id}":
        fail("command status path drifted")
    if edge.get("client_id") != "n8n-automation":
        fail("n8n service identity drifted")
    if edge.get("audience") != "middleware-api":
        fail("middleware audience drifted")
    if edge.get("submit_scope") != "middleware.request.forward":
        fail("command submit scope drifted")
    if edge.get("read_scope") != "middleware.status.read":
        fail("command status scope drifted")
    if edge.get("direct_provider_access") is not False:
        fail("direct provider access must remain prohibited")
    required_headers = {
        "Authorization",
        "X-Tenant-ID",
        "X-Request-ID",
        "X-Correlation-ID",
        "Idempotency-Key",
    }
    if set(edge.get("required_headers", [])) != required_headers:
        fail("canonical command headers drifted")

    policy_errors, _ = validate_n8n_policy(policy)
    if policy_errors:
        fail("n8n policy is invalid: " + "; ".join(policy_errors))
    endpoint = policy.get("endpoint_binding", {})
    credentials = policy.get("credential_binding", {})
    if endpoint.get("template_base_url") != SENTINEL_BASE:
        fail("template base must remain the non-routable middleware.invalid sentinel")
    if policy.get("status") == "UNVERIFIED":
        if endpoint.get("status") != "UNVERIFIED":
            fail("endpoint binding requires staging evidence before verification")
        if credentials.get("status") != "UNVERIFIED":
            fail("credential binding requires staging evidence before verification")

    if workflow.get("active") is not False:
        fail("Odoo workflow template must remain inactive")
    meta = workflow.get("meta", {}).get("codestra", {})
    if meta.get("network_policy") != "MIDDLEWARE_ONLY":
        fail("workflow must declare MIDDLEWARE_ONLY network policy")
    if meta.get("activation_state") != "DISABLED":
        fail("workflow activation state must remain DISABLED")
    if meta.get("credential_binding") != "NO_CREDENTIALS":
        fail("template must not bind credentials")

    http_nodes = [
        node for node in workflow.get("nodes", [])
        if str(node.get("type", "")).lower() == "n8n-nodes-base.httprequest"
    ]
    if len(http_nodes) != 1:
        fail("Odoo template must contain exactly one reviewed HTTP boundary")
    node = http_nodes[0]
    if node.get("disabled") is not True:
        fail("template HTTP node must remain disabled")
    expected_template_url = SENTINEL_BASE + edge["submit_path"]
    if node.get("parameters", {}).get("url") != expected_template_url:
        fail("unverified template must preserve the reviewed command path on the non-routable sentinel")
    headers = {
        item.get("name"): item.get("value")
        for item in node.get("parameters", {}).get("headerParameters", {}).get("parameters", [])
    }
    if set(headers) != required_headers:
        fail("template must carry canonical authentication, request, tenant and idempotency headers")
    if headers["Authorization"] != "={{$json.authorization}}":
        fail("template Authorization must remain an unbound runtime expression")

    serialized = json.dumps(workflow).lower()
    forbidden = (
        "http://odoo",
        "https://odoo",
        "jasmin",
        "postal",
        "vicidial",
        "smtp://",
        "postgres://",
        "redis://",
        "api.codestra.co",
    )
    found = [value for value in forbidden if value in serialized]
    if found:
        fail("unverified template contains routable/direct runtime targets: " + ", ".join(found))

    print("PLATFORM_CONTROL_PLANE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
