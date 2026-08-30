# N8N Protected Review and Merge Report

**Original review date:** 2026-08-27  
**Reconciled:** 2026-08-28  
**Repository owner:** `appolon1908-hue`  
**Canonical repository:** `appolon1908-hue/N8N`  
**Historical requested sequence:** N8N PR #1 → Middleware PR #15 → Keycloak PR #10 → N8N PR #9 → executable workflow implementation

> This file preserves the August 27 protected-review decision as historical evidence and records what changed on August 28. Old PR states and SHAs are not current release authority.

## Current executive decision

```text
AUGUST_27_PROTECTED_REVIEW_COMPLETED=YES
AUGUST_27_PROTECTED_MERGE_PERFORMED=NO

N8N_PR_1_CURRENT_STATE=CLOSED_UNMERGED_SUPERSEDED
N8N_PR_9_CURRENT_STATE=CLOSED_UNMERGED_SUPERSEDED
N8N_CANONICAL_BASELINE_PR_12=MERGED
N8N_RUNTIME_CERTIFICATION_PR_14=MERGED
MIDDLEWARE_PR_15=MERGED_SOURCE_CONTRACT
KEYCLOAK_PR_10=OPEN_DRAFT_DESIRED_STATE

MAIN_RULESET_ACTIVE=YES
MAIN_BYPASS_ACTORS=NONE
BRANCH_CONSOLIDATION_COMPLETED=YES
PRE_CONSOLIDATION_REFERENCES_PRESERVED=YES
REVIEW_CORRECTIONS_APPLIED_TO_N8N_SOURCE=YES

RUNTIME_PATHS_VERIFIED=NO
N8N_POLICY_VERIFIED=NO
CANONICAL_EXECUTABLE_RUNTIME_AUTHORIZED=NO
BROAD_WORKFLOW_ACTIVATION_AUTHORIZED=NO
EXTERNAL_EFFECT_CAPABILITIES_ENABLED=NO
PRODUCTION_PROMOTION=NO_GO
```

The August 27 decision was correct for the repository state at that time: the merge sequence was blocked by unprotected governance, absent independent approval and source/contract defects. The repository was subsequently corrected and consolidated rather than merging the original stacked N8N PR #1 and PR #9 directly.

## Reconciliation baseline

The August 28 reconciliation is based on canonical `main` at:

```text
MAIN_SHA=2bd572578e753cc73ee45c0d4ed712ba7428beea
PR_12_MERGE_SHA=5703d0e1a1f666abbfa33a12a910478cb824b9ef
PR_14_MERGE_SHA=2bd572578e753cc73ee45c0d4ed712ba7428beea
RULESET_ID=21758533
RULESET_NAME=Protect main without bypass
```

The active ruleset targets the default branch, blocks deletion and non-fast-forward updates, requires a pull request, at least one approval, stale-review dismissal, code-owner review, last-push approval, review-thread resolution, strict exact-SHA status checks and has no bypass actors.

---

# 1. Original August 27 verdict

The original review concluded:

```text
N8N_PR_1_REVIEW=CHANGES_REQUIRED
N8N_PR_1_PROTECTED_MERGE=BLOCKED
MIDDLEWARE_PR_15_REVIEW=CHANGES_REQUIRED
KEYCLOAK_PR_10_REVIEW=CHANGES_REQUIRED
N8N_PR_9_REVIEW=CHANGES_REQUIRED
EXECUTABLE_N8N_IMPLEMENTATION=DO_NOT_BEGIN
LIVE_SERVER_CHANGED=NO
WORKFLOW_ACTIVATION=NO
PRODUCTION_DEPLOYMENT=NO
```

That verdict remains the correct historical record. It must not be rewritten as if PR #1 or PR #9 passed and merged through the original sequence.

---

# 2. N8N PR #1 reconciliation

## Historical identity

```text
PR=1
HEAD_BRANCH=platform/services-middleware-automations-designs
ORIGINAL_REVIEWED_SHA=30936448bb911a5dc7ba5311e2125da924c29d16
BASE_BRANCH=main
HISTORICAL_STATE=OPEN_DRAFT
```

## Current outcome

```text
PR_1_STATE=CLOSED
PR_1_MERGED=NO
FINAL_HEAD_SHA=5e24ed88fda0c6d26c355eeca122dc76141b9243
SUPERSEDED_BY_CANONICAL_PR_12=YES
```

The useful governance/source work was hardened on the branch and then canonicalized through PR #12 instead of merging PR #1 itself.

## Finding reconciliation

| August 27 finding | Current state | Canonical evidence / disposition |
|---|---|---|
| P0 endpoint path traversal | **FIXED / SUPERSEDED** | URL validation was hardened before consolidation; PR #1 final description records repeated decoding, traversal rejection and default-deny node validation. |
| P0 n8n data volume not external | **FIXED / SUPERSEDED** | Canonical Compose validation requires external provisioning and semantic object validation. |
| P1 substring-only Compose policy | **FIXED / SUPERSEDED** | Canonical policy renders Compose config and validates semantic service/volume/network/secret objects. |
| P1 release evidence self-attestation | **FIXED IN SOURCE MODEL** | Manifest schema validation is explicitly separated from protected cryptographic artifact verification. Production release evidence is still not complete. |
| P1 CODEOWNERS independence | **GOVERNANCE CONFIGURED** | Canonical CODEOWNERS designates an independent operations/security reviewer; the live ruleset requires code-owner and last-push approval. |
| `main` unprotected / no ruleset | **FIXED** | Active repository ruleset `21758533`, no bypass actors. |

## Remaining N8N governance limitation

The existence of a ruleset does not itself certify any future change. Every new PR still requires exact-head CI and a qualifying independent approval on the unchanged final SHA.

---

# 3. Middleware PR #15 reconciliation

## Current outcome

```text
PR=15
REPOSITORY=appolon1908-hue/Middleware-
STATE=CLOSED
MERGED=YES
FINAL_HEAD_SHA=6a55aa7e35c848fc6bb7cf553d21420dcbbdf914
CONTRACT_STATUS=SOURCE_ONLY
RUNTIME_IMPLEMENTATION_STATUS=NOT_IMPLEMENTED
```

Middleware PR #15 corrected the major contract-review findings:

- design requirements are no longer mislabeled as runtime `PASS`;
- granular operation policy binds endpoints to scopes, clients, workflow families and command prefixes;
- generic `automation.execute` and generic `automation.command` are prohibited;
- claims, steps and commands carry job/lease/execution context;
- tenant and actor are server-derived;
- replay requires protected approval, idempotency, expected version, effect fingerprint, safe classification and capability recheck;
- unknown provider outcomes must reconcile before retry.

### Current limitation

The merged PR remains a **source contract**, not proof that the durable database models, runtime API, authorization, idempotency, concurrency, lease recovery, no-effect staging, backup/restore or rollback behavior have been implemented and tested.

Therefore:

```text
MIDDLEWARE_CONTROL_PLANE_DESIGN=MERGED
MIDDLEWARE_RUNTIME_API_CERTIFIED=NO
MIDDLEWARE_DATABASE_PRIMITIVES_CERTIFIED=NO
MIDDLEWARE_STAGING_NO_EFFECT_EVIDENCE=NO
```

---

# 4. Keycloak PR #10 reconciliation

## Current outcome

```text
PR=10
REPOSITORY=appolon1908-hue/Keycloak
STATE=OPEN
DRAFT=YES
MERGED=NO
HEAD_SHA=fb2bda91e52385c0f673f358ab3147f93b42b766
PROVISIONING_STATE=declared-not-created
```

The source contract now contains the intended least-privilege direction:

- audience `middleware-api`;
- Client Credentials for machine identities;
- maximum token lifetime 300 seconds;
- generic scopes prohibited;
- explicit workflow-family and command-prefix restrictions;
- separate adapter identities;
- no provider credentials or realm-management roles;
- no live client/secret creation performed by the PR.

However, the PR is still open and draft and remains desired state only.

```text
KEYCLOAK_SOURCE_POLICY_CORRECTED=YES
KEYCLOAK_PR_10_PROTECTED_MERGED=NO
LIVE_KEYCLOAK_APPLY=NO
POST_APPLY_TOKEN_MATRIX=NO
ZERO_DRIFT_READBACK=NO
```

This remains a blocker for declaring the complete n8n machine-identity path production-ready.

---

# 5. N8N PR #9 reconciliation

## Historical identity

```text
PR=9
HEAD_BRANCH=contract/automation-control-plane-v2-20260827
ORIGINAL_REVIEWED_SHA=a6facc06a53d71c2c0914c1705f320afe4ba54ca
BASE_BRANCH=platform/services-middleware-automations-designs
```

## Current outcome

```text
PR_9_STATE=CLOSED
PR_9_MERGED=NO
FINAL_HEAD_SHA=6de4eca973454007adfb75ff2146180adeeaf57e
SUPERSEDED_BY_CANONICAL_PR_12=YES
```

The reviewed control-plane material was corrected and absorbed into canonical `main` by the consolidation instead of merging the stacked PR itself.

## Finding reconciliation

| August 27 finding | Current state | Canonical disposition |
|---|---|---|
| P0 scope mismatch | **FIXED IN CANONICAL SOURCE** | Granular operation policy is canonical; generic execute/command scopes prohibited. |
| P0 `StepRecord` missing lease/execution identity | **FIXED IN CONTRACT MODEL** | Step evidence requires current lease token and execution ID. |
| P0 commands not bound to active job lease | **FIXED IN CONTRACT MODEL** | Commands require job, lease, execution, workflow and step context. |
| P0 client-supplied tenant/actor authoritative | **FIXED IN CONTRACT MODEL** | Middleware derives authoritative context. |
| P0 ambiguous tokenless claim | **FIXED IN CONTRACT MODEL** | Wake-bound claims require job ID plus one-use delivery token and execution/workflow identity. |
| P0 replay lacks concurrency/idempotency controls | **FIXED IN CONTRACT MODEL** | Protected replay request requires idempotency, version, fingerprint, classification and approval. |
| P1 stale branch dependency map | **SUPERSEDED** | Old permanent branch forest was consolidated; historical refs preserved and future work branches from current `main`. |
| P1 automation catalog insufficient for capability policy | **FIXED IN CANONICAL SOURCE** | Canonical catalog and operation policy encode authorization profile, capabilities and replay classifications. |
| P1 trading prohibition incomplete | **HARDENED IN CANONICAL SOURCE** | Financial/trading/value-moving operations are prohibited from the n8n automation path; product automation is non-financial only where declared. |

### Important limitation

These are **source and contract corrections**, not proof that the executable shared runtime has passed the required PostgreSQL/Redis/API/staging evidence matrix.

---

# 6. Branch consolidation and archive state

The August 27 blueprint proposed a large permanent branch family. That structure is now superseded.

On August 28:

- the pre-consolidation remote references were captured;
- 72 remote references were grouped by 16 unique commit tips;
- unique non-main tips were preserved with immutable archive tags;
- the old stacked branches were removed from active development authority;
- canonical work was merged into `main` through PR #12;
- future changes must use short-lived branches from current `main`.

```text
OLD_BRANCH_FOREST_ACTIVE=NO
HISTORICAL_BRANCH_EVIDENCE_PRESERVED=YES
CANONICAL_DEVELOPMENT_BASE=main
```

Archive tags and the pre-canonical branch map are evidence only and must not be used as release references.

---

# 7. Runtime certification added after the original review

PR #14 merged additional source-controlled runtime evidence and controls:

- metadata-only credential audit;
- explicit production activation intent;
- n8n `2.36.8` staging certification record;
- health/readiness monitoring;
- queue and execution monitoring;
- database metrics;
- backup and restore evidence monitoring.

The staging certification is not a production approval. Remaining blockers include runtime-policy reconciliation, credential ownership/domain/scope/rotation remediation, hardcoded Authorization remnants in staging workflow exports, external task-runner requirements, successful webhook dependency certification, workflow reconciliation and an approved soak/promotion path.

Canonical configuration still truthfully reports:

```text
config/runtime-paths.json status=UNVERIFIED
config/n8n-policy.json status=UNVERIFIED
```

Do not change those states to `VERIFIED` merely because runtime notes or observations exist. Verification requires bound evidence and independent review.

---

# 8. Current executable-workflow freeze

The original freeze is partially superseded: source contracts and inactive source packs may now be developed through protected `main`, but **production-capable executable promotion remains blocked**.

Current rules:

```text
ALLOW_SOURCE_ONLY_WORKFLOW_PACK_DEVELOPMENT=YES
ALLOW_INACTIVE_SAFE_TEMPLATES=YES
ALLOW_CONTRACT_AND_TEST_IMPLEMENTATION=YES

NO_UNREVIEWED_WORKFLOW_IMPORT=YES
NO_BROAD_WORKFLOW_ACTIVATION=YES
NO_DIRECT_PROVIDER_ACCESS=YES
NO_DIRECT_DATABASE_ACCESS=YES
NO_EMBEDDED_CREDENTIALS=YES
NO_EXTERNAL_CAPABILITY_ENABLEMENT=YES
NO_PRODUCTION_PROMOTION=YES
```

Executable workflow families may proceed only one family at a time after the shared runtime and dependent authorization path have implementation evidence. Every workflow remains inactive by default.

---

# 9. Superseded merge order

The original August 27 merge order is retained for audit history only:

```text
1. Fix N8N PR #1 source findings.
2. Configure no-bypass main ruleset.
3. Add independent CODEOWNER/reviewer.
4. Rerun exact-head PR #1 CI.
5. Obtain independent approval.
6. Protected-merge PR #1.
7. Correct Middleware PR #15.
8. Correct Keycloak PR #10.
9. Correct N8N PR #9.
10. Retarget PR #9 to main.
11. Cross-repository exact-head validation.
12. Independent approvals.
13. Merge Middleware and Keycloak contracts.
14. Protected-merge N8N PR #9.
15. Begin shared automation runtime.
16. Add one executable workflow family per later PR.
```

It is no longer the operational sequence because N8N PR #1/#9 were superseded by the canonical consolidation and Middleware PR #15 has already merged.

---

# 10. Current protected implementation order

```text
1. Keep canonical N8N work based on protected main.
2. Complete and protected-merge the corrected Keycloak machine-identity contract.
3. Implement Middleware automation database primitives and runtime API behind the merged contract.
4. Prove authorization, tenant isolation, idempotency, concurrency, lease recovery, unknown-outcome and dead-letter behavior with real PostgreSQL/Redis/API tests.
5. Reconcile independently reviewed runtime-path evidence into config/runtime-paths.json.
6. Reconcile edition, endpoint, credential and editor evidence into config/n8n-policy.json.
7. Remediate credential ownership, domain allowlists, scopes and rotation metadata.
8. Remove hardcoded authorization remnants before importing runtime exports into canonical workflow packs.
9. Build the executable shared n8n runtime against the corrected operation policy.
10. Promote one no-effect workflow family to isolated staging.
11. Prove duplicate/replay/tenant/lease/restart/rollback and zero-external-effect evidence.
12. Bind immutable release evidence to exact protected SHAs and image/workflow digests.
13. Obtain independent approval on the unchanged release candidate.
14. Import inactive content to production only after release approval.
15. Activate a workflow separately from merge/import.
16. Enable any external-effect capability only through a separate bounded canary approval.
```

---

# 11. Current go / no-go

```text
N8N_CANONICAL_BASELINE=MERGED
N8N_MAIN_PROTECTED=YES
N8N_BRANCH_CONSOLIDATION=COMPLETE
N8N_SOURCE_REVIEW_CORRECTIONS=APPLIED
MIDDLEWARE_SOURCE_CONTRACT=MERGED
KEYCLOAK_SOURCE_CONTRACT=NOT_MERGED

RUNTIME_PATHS_CERTIFIED=NO
N8N_RUNTIME_POLICY_CERTIFIED=NO
MIDDLEWARE_RUNTIME_CONTROL_PLANE_CERTIFIED=NO
KEYCLOAK_LIVE_MACHINE_IDENTITIES_CERTIFIED=NO
CANONICAL_EXECUTABLE_WORKFLOW_E2E_CERTIFIED=NO
PRODUCTION_RELEASE_EVIDENCE_COMPLETE=NO

WORKFLOW_ACTIVATION=NO_GO
EXTERNAL_EFFECT_CAPABILITY_ENABLEMENT=NO_GO
PRODUCTION_PROMOTION=NO_GO
```

## Final reconciliation decision

```text
ORIGINAL_REVIEW_RETAINED_AS_HISTORICAL_EVIDENCE=YES
ORIGINAL_PR_STATES_CURRENT=NO
CANONICAL_SOURCE_RECONCILED=YES
PROTECTED_GOVERNANCE_ACTIVE=YES
CROSS_REPOSITORY_IMPLEMENTATION_COMPLETE=NO
PRODUCTION_READY=NO
LIVE_SERVER_CHANGED_BY_THIS_DOC_UPDATE=NO
```

The source architecture is materially stronger than it was on August 27, but the repository must continue to distinguish **merged design/source controls** from **implemented and independently tested runtime guarantees**. No document, merge, workflow import or successful n8n execution alone authorizes a production effect.
