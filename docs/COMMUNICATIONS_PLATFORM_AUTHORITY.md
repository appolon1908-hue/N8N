# Communications Platform Authority — n8n / Orchestration

## Purpose

This document defines `appolon1908-hue/N8N` as the orchestration authority for communications workflows while preserving Middleware as the only privileged cross-system write boundary.

## Permanent ownership

This repository owns:

- governed n8n workflow packs;
- workflow timing, branching, approvals and SLA escalation;
- communication-oriented orchestration templates;
- consumed event/command contract fixtures;
- workflow validation, deployment policy, observability and recovery evidence.

This repository does not own:

- direct provider execution;
- provider credentials;
- durable cross-system command/idempotency state;
- CRM source of truth;
- identity issuance;
- gateway/edge policy;
- public SDK contracts.

## Required path

```text
n8n workflow
    -> authenticated Middleware API only
    -> Middleware policy/idempotency/ledger
    -> channel adapter
    -> Klyrow / Telnexa / VICIdial / other governed provider
```

n8n must never become an alternate write path to Odoo, VICIdial, Jasmin/Telnexa, Klyrow/Postal, Keycloak administration, Kong administration, databases or provider APIs.

## Communications orchestration use cases

Approved workflow families may include:

- send-after-approval orchestration;
- follow-up sequencing;
- SLA timers and escalations;
- callback scheduling;
- channel fallback decisions based on policy/capability;
- human review steps;
- notification routing;
- event-driven CRM follow-up;
- reconciliation escalation;
- suppression/consent exception review;
- deliverability/operations alerting.

Business effects are requested through versioned Middleware commands. Workflow logic must not construct arbitrary provider URLs or select unrestricted runtime endpoints.

## Event consumption

n8n may consume canonical, signed, tenant-bound events from Middleware. Inbound event handling must enforce:

- exact raw-body signature verification at the receiving boundary;
- timestamp tolerance;
- event ID replay protection;
- tenant/source/event-type allowlists;
- full schema validation;
- separate inbound and outbound credentials.

Provider-local payloads must be normalized by the owning provider/Middleware boundary before workflow use.

## Credential rules

1. n8n receives a narrowly scoped service identity for Middleware only.
2. Provider credentials are prohibited in workflow exports.
3. Odoo/VICIdial/Klyrow/Telnexa database credentials are prohibited.
4. Inbound event credentials/signing secrets are separate from outbound API access credentials.
5. Secrets remain in the approved runtime secret store, never Git.

## Safety rules

1. Workflow source remains inactive by default until separately approved.
2. A merge never activates a production workflow.
3. No arbitrary URL, workflow ID, shell/code execution or local command capability may be introduced without explicit security review.
4. Effectful Middleware commands require deterministic idempotency keys.
5. Workflow retries must not blindly repeat an indeterminate external effect; they must inspect Middleware operation state/reconciliation.
6. Tenant context must come from authenticated/validated workflow inputs and Middleware authorization.
7. Workflows must honor capability, consent, suppression and kill-switch results from Middleware.
8. Workflow logs must not expose tokens, message bodies containing sensitive data, provider secrets or PII beyond approved policy.
9. Production and staging credentials/endpoints remain separated.
10. Emergency disabling of a workflow must not erase durable Middleware/provider state.

## Cross-repository contract requirements

Communications workflow changes may require coordinated evidence from:

- `SDK-repository` — public/event contract definitions when workflow inputs change;
- `Middleware-` — command/event endpoints and durable behavior;
- `Keycloak` — n8n service identity/scopes;
- `Kong` — route/scope policy if n8n crosses the gateway;
- `klyrow.com`, `telnexa`, `Vicidialer-Codestra` — only through their normalized Middleware contracts;
- `Odoo` — CRM/business-state mappings;
- `Caddy` — private/public ingress changes when applicable.

## Release gates

Before activating a communication workflow:

1. exact-head CI and workflow-policy validation pass;
2. all workflow effects route only to approved Middleware endpoints;
3. credentials are externally bound and least privilege;
4. inbound events reject tampering, expiry and replay;
5. duplicate command behavior is tested;
6. unknown/indeterminate operation states do not trigger duplicate effects;
7. tenant/campaign isolation is verified where applicable;
8. staging run proves expected commands/events without live external effects unless explicitly approved;
9. rollback/disable procedure is documented;
10. workflow activation approval is separate from source merge approval.

## Branching

Use short-lived `feature/*`, `fix/*`, `docs/*`, and `test/*` branches and promote through protected review. All executable workflow exports remain governed and inactive until separately activated.
