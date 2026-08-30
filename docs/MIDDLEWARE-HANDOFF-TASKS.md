# Middleware Handoff Tasks

These tasks are prepared from the N8N X0 gate. They are not runtime changes.

## M1: Adopt the Reconciled Command Envelope

Repository: `appolon1908-hue/Middleware-`

Implement the command envelope convention used by `appolon1908-hue/N8N` branch `phase-x0/envelope-reconciliation`:

- `POST /v2/automation/commands` is the only command submission endpoint for n8n.
- Required headers: `Authorization`, `X-Tenant-ID`, `X-Request-ID`, `X-Correlation-ID`, `Idempotency-Key`.
- Required body metadata: `tenant_id`, `correlation_id`, `idempotency_key`, `type`, `version`, `occurred_at`, `actor`, `payload`.
- `X-Tenant-ID` must mirror body `tenant_id`; Middleware must still derive and authorize tenant context server-side.
- `X-Correlation-ID` must mirror body `correlation_id`.
- `Idempotency-Key` must mirror body `idempotency_key`.
- `type` should be unversioned, for example `email.message.send`.
- `version` should be an integer, for example `1`.
- Reject trailing type suffixes such as `.v1` after Klyrow owner approval lands.

Acceptance evidence:

- Exact replay returns the original command receipt.
- Conflicting replay is rejected differently from auth failure.
- Timeout recovery uses command read/reconciliation, not duplicate provider submission.
- No direct Odoo, SMTP, SMS, social, crawler, database, Redis or provider call is made by n8n.

## M2: Decide Temporal Ownership

Repository: `appolon1908-hue/Middleware-`

N8N currently records a control-plane flow containing `middleware -> temporal -> odoo`, but no Temporal contract exists in the N8N repository.

Decision required:

- If Temporal is part of the Middleware runtime, add a Middleware-owned contract covering namespace, task queues, retry policy, idempotency mapping, timeout behavior, observability and rollback.
- If Temporal is not part of staging/prod runtime, approve removing Temporal from the N8N platform control-plane flow before X4 binding verification.

Non-negotiable boundary:

n8n must not call Temporal directly or hold Temporal credentials.
