# Server vs GitHub drift

Assessment date: 2026-08-28  
Production readiness: **NO**

## Compared authorities

| Authority | Revision | Status at assessment |
|---|---|---|
| Live production n8n | database and image capture | 130 workflows; 1 active; n8n 2.30.8 |
| Live staging n8n | database and image capture | 327 workflows; 11 active; n8n 2.30.8 |
| `Codestra-SRL/codestra-n8n-workflows` | `main@5b7e7ba5e0e719194fb6a3fca1c1b05e80de7bee` | previous source authority |
| `appolon1908-hue/N8N` | `main@e89ed696635edff615e69abb7c1fac94c590aeac` | new repository; main contained only README |
| New governance-chain candidate | `6de4eca973454007adfb75ff2146180adeeaf57e` | strongest consolidated baseline, not on main |
| Sanitized server capture | `import/server-n8n-20260828@93a436a` | evidence only; deliberately unmerged |

## Executive finding

The live server, old source repository, and new repository do not describe one
reproducible system. The old repository is the closest workflow source but is
incomplete. The new repository contains the stronger governance, policy,
deployment template, and test model, but that model is distributed across a
large branch stack and is absent from `main`. Neither repository alone can
rebuild the live server.

`appolon1908-hue/N8N` should become canonical only after the governance-chain
candidate is reviewed and merged into protected `main`, followed by selective
workflow-pack reconciliation. The raw server capture must not be merged as the
canonical workflow catalog.

## Workflow identity drift

| Comparison | Shared IDs | Server only | GitHub only |
|---|---:|---:|---:|
| Production vs old repository main | 75 | 55 | 12 |
| Staging vs old repository main | 87 | 240 | 0 |
| Production vs all new-repository branch tips | 9 | 121 | 14 |
| Staging vs all new-repository branch tips | 12 | 315 | 11 |
| Production vs consolidated governance candidate | 0 | 130 | 0 |
| Staging vs consolidated governance candidate | 0 | 327 | 0 |

The consolidated governance candidate intentionally contains templates and
catalogs rather than server workflow exports, so its zero workflow-ID overlap
is an implementation gap, not evidence that the governance work is invalid.

## Structural drift for shared workflow IDs

Structural comparison normalizes each workflow to `nodes`, `connections`, and
`settings`, excluding volatile database timestamps and version counters.

| Comparison | Shared | Structurally identical | Structurally different |
|---|---:|---:|---:|
| Production vs old repository main | 75 | 74 | 1 |
| Staging vs old repository main | 87 | 9 | 78 |
| Production vs all new branch tips | 9 | 9 | 0 |
| Staging vs all new branch tips | 12 | 0 | 12 |

The one production workflow that differs from old `main` is
`CDST_EmailSend_v1`. It requires semantic review before either copy is accepted.
The 78 staging differences must not be bulk-promoted.

Machine-readable workflow-ID and structural results are under `docs/drift/`.

## Security drift

1. Live production and staging use n8n 2.30.8 at digest
   `sha256:11524034450080bd0032754892b23ff20be43d72cf320ce75640f7c5475fdca8`.
   The local image scan reported 4 critical and 52 high findings with fixes.
2. The old repository pins the mutable tag `n8nio/n8n:2.30.8` in its gate
   Compose file. The new governance baseline correctly requires an immutable
   `N8N_IMAGE` digest but does not yet bind an approved release.
3. Production lacks the new baseline's read-only root filesystem, dropped
   capabilities, `no-new-privileges`, PID limit, dangerous-node exclusion, and
   external-task-runner policy.
4. Live staging has 150 hard-coded Authorization fields across 75 workflows.
   Git capture redacted every value. Treat the shared value as compromised,
   rotate it, and replace headers with managed credentials before promotion.
5. The live catalog uses 265 production Code nodes, while the governance policy
   disables Code nodes unless external task runners and explicit approval are
   present. This is a material policy incompatibility.

## Deployment and topology drift

- Production runs a single main n8n process against shared PostgreSQL and no
  production Redis queue.
- Staging runs queue mode with main, webhook, two workers, PostgreSQL, and Redis.
- The new governance deployment template models main plus one worker and omits
  the dedicated webhook processor currently deployed in staging.
- Live Compose directories are not Git worktrees. Production also depends on
  multiple overlays and an untracked internal proxy configuration.
- The production-platform deployment records do not yet bind one N8N source
  SHA, workflow-pack hash set, migration state, staging certification, and
  rollback reference.

## Repository drift

- Old repository: 7 remote branches; 87 workflow IDs on `main`.
- New repository at assessment: 72 remote refs, 16 unique branch tips, and only
  a README on `main`.
- Many new branch names point to shared stacked commits. This makes review,
  ownership, and protected-main enforcement unnecessarily difficult.
- The governance candidate includes a no-bypass ruleset contract, CODEOWNERS,
  CI, release evidence, immutable-image policy, queue-mode template, security
  policy, and cross-product workflow-pack catalogs. Those are the correct base
  to consolidate, subject to CI and review.

## Reconciliation decision

1. Protect `main` before canonicalization; no administrator bypass.
2. Review and promote the consolidated governance candidate to `main` through a
   pull request and required status checks.
3. Preserve the server capture branch as evidence; do not merge it wholesale.
4. Import workflows by product pack into the required directory taxonomy.
5. Prefer reviewed old-repository workflows when structurally identical to the
   server. Treat server-only workflows as unapproved candidates until ownership,
   contract, credential, and activation reviews pass.
6. Resolve `CDST_EmailSend_v1` manually.
7. Do not activate inactive workflows as part of reconciliation.
8. Rotate the hard-coded staging authorization value before any staging or
   production certification that exercises those workflows.

## P0 blockers

- vulnerable n8n image;
- hard-coded staging Authorization values;
- canonical governance not on protected `main`;
- live/Git workflow drift unresolved;
- patched-image migration and rollback not yet certified;
- production containment below approved baseline.

The disk and recovery blockers identified at the start of the operation are now
mitigated: root usage was reduced to 83%, 75/85/90 alerts are loaded, and the
current encrypted recovery point passed an isolated database, volume,
encryption-key, workflow-export, credential-decryption, health, and readiness
rehearsal.
