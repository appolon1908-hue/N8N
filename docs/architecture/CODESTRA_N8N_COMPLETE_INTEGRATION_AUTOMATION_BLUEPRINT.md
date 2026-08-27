# Codestra Complete n8n Integration and Automation Blueprint

**Status:** target design and implementation outline  
**Generated:** 2026-08-27T16:02:00.468240+00:00  
**Current N8N repository:** `appolon1908-hue/N8N`  
**Current scaffold branch:** `platform/services-middleware-automations-designs`  
**Default workflow activation:** `DISABLED`  
**Live deployment authorized by this document:** **NO**

## 1. Executive decision

n8n is the Codestra **orchestration engine**, not the integration authority and not a system of record.

```text
External systems and portals
            |
          Caddy
            |
           Kong
            |
        Middleware
   durable inbox/outbox
            |
      private wake-up
            v
           n8n
   orchestration only
            |
    governed commands
            v
        Middleware
            |
    approved adapters
            |
Odoo / VICIdial / Asterisk / Telnexa / Klyrow / Kyqra /
Postly / Provisioning / MoneyBee / Breero / LARIM-A / Freight / Beyvra
```

### Non-negotiable boundaries

1. Public provider callbacks terminate at Caddy/Kong/Middleware, never directly at n8n.
2. n8n receives no Odoo, VICIdial, Asterisk, Jasmin, Postal, Mautic, Kyqra, Keycloak-administration, Kong-administration, PostgreSQL, Redis, or provider credentials.
3. n8n has one outbound trust destination: the reviewed Middleware API.
4. Middleware owns tenant authorization, contracts, validation, idempotency, replay protection, capability gates, consent, suppression, command state, provider adapters, durable inbox/outbox, retries, dead letters, audit, and reconciliation.
5. A successful n8n execution does not prove a provider effect succeeded. Destination read-back and Middleware reconciliation are authoritative.
6. Every workflow export is inactive in Git. Import, publish, activation, and capability enablement are separate operations.
7. Every live-effect capability remains disabled until a separately approved, tightly bounded canary.

## 2. Current repository position

The N8N repository has a source-governance scaffold in draft PR #1, not a merged automation platform. Before executable workflows are developed:

1. Merge the governance baseline through protected controls.
2. Verify the exact n8n version and edition.
3. Verify runtime paths, Compose identity, network, data volume, backup path, secret provider, and reverse proxy.
4. Verify the Middleware endpoint binding, credential aliases, editor access, authentication/session policy, and outbound egress.
5. Keep every capability false.
6. Build the control-plane API and shared runtime before product workflows.

## 3. Runtime architecture

### 3.1 Environment separation

```text
development
  editable
  synthetic data only
  no production credentials
  workflows inactive by default

staging
  protected import
  staging Keycloak and Middleware credentials
  isolated PostgreSQL and Redis
  every external-effect capability false

production
  protected or read-only editor posture
  one-way promotion from protected release
  no normal workflow authoring
  immutable image digest
  activation and capability canaries approved separately
```

### 3.2 Queue-mode topology

```text
Protected editor route
          |
       n8n-main
          |
     PostgreSQL
          |
    Redis queue
      /       \
worker-1     worker-N
```

Required posture:

- PostgreSQL is durable n8n state.
- Redis is queue and ephemeral coordination, not business authority.
- Main and workers run the same immutable n8n version.
- Main and worker readiness checks validate their dependencies.
- Successful execution payloads are not retained by default.
- Error execution data is bounded, redacted, and pruned.
- Queue-mode binary data remains database-backed until a reviewed shared object-store design exists.
- Code, shell, SSH, Git, FTP, and local-file nodes remain excluded.
- Public API, templates, diagnostics, personalization, and community packages remain disabled unless separately approved.
- Runtime secrets are external to Git.

### 3.3 Network policy

```text
Allowed
  n8n -> reviewed private Middleware HTTPS endpoint
  n8n -> its own PostgreSQL
  n8n -> its own Redis
  approved monitoring scrapes
  protected editor ingress

Denied
  n8n -> public Internet
  n8n -> Odoo or product databases
  n8n -> Keycloak administration
  n8n -> VICIdial/Asterisk
  n8n -> Telnexa/Jasmin
  n8n -> Klyrow/Postal/Mautic
  n8n -> Kyqra/Crawlee/Playwright
  n8n -> Postly
  n8n -> unrelated providers
```

## 4. Durable Middleware-to-n8n handoff

A direct webhook alone is not durable enough. Use a **wake-up plus claim** design.

### 4.1 Middleware transaction

When an event should start an automation, Middleware writes in one transaction:

```text
normalized_event
automation_job
automation_dispatch_outbox
audit_record
```

### 4.2 Private wake-up

The Middleware outbox worker sends a small private wake-up:

```json
{
  "job_id": "uuid",
  "workflow_key": "codestra.crm.lead-intake.v1",
  "workflow_version": 1,
  "correlation_id": "correlation-id",
  "delivery_token": "one-use-signed-token"
}
```

The private route is authenticated, source-allowlisted, rate-limited, and never used as a public provider callback.

### 4.3 Atomic claim

The workflow calls:

```http
POST /v2/automation/jobs/claim
```

Middleware:

- validates the n8n service identity and workflow scope;
- validates tenant and workflow mapping;
- validates the effective capability and policy snapshot;
- atomically grants a lease;
- returns only the safe payload;
- records the n8n workflow version and execution ID.

### 4.4 Heartbeat and terminal result

n8n records steps and heartbeats, then calls exactly one terminal endpoint:

```text
POST /v2/automation/jobs/{job_id}/complete
POST /v2/automation/jobs/{job_id}/fail
```

A lost wake-up is redispatched from the durable outbox. A dead worker loses its lease and the job becomes eligible for governed recovery.

## 5. Job state machine

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

Rules:

- transitions use row locking or optimistic concurrency;
- lease tokens prevent stale completion;
- step evidence is idempotent;
- timeout means `UNKNOWN`, not automatically failed;
- unknown provider outcomes are reconciled before retry;
- replay preserves original tenant, correlation, causation, policy, and idempotency context;
- cross-tenant replay is forbidden.

## 6. Canonical command envelope v2

```json
{
  "event_id": "uuid",
  "tenant_id": "tenant-id",
  "correlation_id": "correlation-id",
  "causation_id": "causation-id",
  "idempotency_key": "stable-key",
  "type": "crm.lead.intake_requested",
  "version": 1,
  "occurred_at": "UTC timestamp",
  "not_before": null,
  "expires_at": null,
  "capability": "ODOO_WRITE",
  "dry_run": true,
  "actor": {
    "kind": "human|service|system",
    "issuer": "optional issuer",
    "subject": "immutable subject"
  },
  "payload": {},
  "traceparent": null
}
```

The proposed OpenAPI contract is supplied in `MIDDLEWARE_AUTOMATION_API_V2.yaml`.

## 7. Shared reusable subworkflows

All product workflows should use these versioned components:

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

A product workflow pins the shared major version it was tested against.

## 8. Project and naming model

```text
00 Platform and shared
10 Identity and provisioning
20 Odoo CRM
30 Telephony
40 Telnexa SMS
50 Klyrow Email
60 Kyqra Crawler
70 Postly Social
80 Product platforms
90 Operations and privacy
```

Workflow key:

```text
<namespace>.<domain>.<action>.v<major>
```

Required tags:

```text
owner:<team>
product:<product>
domain:<domain>
risk:<level>
contract:v<major>
capability:<name>
state:inactive
pii:<none|limited|high>
```

## 9. Automation catalog

`N8N_AUTOMATION_CATALOG_V2.json` contains **96** proposed workflows across:

- shared execution, retry, approval, dead letter, reconciliation, and canary control;
- Keycloak identity and multi-system provisioning;
- Odoo CRM, callbacks, appointments, support, campaigns, and consent;
- VICIdial/Asterisk calls, results, callbacks, agents, campaigns, recordings, and drift;
- Telnexa/Jasmin send, DLR, inbound SMS, opt-out, quota, and reconciliation;
- Klyrow/Postal send, lifecycle, inbound email, suppression, templates, security alerts, and domains;
- Kyqra/Crawlee execution, human review, enrichment, retry, and retention;
- Postly publishing, approval, engagement capture, and integration health;
- operations, privacy, retention, export, deletion, replay, and incident response;
- MoneyBee, Breero, LARIM-A, Freight Platform, and Beyvra product workflows.

All entries are `DESIGN_ONLY`, inactive, and Middleware-only.

## 10. Software communication flows

### 10.1 Odoo CRM

```text
Website or product form
 -> Kong
 -> Middleware validation and deduplication
 -> durable automation job
 -> n8n lead workflow
 -> Middleware Odoo command
 -> Odoo read-back
 -> optional Kyqra enrichment
 -> human review when ambiguous
 -> approved Odoo update
 -> optional Klyrow/Telnexa communication request
```

### 10.2 Telephony

```text
VICIdial/Asterisk adapter event
 -> Middleware signed inbox
 -> normalized call event
 -> Odoo call-history projection
 -> n8n follow-up sequence
 -> callback, appointment, email, or SMS request through Middleware
```

n8n never places calls directly.

### 10.3 SMS

```text
Odoo or product request
 -> Middleware
 -> n8n timing or approval
 -> Middleware Telnexa command
 -> Telnexa/Jasmin
 -> MO/DLR callback
 -> Middleware inbox
 -> n8n reconciliation
 -> Odoo or product history
```

Opt-out events take the global privacy/suppression path before any later send.

### 10.4 Email

```text
Odoo, product, or Klyrow request
 -> Middleware policy
 -> n8n timing or approval when required
 -> Middleware Klyrow command
 -> Klyrow/Postal
 -> provider lifecycle event
 -> Middleware
 -> n8n reconciliation
 -> Odoo or product history
```

Keycloak SECURITY email is not synchronously orchestrated by n8n.

### 10.5 Crawler

```text
Odoo or product discovery request
 -> Middleware target policy
 -> n8n orchestration
 -> Middleware Kyqra command
 -> Kyqra/Crawlee/Playwright
 -> signed result
 -> Middleware
 -> n8n human review
 -> approved Odoo or product writeback
```

### 10.6 Provisioning

```text
Manager-approved request
 -> Middleware
 -> n8n lifecycle coordination
 -> Middleware provisioning-service command
 -> Keycloak/Odoo/VICIdial/Klyrow/Telnexa adapters
 -> destination read-back
 -> completion only when the required tuple agrees
```

### 10.7 Privacy

```text
Privacy request
 -> Middleware identity and tenant validation
 -> protected approval
 -> n8n coordinates service-specific Middleware commands
 -> every adapter returns receipt and read-back
 -> Middleware reconciliation
 -> final privacy evidence
```

n8n never deletes directly from databases.

## 11. Human approval model

Approval authority belongs in Middleware and the approved operations surface, not in an n8n button alone.

Approval classes:

```text
CAMPAIGN_OWNER
UNDERWRITER
TELEPHONY_OWNER
PRIVACY_OFFICER
TWO_PERSON
CONTENT_OWNER
FINANCE_POLICY
RELEASE_OWNER
```

For long waits, the workflow records `WAITING_APPROVAL` and exits. Middleware creates a new resume job after approval instead of keeping thousands of open executions.

## 12. Credentials and scopes

Recommended Keycloak machine clients:

```text
n8n-platform-runtime
n8n-crm-automation
n8n-telephony-automation
n8n-messaging-automation
n8n-crawler-automation
n8n-product-automation
n8n-privacy-automation
n8n-operations-automation
```

All audiences target Middleware only.

Example scopes:

```text
automation.job.claim
automation.job.heartbeat
automation.job.complete
automation.command.crm
automation.command.telephony
automation.command.messaging
automation.command.crawler
automation.command.product
automation.approval.read
automation.operations.reconcile
automation.operations.replay
```

Exact credential aliases and credential types must be declared in a reviewed runtime policy; values stay outside Git.

## 13. Source control and promotion

```text
Development instance
 -> Git feature branch
 -> exact-head CI and PR review
 -> protected merge
 -> staging imports protected content
 -> staging publishes tested versions
 -> release manifest binds exact hashes and workflow IDs
 -> production imports protected release
 -> production activation remains separately approved
```

Do not push and pull from the same instance. Production is a one-way consumer of reviewed source and should not be used for normal editing.

When the installed edition lacks built-in environments/source control, use a reviewed private export/import deployment job. Do not weaken credential, workflow, or branch controls.

## 14. Release manifest

Bind all of the following:

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

Import, publish, activate, and enable a Middleware capability are four separate operations.

## 15. Test matrix

Every workflow branch must prove:

```text
schema validation
inactive export
no embedded credentials
no pin data
no direct provider or database endpoint
no public webhook
no blocked node
tenant isolation
exact replay produces one logical effect
conflicting replay is rejected
concurrent duplicate is safe
capability disabled blocks the effect
expired jobs do not run
lease loss blocks stale completion
timeout reconciles before retry
retry is bounded
dead letter is durable
operator replay is audited
human rejection stops the workflow
Middleware outage is recoverable
n8n restart is recoverable
Redis outage loses no business state
PostgreSQL outage fails closed
staging produces zero external effects
```

## 16. Observability

Metrics:

```text
automation_jobs_total{workflow,state}
automation_job_oldest_seconds{workflow,state}
automation_job_duration_seconds{workflow,result}
automation_retries_total{workflow,error_code}
automation_dead_letters_total{workflow}
automation_idempotency_conflicts_total{workflow}
automation_capability_blocks_total{capability}
automation_lease_expirations_total{workflow}
automation_command_unknown_total{adapter}
n8n_worker_heartbeat
n8n_queue_wait_seconds
n8n_execution_errors_total
```

Alerts:

- dead letter exists;
- oldest pending job exceeds SLA;
- repeated idempotency conflicts;
- worker heartbeat missing;
- lease-expiration spike;
- unknown provider outcomes;
- contract-version mismatch;
- external capability unexpectedly enabled;
- queue or execution error spik;
- production workflow edited outside release flow.

Logs contain correlation IDs and safe error codes, not customer payloads or secrets.

## 17. Branch plan

```text
platform/services-middleware-automations-designs
contract/automation-control-plane-v2
platform/runtime-path-verification
platform/n8n-runtime-policy
platform/n8n-queue-mode
platform/n8n-editor-identity
platform/n8n-secrets
shared/automation-runtime
automation/identity-provisioning
automation/odoo-crm
automation/vicidial-telephony
automation/telnexa-sms
automation/klyrow-email
automation/kyqra-crawler
automation/postly-social
automation/moneybee-loans
automation/breero-marketplace
automation/larim-a-booking
automation/freight-operations
automation/beyvra
operations/human-approvals
operations/retry-dead-letter
operations/reconciliation
operations/incident-alerting
operations/release-canary
privacy/data-rights
observability/n8n
testing/contract-fixtures
testing/staging-no-effect-e2e
release/automation-v1
```

## 18. Cross-repository merge order

```text
1. Middleware core/integration-contracts
2. Middleware PostgreSQL and Redis primitives
3. Middleware Keycloak integration
4. Middleware event ledger/outbox
5. Middleware webhook inbox/replay
6. Middleware workers/scheduler
7. Middleware integration/n8n
8. N8N automation-control-plane contract
9. N8N shared runtime
10. Relevant Middleware provider or product adapter
11. Matching N8N workflow branch
12. Odoo module or product backend projection
13. Kong and Caddy routing when required
14. Observability
15. No-effect staging
16. Immutable release
17. Separate production capability canary
```

## 19. Current go/no-go

```text
N8N_BASELINE_PR_MERGED=NO
N8N_RUNTIME_PATHS_VERIFIED=NO
N8N_EDITION_VERIFIED=NO
N8N_ENDPOINT_BINDING_VERIFIED=NO
N8N_CREDENTIAL_BINDING_VERIFIED=NO
N8N_EDITOR_POLICY_VERIFIED=NO
EXECUTABLE_WORKFLOW_EXPORTS_READY=NO
EXTERNAL_EFFECT_CAPABILITIES_ENABLED=NO
LIVE_DEPLOYMENT_AUTHORIZED=NO
```

The first implementation work should be:

```text
1. protect and merge the source-governance baseline;
2. contract/automation-control-plane-v2;
3. matching Middleware API/database primitives;
4. shared/automation-runtime;
5. runtime-path and security verification;
6. one no-effect Odoo CRM pilot workflow;
7. staging duplicate, replay, tenant, restart, and rollback evidence.
```
