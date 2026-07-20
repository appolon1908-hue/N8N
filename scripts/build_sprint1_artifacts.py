#!/usr/bin/env python3
"""Generate deterministic Sprint 1 workflow, schema, fixture and documentation artifacts."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MW = "http://middleware:8095"
ERROR_ID = "CdstErrorDeadLetterV1"


def node(identifier, name, kind, x, y, parameters=None, version=1):
    return {"id": identifier, "name": name, "type": kind, "typeVersion": version, "position": [x, y], "parameters": parameters or {}}


def code(identifier, name, script, x, y):
    return node(identifier, name, "n8n-nodes-base.code", x, y, {"jsCode": script}, 2)


def http(identifier, name, method, path, x, y, body="={{$json}}"):
    parameters = {"url": MW + path, "options": {"timeout": 10000}, "sendHeaders": True,
                  "headerParameters": {"parameters": [{"name": "X-Request-ID", "value": "={{$json.request_id}}"}, {"name": "X-Correlation-ID", "value": "={{$json.correlation_id}}"}]}}
    if method != "GET": parameters.update({"method": method, "sendBody": True, "specifyBody": "json", "jsonBody": body})
    return node(identifier, name, "n8n-nodes-base.httpRequest", x, y, parameters, 4.2)


def execute(identifier, name, workflow_id, x, y):
    return node(identifier, name, "n8n-nodes-base.executeWorkflow", x, y,
                {"workflowId": {"__rl": True, "value": workflow_id, "mode": "id"}, "options": {"waitForSubWorkflow": True}}, 1.2)


def connect(names):
    return {left: {"main": [[{"node": right, "type": "main", "index": 0}]]} for left, right in zip(names, names[1:])}


def workflow(identifier, name, folder, nodes, connections=None, meta=None):
    data = {"id": identifier, "name": name, "active": False, "nodes": nodes, "connections": connections or connect([n["name"] for n in nodes]),
            "settings": {"executionOrder": "v1", "errorWorkflow": ERROR_ID, "timezone": "America/Santo_Domingo", "saveExecutionProgress": True},
            "meta": {"sprint": 1, "environment": "test", "campaign_allowlist": ["TEST_SYN"], "middleware_only": True,
                     "request_id_required": True, "correlation_id_required": True, "retry_policy_seconds": [30, 120, 600, 1800], **(meta or {})},
            "tags": [{"name": "codestra-sprint-1"}, {"name": "inactive-blueprint"}]}
    target = ROOT / "workflows" / folder / f"{identifier}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + "\n")
    return data, target


VALIDATE = """const e=$json;const required=['event_id','event_type','event_version','occurred_at','received_at','tenant_id','environment','request_id','correlation_id','idempotency_key','source','campaign_id','references','data'];for(const k of required){if(e[k]===undefined||e[k]===null||e[k]==='')throw new Error('validation_error:'+k)};if(JSON.stringify(e).length>262144)throw new Error('validation_error:payload_too_large');return [{json:e}];"""


def build_workflows():
    made = []
    trigger = lambda: node("trigger", "Execute Workflow Trigger", "n8n-nodes-base.executeWorkflowTrigger", 0, 0)
    nodes = [trigger(), code("headers", "Normalize Headers", "return items.map(i=>({json:{...i.json,headers:Object.fromEntries(Object.entries(i.json.headers||{}).map(([k,v])=>[k.toLowerCase(),v]))}}));", 220, 0),
             code("required", "Validate Required Envelope Fields", VALIDATE, 440, 0), code("version", "Validate Event Version", "if($json.event_version!=='1.0')throw new Error('validation_error:unsupported_event_version');return items;", 660, 0),
             code("environment", "Validate Environment", "if($json.environment!=='test')throw new Error('authorization_error:environment');return items;", 880, 0),
             code("campaign", "Validate Campaign Allowlist", "if($json.campaign_id!=='TEST_SYN')throw new Error('authorization_error:campaign');return items;", 1100, 0),
             http("verify", "POST Middleware Verification", "POST", "/api/v1/automation/events/verify", 1320, 0),
             node("switch", "Switch Verification Result", "n8n-nodes-base.if", 1540, 0, {"conditions":{"boolean":[{"value1":"={{$json.verified}}","operation":"isTrue"}]}} ,2),
             code("return", "Return Validated Event", "return items;", 1760, -80), execute("failure", "Route Failure to CDA-WF-90", ERROR_ID, 1760, 120)]
    con = connect([n["name"] for n in nodes[:8]]); con["Switch Verification Result"]={"main":[[{"node":"Return Validated Event","type":"main","index":0}],[{"node":"Route Failure to CDA-WF-90","type":"main","index":0}]]}
    made.append(workflow("CdstVerifyEventV1", "CDA-SW-01 Verify Event", "shared", nodes, con, {"signature_verification": True}))

    for wid, title, path, payload in [
        ("CdstStartExecutionV1", "CDA-SW-02 Start Execution", "/api/v1/automation/executions/start", "={{$json}}"),
        ("CdstCompleteExecutionV1", "CDA-SW-04 Complete Execution", "/api/v1/automation/executions/complete", "={{$json}}"),
        ("CdstFailExecutionV1", "CDA-SW-05 Fail Execution", "/api/v1/automation/executions/fail", "={{$json}}")]:
        made.append(workflow(wid, title, "shared", [trigger(), code("sanitize", "Sanitize Execution Payload", "const deny=/password|secret|token|stack|authorization/i;const clean=Object.fromEntries(Object.entries($json).map(([k,v])=>[k,deny.test(k)?'[REDACTED]':v]));return [{json:clean}];", 240, 0), http("post", "POST Middleware Lifecycle", "POST", path, 480, 0, payload)]))

    made.append(workflow("CdstFetchContextV1", "CDA-SW-03 Fetch Context", "shared", [trigger(), code("route", "Validate Context Route", "const allowed=['calls','leads','timeline','agents','campaigns','callbacks/due','reports/daily-operations'];if(!allowed.includes($json.context_type))throw new Error('validation_error:context_type');const id=$json.identifier?'/'+encodeURIComponent($json.identifier):'';return [{json:{...$json,context_url:'"+MW+"/api/v1/automation/context/'+$json.context_type+id}}];", 240, 0), node("get", "GET Middleware Context", "n8n-nodes-base.httpRequest", 480, 0, {"url":"={{$json.context_url}}","options":{"timeout":10000},"sendHeaders":True,"headerParameters":{"parameters":[{"name":"X-Request-ID","value":"={{$json.request_id}}"},{"name":"X-Correlation-ID","value":"={{$json.correlation_id}}"}]}}, 4.2), code("structured", "Return Structured Context", "return [{json:{ok:true,context:$json}}];", 720, 0)]))

    router_nodes=[node("webhook","Webhook","n8n-nodes-base.webhook",0,0,{"httpMethod":"POST","path":"codestra/events/v1","responseMode":"responseNode"},2),execute("verify","CDA-SW-01 Verify Event","CdstVerifyEventV1",220,0),execute("start","CDA-SW-02 Start Execution","CdstStartExecutionV1",440,0),node("switch","Switch Event Type","n8n-nodes-base.switch",660,0,{"rules":{"values":[{"conditions":{"conditions":[{"leftValue":"={{$json.event_type}}","rightValue":t,"operator":{"type":"string","operation":"equals"}}]}} for t in ['call.completed','callback.due','lead.enrichment_requested','lead.hot','report.daily_requested']]},"options":{"fallbackOutput":"extra"}},3.2)]
    children=[("call","CDA-WF-10 Call Completed","CdstCallCompletedV1"),("callback","CDA-WF-20 Callback Due","CdstCallbackDueV1"),("enrichment","CDA-WF-30 Lead Enrichment","CdstLeadEnrichmentV1"),("hot","CDA-WF-40 Hot Lead Alert","CdstHotLeadAlertV1"),("report","CDA-WF-70 Daily Operations Digest","CdstDailyOperationsDigestV1")]
    router_nodes += [execute(i,n,w,900,y) for (i,n,w),y in zip(children,[-240,-120,0,120,240])]
    router_nodes += [execute("complete","CDA-SW-04 Complete Execution","CdstCompleteExecutionV1",1140,0),node("respond","Respond 202 Accepted","n8n-nodes-base.respondToWebhook",1360,0,{"respondWith":"json","responseBody":"={{ {accepted:true,event_id:$json.event_id} }}","options":{"responseCode":202}},1.4),execute("error","Error Branch to CDA-WF-90",ERROR_ID,1140,260)]
    con={"Webhook":{"main":[[{"node":"CDA-SW-01 Verify Event","type":"main","index":0}]]},"CDA-SW-01 Verify Event":{"main":[[{"node":"CDA-SW-02 Start Execution","type":"main","index":0}]]},"CDA-SW-02 Start Execution":{"main":[[{"node":"Switch Event Type","type":"main","index":0}]]},"Switch Event Type":{"main":[[{"node":n,"type":"main","index":0}] for _,n,_ in children]+[[{"node":"Error Branch to CDA-WF-90","type":"main","index":0}]]}}
    for _,n,_ in children: con[n]={"main":[[{"node":"CDA-SW-04 Complete Execution","type":"main","index":0}]]}
    con["CDA-SW-04 Complete Execution"]={"main":[[{"node":"Respond 202 Accepted","type":"main","index":0}]]}
    made.append(workflow("CdstAutomationRouterV1","CDA-WF-00 Codestra Event Router","events",router_nodes,con,{"supported_event_types":["call.completed","callback.due","lead.enrichment_requested","lead.hot","report.daily_requested"],"webhook_future_only":True,"signature_verification":True}))

    biz = [
      ("CdstCallCompletedV1","CDA-WF-10 Call Completed","events",[("call","Fetch Call Context","calls"),("lead","Fetch Lead Context","leads"),("timeline","Fetch Lead Timeline","timeline")],"Normalize Disposition and Calculate Call Metrics","/api/v1/automation/actions/call-completed"),
      ("CdstLeadEnrichmentV1","CDA-WF-30 Lead Enrichment","intelligence",[("lead","Fetch Lead Context","leads"),("call","Fetch Latest Call","calls"),("timeline","Fetch Timeline","timeline")],"Build Deterministic Test Enrichment","/api/v1/automation/actions/lead-enrichment"),
      ("CdstHotLeadAlertV1","CDA-WF-40 Hot Lead Alert","alerts",[("lead","Fetch Lead Context","leads"),("call","Fetch Latest Call","calls"),("campaign","Fetch Campaign","campaigns")],"Build Clean Management Alert Card","/api/v1/automation/actions/notifications/preview")]
    for wid,title,folder,fetches,transform,path in biz:
        ns=[trigger(),execute("verify","CDA-SW-01 Verify Event","CdstVerifyEventV1",200,0),execute("start","CDA-SW-02 Start Execution","CdstStartExecutionV1",400,0)]
        x=600
        for ident,name,context_type in fetches:
            ns.append(code(ident+"route",name+" Route","return [{json:{...$json,context_type:'"+context_type+"',identifier:$json.references?.uniqueid||$json.references?.vicidial_lead_id||$json.campaign_id}}];",x,0));x+=180
            ns.append(execute(ident,name,"CdstFetchContextV1",x,0));x+=180
        if wid=="CdstLeadEnrichmentV1": script="return [{json:{...$json,result:{summary:'Customer requested a callback.',intent:'interested_callback',sentiment_score:0.74,lead_score:82,next_best_action:'Schedule callback with closer',risk_flags:[],reason_codes:['requested_callback','verified_contact']}}}];"
        elif wid=="CdstHotLeadAlertV1": script="if(($json.data?.lead_score||0)<80)throw new Error('permanent_business_rejection:score');return [{json:{...$json,preview:{lead_reference:$json.references?.vicidial_lead_id,campaign:$json.campaign_id,assigned_agent:$json.references?.agent_id,score:$json.data.lead_score,latest_disposition:$json.data.latest_disposition,estimated_value:$json.data.estimated_value,recommended_action:$json.data.recommended_action,crm_reference:'test-placeholder'}}}];"
        else: script="const d=$json.data||{};return [{json:{...$json,result:{wait_seconds:Number(d.wait_seconds||0),talk_seconds:Number(d.talk_seconds||0),total_seconds:Number(d.total_seconds||0),call_attempt_number:Number(d.call_attempt_number||1),callback_required:Boolean(d.callback_required),enrichment_eligible:Boolean(d.enrichment_eligible),hot_lead_eligible:Boolean(d.hot_lead_eligible)}}}];"
        ns += [code("transform",transform,script,x,0),http("action","POST Mock/Test Middleware Action","POST",path,x+220,0),execute("complete","CDA-SW-04 Complete Execution","CdstCompleteExecutionV1",x+440,0)]
        made.append(workflow(wid,title,folder,ns,meta={"test_action_only":True,"signature_verification":True}))

    callback_nodes=[node("manual","Manual Trigger","n8n-nodes-base.manualTrigger",0,-80),node("schedule","Inactive Schedule Trigger","n8n-nodes-base.scheduleTrigger",0,80,{"rule":{"interval":[{"field":"minutes","minutesInterval":5}]}},1.2),http("due","GET Due Callbacks","GET","/api/v1/automation/callbacks/due",240,0),code("filter","Filter TEST_SYN Scheduled Callbacks","const now=Date.now();return ($json.items||[]).filter(c=>c.status==='scheduled'&&c.campaign_id==='TEST_SYN'&&!c.dispatched_at&&c.assigned_agent_id).map(c=>({json:{...c,category:new Date(c.scheduled_at).getTime()<now?'overdue':c.priority==='high'?'high_priority':'due',supervisor_escalation:new Date(c.scheduled_at).getTime()<now}}));",480,0),code("preview","Build Notification Preview","return items.map(i=>({json:{request_id:i.json.request_id||'req_callback_test',correlation_id:i.json.callback_id, campaign_id:'TEST_SYN',preview:i.json}}));",720,0),http("post","POST Notification Preview","POST","/api/v1/automation/actions/notifications/preview",960,0)]
    callback_con={"Manual Trigger":{"main":[[{"node":"GET Due Callbacks","type":"main","index":0}]]},"Inactive Schedule Trigger":{"main":[[{"node":"GET Due Callbacks","type":"main","index":0}]]},**connect([n["name"] for n in callback_nodes[2:]])}
    made.append(workflow("CdstCallbackDueV1","CDA-WF-20 Callback Due","callbacks",callback_nodes,callback_con,{"preview_only":True,"signature_verification":True}))

    report_nodes=[node("manual","Manual Trigger","n8n-nodes-base.manualTrigger",0,-80),node("schedule","Inactive Schedule Trigger","n8n-nodes-base.scheduleTrigger",0,80,{"rule":{"interval":[{"triggerAtHour":7}]}} ,1.2),http("fetch","GET Daily Operations Report","GET","/api/v1/reports/daily-operations",240,0),code("validate","Validate Report Response","if(!$json.report_date||!$json.kpis)throw new Error('validation_error:daily_report');return items;",480,0),code("render","Render JSON HTML CSV and Text","const k=$json.kpis;const rows=Object.entries(k).map(([a,b])=>a+','+b);return [{json:{normalized:$json,html:'<!doctype html><html><body><h1>Codestra Daily Operations</h1><p>'+JSON.stringify(k)+'</p></body></html>',csv:['metric,value',...rows].join('\\n'),text:'Codestra Daily Operations '+JSON.stringify(k)}}];",720,0)]
    report_con={"Manual Trigger":{"main":[[{"node":"GET Daily Operations Report","type":"main","index":0}]]},"Inactive Schedule Trigger":{"main":[[{"node":"GET Daily Operations Report","type":"main","index":0}]]},**connect([n["name"] for n in report_nodes[2:]])}
    made.append(workflow("CdstDailyOperationsDigestV1","CDA-WF-70 Daily Operations Digest","reporting",report_nodes,report_con,{"render_only":True,"signature_verification":True}))

    error_nodes=[node("error","Error Trigger","n8n-nodes-base.errorTrigger",0,-80),trigger(),code("classify","Classify Error and Redact Sensitive Values","const msg=String($json.error?.message||$json.message||'unknown_error').replace(/(password|secret|token|authorization)=[^ ]+/ig,'$1=[REDACTED]');const never=/signature|timestamp|version|campaign|environment|idempotency|permanent_business/i.test(msg);return [{json:{...$json,error_classification:msg.split(':')[0]||'unknown_error',sanitized_error_message:msg,retry_eligible:!never,retry_policy_seconds:[30,120,600,1800]}}];",240,0),node("retry","Retry Eligible?","n8n-nodes-base.if",480,0,{"conditions":{"boolean":[{"value1":"={{$json.retry_eligible}}","operation":"isTrue"}]}},2),execute("fail","CDA-SW-05 Fail Execution","CdstFailExecutionV1",720,-100),http("dead","POST Final Dead Letter","POST","/api/v1/automation/events/dead-letter",720,100)]
    error_con={"Error Trigger":{"main":[[{"node":"Classify Error and Redact Sensitive Values","type":"main","index":0}]]},"Execute Workflow Trigger":{"main":[[{"node":"Classify Error and Redact Sensitive Values","type":"main","index":0}]]},"Classify Error and Redact Sensitive Values":{"main":[[{"node":"Retry Eligible?","type":"main","index":0}]]},"Retry Eligible?":{"main":[[{"node":"CDA-SW-05 Fail Execution","type":"main","index":0}],[{"node":"POST Final Dead Letter","type":"main","index":0}]]}}
    made.append(workflow(ERROR_ID,"CDA-WF-90 Error and Dead Letter","errors",error_nodes,error_con,{"never_retry":["invalid_signature","stale_timestamp","unsupported_event_version","disallowed_campaign","invalid_environment","conflicting_idempotency_payload","permanent_business_rejection"],"signature_verification":True}))
    return made


def schema(title, required, properties):
    return {"$schema":"https://json-schema.org/draft/2020-12/schema","$id":f"https://codestra.agency/schemas/{title}","title":title,"type":"object","required":required,"properties":properties,"additionalProperties":False}


def build_support(workflows):
    for directory in ["contracts","fixtures","templates","tests/mock-middleware","tests/assertions","docs","reports","manifests","schemas","workflows/intelligence","workflows/alerts"]: (ROOT/directory).mkdir(parents=True,exist_ok=True)
    env_props={k:{"type":"string","minLength":1} for k in ["event_id","event_type","event_version","occurred_at","received_at","tenant_id","environment","request_id","correlation_id","idempotency_key","source","campaign_id"]}
    env_props.update({"event_type":{"enum":["call.completed","callback.due","lead.enrichment_requested","lead.hot","report.daily_requested"]},"event_version":{"const":"1.0"},"environment":{"const":"test"},"campaign_id":{"const":"TEST_SYN"},"occurred_at":{"type":"string","format":"date-time"},"received_at":{"type":"string","format":"date-time"},"references":{"type":"object"},"data":{"type":"object"}})
    envelope=schema("event-envelope-v1",list(env_props),env_props); (ROOT/"schemas/event-envelope-v1.json").write_text(json.dumps(envelope,indent=2)+"\n")
    specs={"call-completed-v1":["uniqueid","lead_id","disposition","talk_seconds"],"callback-due-v1":["callback_id","scheduled_at","assigned_agent_id"],"lead-enrichment-v1":["lead_id"],"hot-lead-v1":["lead_id","lead_score"],"daily-report-v1":["report_date","timezone","kpis"],"execution-result-v1":["event_id","workflow_id","result_status"],"dead-letter-v1":["event_id","error_classification","retry_eligible"]}
    for name,req in specs.items():
        props={key:({"type":"number"} if key.endswith("seconds") or key=="lead_score" else {"type":["string","object","boolean"]}) for key in req}
        (ROOT/f"schemas/{name}.json").write_text(json.dumps(schema(name,req,props),indent=2)+"\n")
    manifest={"version":"1.0","sprint":1,"expected_workflow_count":len(workflows),"workflows":[{"id":w[0]["id"],"name":w[0]["name"],"path":str(w[1].relative_to(ROOT)),"node_count":len(w[0]["nodes"]),"active":False} for w in workflows]}
    (ROOT/"manifests/workflow-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    fixture={"event_id":"evt_call_completed_001","event_type":"call.completed","event_version":"1.0","occurred_at":"2026-07-20T18:15:00Z","received_at":"2026-07-20T18:15:02Z","tenant_id":"codestra","environment":"test","request_id":"req_001","correlation_id":"call_1783449096.000000037","idempotency_key":"call.completed:1783449096.000000037","source":"vicidial","campaign_id":"TEST_SYN","references":{"uniqueid":"1783449096.000000037","vicidial_lead_id":"37","odoo_lead_id":45,"agent_id":"1001"},"data":{"disposition":"CALLBK","talk_seconds":90,"wait_seconds":12,"total_seconds":102,"lead_score":82,"latest_disposition":"CALLBK","estimated_value":2500,"recommended_action":"Schedule callback with closer"}}
    for name,changes in {"completed-call":{},"duplicate-event":{},"conflicting-duplicate":{"data":{"talk_seconds":999}},"invalid-signature":{"test_signature":"invalid"},"stale-timestamp":{"test_timestamp":"1"},"hot-lead":{"event_id":"evt_hot_001","event_type":"lead.hot"}}.items():
        value={**fixture,**changes}; (ROOT/f"fixtures/{name}.json").write_text(json.dumps(value,indent=2)+"\n")
    callbacks=[{"callback_id":"cb_due","status":"scheduled","campaign_id":"TEST_SYN","scheduled_at":"2026-07-20T18:10:00Z","assigned_agent_id":"1001","priority":"normal"},{"callback_id":"cb_overdue","status":"scheduled","campaign_id":"TEST_SYN","scheduled_at":"2026-07-20T17:00:00Z","assigned_agent_id":"1002","priority":"high"}]
    (ROOT/"fixtures/callbacks.json").write_text(json.dumps(callbacks,indent=2)+"\n")
    daily={"report_date":"2026-07-20","timezone":"America/Santo_Domingo","kpis":{"total_calls":100,"answer_rate":0.72,"human_contacts":55,"sales":12,"conversion_rate":0.2182,"average_talk_time":184,"callbacks_due":8,"callback_sla":0.875},"campaigns":[],"agents":[],"automation_health":{"events_received":100,"events_processed":100,"successful":99,"failed":1,"retries":1,"dead_letter_count":0,"average_processing_time_ms":213}}
    (ROOT/"fixtures/daily-report.json").write_text(json.dumps(daily,indent=2)+"\n")


if __name__ == "__main__":
    workflows=build_workflows();build_support(workflows);print(f"generated {len(workflows)} inactive Sprint 1 workflows")
