# Decisions

## X0: Canonical Middleware Automation Submit Path

Date: 2026-08-30

Decision: n8n command submission uses one canonical path: `POST /v2/automation/commands`.

Historical command aliases are prohibited in workflow exports and new docs:

- `/internal/v1/automation/commands`
- `/v1/integrations/n8n/commands`

Distinct non-command operations remain valid where they represent different control-plane actions, including job claim, job status read, heartbeat, step record, complete, fail, command read, approval, DLQ replay, reconciliation and capability read.

Rationale: n8n is the orchestrator only. Middleware remains the durable command, job, policy, idempotency, DLQ and reconciliation authority. One submit path removes ambiguity while keeping explicit paths for distinct lifecycle operations.

Activation impact: none. `active=false`, external effects, Odoo writes and live writes remain disabled.
