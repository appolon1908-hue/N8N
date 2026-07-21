import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOWS = {
    "WF-00_CODESTRA_EVENT_ROUTER": ("Webhook", "route event to reusable sub-workflow"),
    "WF-10_CALL_LIFECYCLE": ("Webhook", "process call lifecycle events"),
    "WF-20_CALLBACK_MANAGEMENT": ("Cron", "process due and overdue callbacks"),
    "WF-30_LEAD_INTELLIGENCE": ("Webhook", "score and enrich leads"),
    "WF-40_SALES_AND_HOT_LEADS": ("Webhook", "route sales and hot leads"),
    "WF-50_AGENT_AND_QUEUE_MONITORING": ("Cron", "monitor queue and agent KPIs"),
    "WF-60_QA_AND_COMPLIANCE": ("Webhook", "apply QA and consent controls"),
    "WF-70_REPORTING": ("Cron", "request and render reports"),
    "WF-90_ERROR_AND_DEAD_LETTER": ("Webhook", "classify, retry, or dead-letter failures"),
}
WORKFLOW_IDS = {
    name: f"Cdst{name.split('_', 1)[0].replace('-', '')}{index:02d}"
    for index, name in enumerate(WORKFLOWS)
}
MIDDLEWARE_CREDENTIAL = {
    "httpHeaderAuth": {
        "id": "codestraMiddlewareBearer",
        "name": "Codestra Middleware Bearer",
    }
}


def node(node_id: str, name: str, type_: str, x: int, y: int, parameters: dict) -> dict:
    item = {"id": node_id, "name": name, "type": type_, "typeVersion": 1, "position": [x, y], "parameters": parameters}
    if type_ == "n8n-nodes-base.httpRequest":
        item["parameters"] = {**parameters, "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"}
        item["credentials"] = MIDDLEWARE_CREDENTIAL
    return item


def make(name: str, trigger: str, purpose: str) -> dict:
    trigger_type = "n8n-nodes-base.webhook" if trigger == "Webhook" else "n8n-nodes-base.cron"
    trigger_params = {"path": name.lower(), "httpMethod": "POST", "responseMode": "responseNode"} if trigger == "Webhook" else {"triggerTimes": {"item": [{"mode": "everyX", "value": 5, "unit": "minutes"}]}}
    nodes = [
        node("trigger", f"{trigger} Trigger", trigger_type, 0, 0, trigger_params),
        node("signature", "Verify Signature", "n8n-nodes-base.code", 220, 0, {"jsCode": "const body=$json; if (!$headers['x-codestra-signature'] || !$headers['x-codestra-timestamp']) throw new Error('signature required'); return [{json: body}];"}),
        node("schema", "Validate Event Schema", "n8n-nodes-base.code", 440, 0, {"jsCode": "const e=$json; for (const key of ['event_id','event_type','event_version','environment','campaign_id','correlation_id']) if (!e[key]) throw new Error(`missing ${key}`); if (e.event_version !== '1.0') throw new Error('unsupported event version'); return [{json:e}];"}),
        node("policy", "Check Environment and Campaign Allowlist", "n8n-nodes-base.httpRequest", 660, 0, {"method": "POST", "url": "={{$env.MIDDLEWARE_INTERNAL_URL}}/api/v1/automation/policy-check", "sendBody": True, "jsonBody": "={{$json}}", "options": {"timeout": 10000}}),
        node("start", "Register Execution With Middleware", "n8n-nodes-base.httpRequest", 880, 0, {"method": "POST", "url": "={{$env.MIDDLEWARE_INTERNAL_URL}}/api/v1/automation/executions/start", "sendBody": True, "jsonBody": "={{$json}}", "options": {"timeout": 10000}}),
        node("context", "Fetch Full Context From Middleware", "n8n-nodes-base.httpRequest", 1100, 0, {"method": "GET", "url": "={{$env.MIDDLEWARE_INTERNAL_URL}}/api/v1/automation/context/leads/{{$json.lead_id}}", "options": {"timeout": 10000}}),
        node("switch", "Switch by Event Type", "n8n-nodes-base.switch", 1320, 0, {"mode": "rules", "rules": {"values": []}}),
        node("action", "Send Authorized Action to Middleware", "n8n-nodes-base.httpRequest", 1540, 0, {"method": "POST", "url": "={{$env.MIDDLEWARE_INTERNAL_URL}}/api/v1/automation/actions/notifications", "sendBody": True, "jsonBody": "={{$json}}", "options": {"timeout": 10000}}),
        node("complete", "Record Completion", "n8n-nodes-base.httpRequest", 1760, 0, {"method": "POST", "url": "={{$env.MIDDLEWARE_INTERNAL_URL}}/api/v1/automation/executions/complete", "sendBody": True, "jsonBody": "={{$json}}", "options": {"timeout": 10000}}),
        node("response", "Return 202", "n8n-nodes-base.respondToWebhook", 1980, 0, {"respondWith": "json", "responseBody": "={accepted:true,status:202}"}),
        node("error", "Classify Error and Redact", "n8n-nodes-base.code", 880, 240, {"jsCode": "const value={...$json}; for (const key of ['password','token','secret','phone','prompt']) if (key in value) value[key]='[REDACTED]'; return [{json:value}];"}),
        node("retry", "Retry Eligible?", "n8n-nodes-base.if", 1100, 240, {"conditions": {"boolean": [{"value1": "={{$json.retry_count < 4}}", "operation": "true"}]}}),
        node("dead", "Dead-Letter Through Middleware", "n8n-nodes-base.httpRequest", 1320, 360, {"method": "POST", "url": "={{$env.MIDDLEWARE_INTERNAL_URL}}/api/v1/automation/events/dead-letter", "sendBody": True, "jsonBody": "={{$json}}", "options": {"timeout": 10000}}),
    ]
    names = [item["name"] for item in nodes]
    connections = {names[index]: {"main": [[{"node": names[index + 1], "type": "main", "index": 0}]]} for index in range(len(names) - 1)}
    return {"id": WORKFLOW_IDS[name], "name": name, "active": False, "settings": {"executionOrder": "v1", "timezone": "America/Santo_Domingo"}, "nodes": nodes, "connections": connections, "meta": {"purpose": purpose, "mode": "integration", "middleware_only": True, "signature_verification": True, "event_version": "1.0", "campaign_allowlist": "TEST_SYN", "environment": "test", "error_workflow": "WF-90_ERROR_AND_DEAD_LETTER", "retry_delays_seconds": [30, 120, 600, 1800], "no_credentials": True, "credential_reference": "codestraMiddlewareBearer", "no_direct_system_access": True}}


(ROOT / "workflows").mkdir(exist_ok=True)
for workflow_name, (trigger, purpose) in WORKFLOWS.items():
    (ROOT / "workflows" / f"{workflow_name}.json").write_text(json.dumps(make(workflow_name, trigger, purpose), indent=2) + "\n")
print(f"generated {len(WORKFLOWS)} inactive workflows")
