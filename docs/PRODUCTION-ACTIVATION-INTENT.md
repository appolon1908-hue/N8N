# Production activation intent — 2026-08-28

## Decision

Broad production activation is **not approved**. The presence of 130 production workflows is inventory, not activation intent. Production currently has one active workflow and 129 inactive workflows.

| Group | Current state | Production intent |
|---|---:|---|
| External Webhook Certification Sink V1 | Active | Certification-only. Keep fail-closed and internal; deactivate after the upgrade certification window unless an owner supplies a managed authorization dependency and successful synthetic test. |
| 74 workflows structurally matching the old repository and production | Inactive | Evidence-backed legacy candidates only. They contain Code/direct HTTP patterns and cannot enter canonical workflow packs until rewritten to pass policy. |
| Other production-only workflows | Inactive | Quarantine as runtime evidence. No activation or canonical import without owner, product pack, contract, tests, and rollback plan. |
| Staging social workflows | 11 active in staging | Staging-only. Do not promote while hardcoded Authorization remnants, task-runner isolation, and callback certification remain unresolved. |

## Activation gate for any workflow

A workflow may be proposed for production only when it has a named product pack and owner, inactive sanitized source in protected main, middleware-only destinations, managed credential references, explicit domain/scope/rotation metadata, idempotency and dead-letter behavior, isolated staging tests, observability, rollback evidence, and an explicit approval record. Activation is a separate controlled operation after merge; merge alone never activates a workflow.
