# Blockers

## R6: Klyrow Command Envelope Convention Conflict

Status: `BLOCKED_OWNER_DECISION_REQUIRED`

The n8n Middleware surface is now normalized around `POST /v2/automation/commands`, with Middleware deriving tenant, actor and workflow family from the durable automation job. That convention conflicts with the current Klyrow email/SMTP integration manifest.

Observed conflict:

- N8N command envelopes carry `tenant_id`, `correlation_id` and `idempotency_key` in the JSON body.
- Klyrow expects routing metadata as headers: `X-Tenant-ID`, `X-Correlation-ID` and `Idempotency-Key`.
- Klyrow does not send `X-Tenant-ID` or `X-Correlation-ID` today.
- N8N separates command name and version as `command_type` plus integer `command_version`.
- Klyrow currently names commands with a version suffix, for example `email.message.send.v1`.

Recommended convention:

- Keep authoritative tenant, actor and workflow family in Middleware job state and command body metadata.
- Mirror `X-Correlation-ID` and `Idempotency-Key` headers for routing, tracing and gateway dedupe.
- Do not trust `X-Tenant-ID` from n8n as authority; if a gateway needs it for routing, it must be mirrored from Middleware-issued job context.
- Use `command_type` without the version suffix, for example `email.message.send`, and keep the version in `command_version`.

Decision needed:

Klyrow and Middleware owners must agree on the envelope/header convention before executable CP-KLYROW workflows are built or activated. This repository must not unilaterally change the cross-repo contract beyond documenting the blocker.
