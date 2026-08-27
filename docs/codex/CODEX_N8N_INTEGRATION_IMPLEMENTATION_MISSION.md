# Codex Mission — Complete Codestra n8n Integration and Automation Control Plane

## Authority

```text
N8N repository:
appolon1908-hue/N8N

Current baseline PR:
#1

Current baseline branch:
platform/services-middleware-automations-designs

Current recorded baseline head:
c7130d73b1618b3bb82cc635dde6049190a9d4ec

Middleware repository:
appolon1908-hue/Middleware-

Workflow catalog:
96 design-only workflows

Production deployment:
NOT AUTHORIZED BY THIS MISSION
```

Read completely before changing code:

```text
CODESTRA_N8N_COMPLETE_INTEGRATION_AUTOMATION_BLUEPRINT.md
N8N_AUTOMATION_CATALOG_V2.json
MIDDLEWARE_AUTOMATION_API_V2.yaml
N8N_BRANCH_DEPENDENCY_MAP.json
```

## Mission objective

Build the integration control plane and shared n8n runtime foundation without connecting n8n directly to any business application, provider, or unrelated database.

The mission ends with reviewed, inactive, tested source and a conflict-free branch stack. It does not activate workflows or change production.

## Phase 0 — re-read current truth

1. Fetch every remote branch and PR #1.
2. Record current exact head/base SHAs, mergeability, checks, review state, and unresolved conversations.
3. Do not assume the recorded head is still current.
4. Do not assume runtime paths, n8n version, edition, endpoint, credentials, editor access, Compose identity, or backup paths.
5. Run only authorized read-only runtime inventory.
6. Sanitize and hash evidence before changing an `UNVERIFIED` value.
7. Keep every capability false.

Required conflict certification:

```bash
git fetch --all --prune
git status --short
git branch --show-current
git fsck --full
test -z "$(git ls-files -u)"
git diff --check
! git grep -nE '^(<<<<<<<|=======|>>>>>>>)' -- . ':!*.md' ':!docs/evidence/**'
```

## Phase 1 — baseline governance

PR #1 must:

- pass exact-head CI;
- receive independent approval for the unchanged final SHA;
- have every conversation resolved;
- merge through a protected `main`;
- prohibit force push, deletion, and administrator bypass.

Do not build executable workflow branches on an unmerged or mutable governance baseline.

## Phase 2 — contract branch

Create:

```text
contract/automation-control-plane-v2
```

Implement:

- versioned event and command envelopes with causation and trace metadata;
- automation jobs, steps, leases, attempts, approvals, dead letters, commands, and reconciliation models;
- OpenAPI operations from `MIDDLEWARE_AUTOMATION_API_V2.yaml`;
- compatibility and deprecation policy;
- stable safe error codes;
- positive and negative contract fixtures;
- tenant and actor authorization;
- workflow-to-scope mapping;
- capability mapping;
- PII classification and log redaction;
- exact replay and conflicting replay behavior.

Coordinate matching Middleware implementation in focused branches based on:

```text
core/integration-contracts
platform/postgresql
platform/redis
integration/keycloak
core/event-ledger-outbox
core/webhook-inbox-replay
core/workers-scheduler
integration/n8n
```

## Phase 3 — shared runtime

Create:

```text
shared/automation-runtime
```

Build inactive reusable workflows for:

```text
private wake validation
job claim
capability preflight
lease heartbeat
governed command request
command-state reconciliation
safe step evidence
human approval request
durable resume
terminal completion
retry and failure
dead-letter reporting
sanitized incident notification
resource cleanup
```

No direct providers, databases, public webhooks, Code, shell, SSH, Git, FTP, or local-file nodes.

## Phase 4 — runtime/security branches

Create focused branches:

```text
platform/runtime-path-verification
platform/n8n-runtime-policy
platform/n8n-queue-mode
platform/n8n-editor-identity
platform/n8n-secrets
```

Verify and implement only with evidence:

- exact n8n version and edition;
- queue-mode support;
- PostgreSQL and Redis roles, TLS, ACL, backup, restore, and recovery;
- immutable n8n image digest;
- exact Middleware endpoint binding and egress enforcement;
- exact credential aliases and types;
- protected editor route;
- gateway/Keycloak and native session policy;
- blocked-node policy;
- execution-data retention;
- encryption-key versioning and rotation;
- main and worker health/readiness;
- metrics and alerting.

## Phase 5 — product workflows

Implement one branch and pull request at a time:

```text
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
```

For every workflow:

1. Require a merged Middleware event and command contract.
2. Keep the export inactive.
3. Use only an approved Middleware credential.
4. Map one immutable workflow key and major version.
5. Declare one required capability.
6. Add exact replay, conflict, concurrent duplicate, tenant isolation, capability-off, expiry, lease-loss, retry, unknown-outcome, dead-letter, and rollback tests.
7. Add human approval where the catalog requires it.
8. Keep production data and secrets out of Git.

## Phase 6 — operations, privacy, and observability

Create:

```text
operations/human-approvals
operations/retry-dead-letter
operations/reconciliation
operations/incident-alerting
operations/release-canary
privacy/data-rights
observability/n8n
```

Dead-letter replay and privacy deletion require protected approval. Do not implement destructive automatic repair.

## Phase 7 — isolated staging only

After exact-head review and immutable release evidence:

- import workflows inactive;
- verify workflow export hashes, workflow IDs, and version IDs;
- keep all capabilities false;
- run synthetic no-effect end-to-end tests;
- test restart, queue, lease, duplicate, replay, unknown outcome, dead letter, approval, tenant isolation, egress denial, and rollback;
- prove zero calls, SMS, email, social publication, crawler writeback, lead publication, payment, or provider write.

Do not activate production workflows in this mission.

## Required validation

```text
SOURCE_SHA_IDENTITY=PASS
CONFLICT_MARKER_SCAN=PASS
WORKFLOW_JSON_SCHEMA=PASS
WORKFLOWS_ACTIVE_FALSE=PASS
PIN_DATA_EMPTY=PASS
EMBEDDED_CREDENTIALS=NONE
PUBLIC_WEBHOOKS=NONE
DIRECT_PROVIDER_ENDPOINTS=NONE
DIRECT_DATABASE_NODES=NONE
BLOCKED_NODES=NONE
CONTRACT_FIXTURES=PASS
TENANT_ISOLATION=PASS
EXACT_REPLAY=PASS
CONFLICTING_REPLAY=PASS
CONCURRENT_DUPLICATE=PASS
CAPABILITY_DISABLED=PASS
LEASE_LOSS=PASS
UNKNOWN_OUTCOME_RECONCILIATION=PASS
BOUNDED_RETRY=PASS
DEAD_LETTER=PASS
APPROVAL_REJECTION=PASS
N8N_RESTART_RECOVERY=PASS
MIDDLEWARE_OUTAGE_RECOVERY=PASS
STAGING_EXTERNAL_EFFECTS=ZERO
BACKUP_RESTORE=PASS
ROLLBACK_REHEARSAL=PASS
```

## Final report

Return:

1. repository and working directory;
2. starting baseline SHA;
3. current protected base SHA;
4. every branch and commit;
5. every pull request;
6. contract version;
7. workflow catalog count;
8. exact workflow export hashes;
9. commands and tests;
10. runtime and edition evidence;
11. endpoint and credential-binding evidence;
12. editor and egress evidence;
13. PostgreSQL and Redis evidence;
14. backup and restore evidence;
15. immutable image evidence;
16. staging no-effect evidence;
17. rollback result;
18. unresolved blockers;
19. `BASELINE_MERGED=YES|NO`;
20. `WORKFLOWS_IMPORTED=YES|NO`;
21. `WORKFLOWS_ACTIVE=YES|NO`;
22. `PRODUCTION_CHANGED=YES|NO`.

Never claim an Odoo, telephony, messaging, crawler, provider, product, or production result without runtime read-back.
