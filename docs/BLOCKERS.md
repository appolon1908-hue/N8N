# Blockers

## R6: Klyrow Command Type Version Convention

Status: `BLOCKED_OWNER_DECISION_REQUIRED`

The n8n envelope is reconciled to carry routing and trace metadata in both headers and body: headers for gateway routing/rate limiting, body for schema validation and durable replay. That now matches the Klyrow header expectation for `X-Tenant-ID`, `X-Correlation-ID` and `Idempotency-Key`.

The remaining cross-repo disagreement is command type versioning:

- N8N canonical recommendation: `type` without version suffix, for example `email.message.send`, with `version` as the separate integer.
- Klyrow currently uses a version suffix in the type name, for example `email.message.send.v1`.

Recommendation: keep `type` stable and unversioned, and use the existing integer `version` field for schema evolution. Klyrow and Middleware owners must decide this convention before executable CP-KLYROW workflows are built or activated.

Owner answer prepared for Middleware and Klyrow:

- Middleware should accept `type` without a trailing version suffix and require integer `version`.
- Middleware should reject `type` values ending in `.v[0-9]+` with a contract validation error after the cross-repo decision lands.
- Klyrow should emit `email.message.send` with `version: 1`, not `email.message.send.v1`.
- During migration only, Middleware may log but not execute legacy suffix commands until the Klyrow branch is updated. No live send path should be enabled during that compatibility window.
- Headers remain required: `Authorization`, `X-Tenant-ID`, `X-Request-ID`, `X-Correlation-ID` and `Idempotency-Key`.
- Body metadata remains required for durability: `tenant_id`, `correlation_id`, `idempotency_key`, `type`, `version`, `occurred_at`, `actor` and `payload`.

## R6: Temporal Control-Plane Component

Status: `BLOCKED_OWNER_DECISION_REQUIRED`

`contracts/platform-control-plane.v1.json` currently declares the flow `middleware -> temporal -> odoo`, but this repository has no Temporal service contract, runtime config, credential policy, deployment reference or roadmap ownership record.

Decision needed: confirm whether Temporal is a real Middleware-owned runtime component that needs a contract in the Middleware mission, or update the cross-repo control-plane flow to remove it. This repository must not silently delete or invent the Temporal contract.

Owner answer prepared for Middleware:

- If Temporal is real, Middleware owns the worker/runtime contract and n8n sees only Middleware API state.
- If Temporal is not real in staging, update the control-plane flow to `middleware -> odoo/provider` before X4 binding verification.
- n8n must not add a direct Temporal credential, host, namespace or workflow node.
