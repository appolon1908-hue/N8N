# Communications Platform Authority — n8n Orchestration

## Status

`SOURCE_ONLY` — this document defines source ownership and release gates. It does not activate a workflow, bind a credential, change DNS, call a provider, deploy n8n, or authorize an external effect.

## Purpose

`appolon1908-hue/N8N` is the orchestration-source authority for communications workflow designs. Codestra Middleware remains the only privileged cross-system command boundary and the owner of durable authorization, idempotency, replay protection, consent, suppression, kill switches, operation state, and audit records.

## Ownership

This repository owns:

- governed workflow designs and inactive exports;
- workflow timing, sequencing, branching, policy checkpoints, and SLA escalation;
- bounded retry, reconciliation, dead-letter, and operator-review paths;
- communications-oriented templates and workflow-pack declarations;
- consumed event/command fixtures, validation, observability, and recovery evidence.

This repository does not own:

- provider execution or provider credentials;
- CRM, identity, gateway, billing, ledger, or delivery source-of-truth state;
- durable cross-system command/idempotency records;
- public webhooks or raw provider callbacks;
- direct database, Odoo, VICIdial, Jasmin/Telnexa, Klyrow/Postal, Kyqra, Keycloak-administration, Kong-administration, or provider access.

## Required path

```text
public callback or application event
        -> Caddy/Kong and owning service boundary
        -> Codestra Middleware normalization and authorization
        -> durable tenant-bound automation job
        -> n8n orchestration
        -> governed Middleware command or operation query
        -> Middleware adapter
        -> approved system of record or provider
```

n8n must not become an alternate write path. Outbound HTTP is limited to the reviewed Middleware endpoint binding. Provider-local payloads are normalized before workflow use, and provider callbacks never terminate directly at public n8n endpoints.

## Covered workflow families

The communications authority includes source-only designs for:

- Odoo CRM intake, routing, follow-up, callbacks, campaign coordination, and support;
- VICIdial/contact-center scheduling, call-result reconciliation, QA, and agent-state coordination;
- Telnexa SMS onboarding, approval, send requests, inbound routing, receipts, opt-out, and provider-health handling;
- Klyrow email onboarding, domain and sender approval, transactional/campaign requests, bounce/complaint handling, suppression, and deliverability;
- Postly social content approval, scheduling, publication results, engagement leads, analytics, and account health;
- internal alerting, reconciliation, dead-letter review, privacy, retention, and suppression coordination.

Catalog membership and workflow-domain routing are controlled by `config/catalog-registry.v1.json`; catalog totals and implementation-pack totals remain separate.

## Event and job intake

n8n receives normalized, authenticated, tenant-bound work from Middleware. The approved intake contract must provide:

- event or job identity;
- tenant and actor/service identity context;
- correlation and causation identifiers;
- deterministic idempotency/replay context;
- workflow family and allowed command scope;
- lease or claim state when asynchronous execution is used;
- schema version and data-classification metadata.

The public edge or Middleware receiving boundary verifies provider signatures, timestamps, replay windows, source allowlists, and raw payload integrity. n8n validates the normalized envelope and its authorization/lease context; it must not reintroduce trust in unverified provider input.

## Credential and endpoint rules

1. n8n receives a narrowly scoped machine identity for the reviewed Middleware API only.
2. Provider, database, CRM, gateway-administration, and identity-administration credentials are prohibited.
3. Secret values and credential exports are prohibited in Git.
4. Staging and production identities, endpoints, queues, and evidence remain separate.
5. Public webhooks, arbitrary URLs, browser tokens, and user-supplied endpoint selection are prohibited.
6. Credential type/name bindings must be independently verified before executable exports are accepted.

## Effect safety

- Source merge never activates a workflow or capability.
- Each effectful command requires a deterministic idempotency key and an allowed command type.
- An unknown provider outcome is reconciled through Middleware before any retry.
- Retries are bounded and terminate in a durable dead-letter/operator path.
- Workflows honor capability, campaign, tenant, consent, suppression, integration-pause, and global kill-switch decisions returned by Middleware.
- Logs, node names, static data, and errors must not expose tokens, sensitive message bodies, government identifiers, payment data, recordings, or unnecessary personal data.
- Disabling a workflow must not erase durable Middleware or provider state.

## Cross-repository dependencies

A communications workflow change may require coordinated evidence from:

- `Middleware-` for canonical commands, operations, durable state, and adapters;
- `Keycloak` for machine clients, audiences, scopes, and role mappings;
- `Kong` and `Caddy` for approved ingress and gateway policy;
- `SDK-repository` for shared public/event contracts where applicable;
- Odoo, contact-center, Telnexa, Klyrow, Postly, and Kyqra repositories for their owned service contracts;
- `Infustruction-repo` for protected environment and immutable deployment controls.

The N8N repository consumes those authorities; it does not override them.

## Merge and activation gates

Before source merge:

1. the exact unchanged PR head is current with `main`;
2. required CI, catalog reconciliation, workflow policy, contract, secret, and security checks pass;
3. review and conversation-resolution requirements in the active ruleset are satisfied;
4. all committed workflows remain inactive and direct service access remains false.

Before staging execution:

1. endpoint, credential, editor-access, identity, and environment bindings are verified;
2. the exact immutable source/artifact is selected without rebuild or retagging;
3. tenant, campaign, idempotency, duplicate, timeout, retry, reconciliation, DLQ, and observability cases pass with external effects denied;
4. backup, isolated restore, disable, and rollback procedures are proven.

Before production activation:

1. the same certified immutable artifact passes a protected read-only canary;
2. source/digest readback, monitoring, readiness, rollback, and zero-unapproved-effect evidence pass;
3. each external capability receives separate explicit authorization;
4. calls, email, SMS, social publication, trading, wallet movement, or other live effects remain disabled unless that exact capability is approved.
