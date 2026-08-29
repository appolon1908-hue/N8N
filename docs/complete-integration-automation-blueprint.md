# Codestra complete n8n integration and automation blueprint

## Canonical status

**Reconciled:** 2026-08-28  
**Canonical repository:** `appolon1908-hue/N8N`  
**Canonical branch:** `main`  
**Document role:** architecture and promotion authority for n8n source; not deployment authorization

```text
BASELINE_GOVERNANCE_MERGED=YES
MAIN_RULESET_ACTIVE=YES
MAIN_BYPASS_ACTORS=NONE
BRANCH_CONSOLIDATION_COMPLETED=YES
PRE_CONSOLIDATION_HISTORY_PRESERVED=YES
AUTOMATION_CONTRACT_REVIEW_CORRECTIONS_APPLIED=YES
SOURCE_ONLY=YES
CANONICAL_WORKFLOWS_ACTIVE_IN_GIT=NO
DIRECT_PROVIDER_ACCESS=NO
EXTERNAL_EFFECT_CAPABILITIES_ENABLED=NO
RUNTIME_PATHS_VERIFIED=NO
N8N_RUNTIME_POLICY_VERIFIED=NO
STAGING_2_36_8_CERTIFICATION=PARTIAL_REMEDIATION
PRODUCTION_PROMOTION_AUTHORIZED=NO
PRODUCTION_CHANGED_BY_THIS_DOCUMENT=NO
```

The August 27 design assumed that the governance baseline and the long stacked branch family were still pending. That is no longer the repository state. On August 28 the accepted source was consolidated into canonical `main`, the pre-consolidation references were preserved as evidence/archive tags, and the old stacked PR/branch model was retired. New work must use short-lived branches from current protected `main`.

n8n is the Codestra orchestration engine. It is not an authorization authority, integration gateway, provider adapter, durable business ledger, or system of record.

## Runtime topology

```text
Public clients and provider callbacks
                 |
               Caddy
                 |
                Kong
                 |
             Middleware
  durable inbox / event ledger / outbox
                 |
       private wake-up and claim
                 v
                n8n
     timing, branching and approvals
                 |
        governed commands only
                 v
             Middleware
                 |
  Odoo / VICIdial / Asterisk / Telnexa /
  Klyrow / Kyqra / Postly / Provisioning /
  MoneyBee / Breero / LARIM-A / Freight /
  Beyvra / approved future adapters
```

## Non-negotiable trust boundaries

1. Public webhooks terminate at Caddy, Kong and Middleware—not n8n.
2. n8n may call the reviewed Middleware API only.
3. n8n never receives direct credentials for Odoo, VICIdial, Asterisk, Jasmin, Postal, Mautic, Kyqra, Postly, Keycloak administration, Kong administration, product databases, PostgreSQL, Redis or provider APIs.
4. Middleware owns authentication context, tenant isolation, canonical validation, idempotency, semantic replay detection, capabilities, consent, suppression, provider adapters, command state, retry, dead letters, audit and reconciliation.
5. A successful n8n execution is not proof that an external effect succeeded. Destination read-back through Middleware is authoritative.
6. Every canonical workflow export is inactive in Git. Import, publish, activate and enable a Middleware capability are separate reviewed operations.
7. Existing production or staging runtime workflows are inventory/evidence only until reconciled into a protected workflow pack and promoted through this policy.

## Canonical repository model

The repository is a single governed n8n source tree. Product-specific n8n repositories and permanent branch forests are prohibited.

```text
main
  automations/      machine-readable workflow catalog and product packs
  config/           capabilities, cells, services, runtime and policy state
  contracts/        consumed automation API and operation-policy contracts
  deploy/           non-applying deployment and release-preflight material
  docs/             architecture, reviews, certification and runbooks
  observability/    health/readiness metrics and alerts
  operations/       recovery, audit and branch-preservation evidence
  scripts/          source and policy validators
  tests/            policy, contract and compose validation
  workflows/        inactive workflow packs and safe templates
```

Accepted historical branch tips are preserved as evidence. They are not release references and must not be revived as parallel implementation authorities.

## Durable wake-and-claim handoff

A direct n8n webhook alone is not durable enough.

Middleware creates, in one database transaction:

```text
normalized_event
automation_job
automation_dispatch_outbox
audit_record
```

The outbox worker sends n8n a private wake containing identifiers only:

```json
{
  "job_id": "uuid",
  "workflow_key": "codestra.crm.lead-intake.v1",
  "workflow_version": 1,
  "correlation_id": "correlation-id",
  "delivery_token": "one-use-signed-token"
}
```

The workflow calls `POST /v2/automation/jobs/claim`. Middleware validates the machine client, granular scope, allowed workflow family, job tenant, workflow version, effective capability and policy snapshot before granting a lease and returning the safe payload.

During execution n8n records safe steps and sends heartbeats. Every business or provider effect is requested through `POST /v2/automation/commands`. Commands are idempotent and may return `ACCEPTED`, `BLOCKED`, `SUBMITTED`, `UNKNOWN`, `COMPLETED`, `FAILED` or `CANCELLED`.

`UNKNOWN` requires destination reconciliation before another externally effective request is allowed.

The workflow completes through exactly one terminal endpoint:

```text
POST /v2/automation/jobs/{job_id}/complete
POST /v2/automation/jobs/{job_id}/fail
```

A lost wake is redelivered from the durable outbox. A dead n8n worker loses its lease. A stale execution cannot record steps, issue governed commands, or complete the job.

## Authorization contract

The protected review corrections are binding:

- generic `automation.execute` and generic `automation.command` scopes are prohibited;
- each API operation uses a granular scope from `contracts/operation-policy.v2.json`;
- each machine client is restricted to explicit workflow families and command prefixes;
- wake-bound claims require `job_id`, a one-use `delivery_token`, workflow identity and execution identity;
- step evidence requires the current `lease_token` and `execution_id`;
- governed commands require job, lease, execution, workflow and step context;
- Middleware derives authoritative tenant and actor identity from durable job/token state;
- n8n-supplied tenant/actor values are assertions only and cannot authorize access;
- dead-letter replay is a protected request, not direct replay execution;
- replay requires non-self approval, idempotency, expected version, effect fingerprint, safe-replay classification, capability recheck and audit evidence.

## Automation state machine

```text
PENDING
  -> DISPATCHING
  -> CLAIMED
  -> RUNNING
      -> WAITING_APPROVAL
      -> WAITING_TIMER
      -> WAITING_COMMAND
      -> RETRY_SCHEDULED
      -> COMPLETED
      -> FAILED_TERMINAL
      -> DEAD_LETTER
      -> CANCELLED

DEAD_LETTER
  -> OPERATOR_REVIEW
  -> REPLAY_APPROVED
  -> PENDING
```

Transitions use row locking or optimistic concurrency. Lease tokens prevent stale completion. Timeouts become `UNKNOWN` until reconciled. Cross-tenant replay is forbidden.

Long human waits belong in Middleware durable state. n8n records `WAITING_APPROVAL` or `WAITING_TIMER` and exits; Middleware creates a new resume job when the condition becomes effective.

## Shared reusable workflows

Every product workflow should use versioned shared components:

```text
00 Validate Wake Envelope
01 Claim Middleware Job
02 Verify Workflow and Capability
03 Start or Extend Lease
04 Request Governed Command
05 Poll or Reconcile Command
06 Record Safe Step Evidence
07 Request Human Approval
08 Schedule Durable Resume
09 Complete Job
10 Fail or Retry Job
11 Report Dead Letter
12 Sanitize Incident Alert
13 Release Local Resources
```

## System ownership

| Domain | Authority | n8n role |
|---|---|---|
| Human and machine identity | Keycloak | Consume validated subject, tenant and granular scopes |
| Cross-system writes | Middleware | Request governed commands |
| CRM and business history | Odoo 19 | Sequence approved CRM operations |
| Calls and campaigns | VICIdial/Asterisk | Follow call-result and callback workflows |
| SMS control/delivery | Telnexa/Jasmin | Sequence sends and reconcile MO/DLR events |
| Email control/delivery | Klyrow/Postal | Sequence approved sends and lifecycle handling |
| Crawler jobs/results | Kyqra/Crawlee/Playwright | Sequence jobs and human review |
| Social publication | Postly adapter | Coordinate approved publications |
| Provisioning | Provisioning service | Coordinate multi-system lifecycle requests |
| Product business state | Product backend | Sequence product-specific commands |
| Durable automation state | Middleware PostgreSQL | Execute leased jobs only |
| n8n queue coordination | n8n Redis | Worker dispatch only |

## Software flows

### Odoo CRM

```text
Form or product event -> Middleware validation -> automation job -> n8n
-> Middleware Odoo command -> Odoo read-back -> optional Kyqra review
-> approved Odoo update -> optional Klyrow/Telnexa message request
```

### Telephony

```text
VICIdial/Asterisk adapter -> Middleware inbox -> normalized call event
-> Odoo history -> n8n follow-up -> Middleware callback/message commands
```

n8n never places a call directly.

### SMS

```text
Odoo/product request -> Middleware -> n8n timing/approval
-> Middleware Telnexa command -> Jasmin/provider
-> MO/DLR -> Middleware -> n8n reconciliation -> business history
```

Opt-out events take the privacy/suppression path before any later send.

### Email

```text
Odoo/product/Klyrow request -> Middleware policy -> optional n8n timing/approval
-> Middleware Klyrow command -> Postal -> lifecycle event
-> Middleware -> n8n reconciliation -> business history
```

Keycloak SECURITY email is not synchronously orchestrated by n8n.

### Crawler

```text
Discovery request -> Middleware target policy -> n8n
-> Middleware Kyqra command -> crawler execution -> signed result
-> Middleware -> human review -> approved writeback
```

### Provisioning

```text
Manager approval -> Middleware -> n8n lifecycle coordination
-> Middleware provisioning command -> destination adapters and read-back
-> completion only when the required resource tuple agrees
```

### Privacy

```text
Privacy request -> identity and tenant validation -> protected approval
-> n8n coordinates Middleware commands -> every adapter returns read-back
-> Middleware reconciliation -> final privacy evidence
```

n8n never deletes directly from databases.

## Runtime hardening

Target queue-mode topology:

```text
protected editor route -> n8n-main -> PostgreSQL -> Redis queue -> n8n workers
```

Required controls:

- one immutable n8n version across main, webhook and workers;
- external secret provider and managed n8n credential references;
- least-privilege PostgreSQL and Redis identities;
- no public editor or webhook exposure without reviewed gateway policy;
- public API, community packages, templates, diagnostics and personalization disabled unless separately approved;
- Code, shell, SSH, FTP, Git and local-file nodes excluded from canonical packs;
- successful execution payloads not retained by default;
- bounded, redacted error retention;
- readiness for main, webhook and every worker;
- egress allowlist to Middleware only;
- encrypted backup, restore and rollback evidence before production promotion.

## Runtime evidence state

The repository now contains runtime certification evidence, but evidence does not automatically change `config/runtime-paths.json` or `config/n8n-policy.json` from `UNVERIFIED`.

Current source-controlled facts:

- the canonical governance baseline is merged;
- the main no-bypass ruleset is active;
- staging n8n `2.36.8` has been exercised as a remediation/soak candidate;
- production and staging credential inventories were recorded as metadata only;
- source-controlled health, queue, execution, database, backup and restore monitoring was added;
- production promotion remains blocked by unresolved runtime-policy, credential, workflow-reconciliation and certification requirements;
- broad production workflow activation is not approved.

The authoritative source files remain:

```text
config/runtime-paths.json
config/n8n-policy.json
docs/CREDENTIAL-METADATA-AUDIT.md
docs/PRODUCTION-ACTIVATION-INTENT.md
docs/STAGING-CERTIFICATION-2.36.8.md
observability/n8n-metrics.sh
observability/n8n-readiness.rules.yml
```

## Credential model

Recommended machine clients remain domain-scoped:

```text
n8n-platform-runtime
n8n-identity-automation
n8n-crm-automation
n8n-telephony-automation
n8n-messaging-automation
n8n-social-automation
n8n-crawler-automation
n8n-product-automation
n8n-privacy-automation
n8n-operations-automation
```

All audiences target Middleware only. Credential aliases and types are reviewed runtime configuration; secret values never appear in workflow exports or Git.

## Branch and promotion model

The old August 27 permanent branch plan is superseded.

```text
protected main
  -> short-lived feature/fix/docs branch
  -> exact-head CI
  -> independent code-owner review on unchanged final SHA
  -> protected merge with no bypass
  -> inactive staging import from protected content
  -> no-effect E2E and runtime certification
  -> published workflow version
  -> immutable release manifest
  -> inactive production import
  -> separate workflow activation approval
  -> separate Middleware capability canary
```

Rules:

1. Branch from current `main`, not an archived pre-consolidation branch.
2. One coherent change family per PR.
3. Do not force-push protected history.
4. Do not revive old stacked branches as implementation authorities.
5. Production is a one-way consumer of reviewed releases and is not a normal editing environment.
6. Merge alone never activates a workflow or enables an external-effect capability.

## Test requirements

Every executable workflow family must prove with real implementation evidence—not design assertions:

```text
WORKFLOW_ACTIVE_FALSE=PASS
PIN_DATA_EMPTY=PASS
EMBEDDED_CREDENTIALS=NONE
PUBLIC_WEBHOOKS=NONE
DIRECT_PROVIDER_ENDPOINTS=NONE
DIRECT_DATABASE_NODES=NONE
BLOCKED_NODES=NONE
TENANT_ISOLATION=PASS
EXACT_REPLAY=PASS
CONFLICTING_REPLAY=PASS
CONCURRENT_DUPLICATE=PASS
CAPABILITY_DISABLED=PASS
EXPIRED_JOB_BLOCKED=PASS
LEASE_LOSS_BLOCKS_COMPLETION=PASS
UNKNOWN_OUTCOME_RECONCILED=PASS
BOUNDED_RETRY=PASS
DEAD_LETTER=PASS
APPROVAL_REJECTION=PASS
N8N_RESTART_RECOVERY=PASS
MIDDLEWARE_OUTAGE_RECOVERY=PASS
STAGING_EXTERNAL_EFFECTS=ZERO
BACKUP_RESTORE=PASS
ROLLBACK_REHEARSAL=PASS
```

`PASS` is reserved for implementation/test evidence. Contract-only or design-only work must use truthful states such as `DESIGN_REVIEWED`, `IMPLEMENTATION_PENDING` or `TEST_EVIDENCE_PENDING`.

## Release evidence

A production release manifest must bind at least:

```text
source_git_sha
n8n_image_digest
workflow_key
workflow_export_sha256
n8n_workflow_id
n8n_version_id
published_version
active_state
middleware_contract_version
required_credential_alias
required_capability
runtime_policy_sha256
backup_evidence_sha256
rollback_evidence_sha256
independent_approval
change_id
```

Schema validation is not cryptographic evidence verification. SBOM, provenance, signatures, vulnerability evidence, backup/restore evidence and rollback evidence must be independently verified by the protected release process.

## Current release decision

```text
BASELINE_GOVERNANCE_MERGED=YES
MAIN_RULESET_ACTIVE=YES
REVIEW_CORRECTIONS_APPLIED=YES
BRANCH_CONSOLIDATION_COMPLETED=YES
RUNTIME_PATHS_VERIFIED=NO
N8N_EDITION_VERIFIED=NO
ENDPOINT_BINDING_VERIFIED=NO
CREDENTIAL_BINDING_VERIFIED=NO
EDITOR_POLICY_VERIFIED=NO
CANONICAL_EXECUTABLE_WORKFLOW_PROMOTION_READY=NO
EXTERNAL_EFFECT_CAPABILITIES_ENABLED=NO
BROAD_PRODUCTION_ACTIVATION_APPROVED=NO
PRODUCTION_PROMOTION=NO_GO
```

## Next implementation gates

1. Reconcile verified runtime evidence into `config/runtime-paths.json` only after independent evidence review.
2. Reconcile edition, endpoint, credential and editor evidence into `config/n8n-policy.json` only after independent review.
3. Finish credential ownership/domain/scope/rotation remediation.
4. Replace hardcoded authorization remnants before accepting runtime workflow exports into canonical packs.
5. Build executable shared automation runtime only against the corrected granular operation policy.
6. Promote one no-effect workflow family at a time through isolated staging.
7. Prove duplicate, replay, tenant, lease-loss, restart, unknown-outcome, backup and rollback behavior.
8. Keep all external-effect capabilities false until a separate production canary is approved.
