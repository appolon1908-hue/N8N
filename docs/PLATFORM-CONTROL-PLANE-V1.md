# Codestra platform control plane

**Status:** source-only, prepared and disabled.

This repository owns orchestration only. The accepted integration path is:

```text
n8n
  -> Kong
  -> Middleware automation v2
  -> Temporal and the durable command ledger
  -> Odoo or another reviewed destination adapter
  -> destination read-back and reconciliation
  -> Middleware command state
  -> n8n
```

n8n does not own provider credentials, tenant authority, actor authority,
capability truth, approval truth, durable command state, direct database access,
or direct Odoo/provider writes.

The machine-readable authority is split across:

- `contracts/automation-control-api.v2.yaml`;
- `contracts/operation-policy.v2.json`;
- `contracts/command-envelope.schema.json`;
- `contracts/middleware-surface.v1.json`;
- `contracts/platform-control-plane.v1.json`.

## Canonical n8n command boundary

New workflows use exactly:

```text
POST https://api.codestra.co/v2/automation/commands
GET  https://api.codestra.co/v2/automation/commands/{command_id}
```

The `/v1/integrations/n8n/commands` and
`/v1/integrations/n8n/operations/{command_id}` routes are Middleware
compatibility aliases for old callers. They are deprecated and prohibited in
new n8n templates.

CRM workflows use:

```text
client_id = n8n-crm-automation
audience  = middleware-api
submit    = automation.command.crm
read      = automation.command.read
```

Every command request is bound to a claimed job and active execution lease. It
carries the job, execution, workflow, step, event, correlation, causation,
idempotency, command type, command version, occurrence time, and payload.
Tenant and requester assertions are revalidated against the verified token and
durable job; neither assertion grants authority by itself.

Requests carry:

- `Authorization`;
- `X-Tenant-ID`;
- `X-Request-ID`;
- `X-Correlation-ID`;
- `Idempotency-Key`.

Middleware independently verifies the Keycloak token, exact client and scope,
job family, active lease, tenant, requester, command prefix, capability,
idempotency identity, approval requirements, and durable command state. Kong is
the network/API gateway but is not the cross-system write authority.

## Canonical Odoo command

There is one canonical CRM mutation:

```text
command_type    = crm.lead.upsert
command_version = "1.0"
```

n8n submits that governed command to Middleware. Middleware derives the Odoo
target and `ODOO_WRITE` capability from policy, persists the durable intent,
executes it through Temporal, and calls Odoo's reviewed
`codestra_middleware_bridge`:

```text
POST /codestra/middleware/v1/commands/crm.lead.upsert
GET  /codestra/middleware/v1/commands/{command_id}/status
```

The Odoo payload requires a stable `source_record_id`, provenance, consent,
review/contact controls, and the lead subject. n8n never calls Odoo directly and
never receives the Odoo HMAC secret.

## Unknown outcomes

An HTTP timeout after a command request is not proof that the destination
rejected it. Every command template therefore has:

```text
automatic_retry_on_timeout = false
timeout_semantics = UNKNOWN_OUTCOME_REQUIRES_RECONCILIATION
```

The workflow reads the Middleware command state. Middleware reconciles the
recorded Odoo command status before permitting any retry. Repeating the
external effect merely because the caller did not receive a response is
prohibited.

## Promotion rule

All source templates remain `active=false`, their HTTP nodes remain disabled,
and `config/n8n-policy.json` remains `UNVERIFIED` until staging proves:

- the exact private endpoint binding;
- the exact n8n machine credential and scope binding;
- editor access restrictions;
- egress restrictions;
- claimed-job and lease behavior;
- duplicate and semantic-conflict behavior;
- timeout-after-commit reconciliation;
- zero direct provider or Odoo access.

No token, client secret, provider credential, database credential, or HMAC
secret belongs in workflow JSON or Git.

## Safety state

This source change does not activate workflows, provision credentials, enable
`ODOO_WRITE`, enable external delivery, deploy a runtime, or mutate production.
All effectful capabilities remain false until separately reviewed staging and
production gates pass.
