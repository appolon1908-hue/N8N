# Codestra n8n identity and webhook contract

This repository currently contains governance and contract scaffolding only. It
does not yet contain reviewed n8n workflow exports, credentials, or runtime
evidence.

## Machine identity

```text
issuer=https://auth.codestra.co/realms/codestra
client_id=n8n-automation
grant_type=client_credentials
maximum_access_token_lifetime_seconds=300
```

Middleware calls the n8n automation boundary with audience `n8n-automation` and
only `workflow.trigger` or `workflow.status.read`. n8n returns results to
`middleware-api` with only `workflow.result.publish`.

n8n receives no direct grant to Odoo, VICIdial, Telnexa, Klyrow, Kyqra, or
Postly. Every effectful provider action must pass through the middleware command
boundary.

## Result webhook

```text
POST ${MIDDLEWARE_API_BASE_URL}/api/v1/n8n/results
```

The callback requires a short-lived bearer token for audience `middleware-api`,
HMAC-SHA256, tenant/event/source/timestamp/signature/correlation headers, a
stable event ID, replay protection for at least 24 hours, and idempotent
at-least-once processing.

Canonical event types:

```text
codestra.n8n.workflow.completed
codestra.n8n.workflow.failed
```

## Workflow import gate

A later implementation PR must add sanitized workflow exports under
`workflows/`, with credentials referenced only by n8n credential IDs or
protected runtime configuration. The implementation PR must include positive and
negative token tests, duplicate-delivery tests, replay tests, tenant-isolation
tests, disabled external delivery, and staging execution evidence.
