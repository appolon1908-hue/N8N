# Security and deployment-scaffold review

## Decision

**SOURCE_SCAFFOLD: ACCEPTABLE FOR REVIEW**  
**LIVE_DEPLOYMENT: BLOCKED**

The repository was empty before this branch. No existing CI, ruleset, runtime manifest, immutable image reference, or deployment evidence existed. This branch adds validation-only controls and intentionally omits all live-server mutation steps.

## Findings

| ID | Severity | Finding | Treatment in this branch |
|---|---|---|---|
| SR-001 | Blocker | Live n8n Compose, data, environment, and proxy paths are not verified. | `config/runtime-paths.json` remains `UNVERIFIED`; preflight refuses approval. |
| SR-002 | Blocker | No immutable n8n image digest, SBOM, provenance, or signature evidence exists. | Release validator requires all before approval. |
| SR-003 | High | Repository had no branch rules or required checks. | CODEOWNERS, exact-head CI, PR template, and a protection checklist are provided; repository administration must enable rules. |
| SR-004 | High | Direct n8n access to service databases/providers could bypass policy. | Workflow validator permits outbound HTTP only through `MIDDLEWARE_BASE_URL`. |
| SR-005 | High | Static webhook authentication alone does not prevent replay. | Middleware contract requires timestamp, event id, canonical HMAC, replay window, and durable deduplication. |
| SR-006 | High | A queued event could outlive consent or a pause decision. | Dispatch contract requires suppression and pause re-check immediately before external submission. |
| SR-007 | Medium | A broad automation repository can become an unreviewable monolith. | Umbrella branch establishes the baseline; implementation work is split into product/service child branches. |
| SR-008 | Medium | Workflow exports can accidentally include credentials or active state. | Secret scan and workflow validation are required in CI. |

## Deployment exclusions

This branch contains no SSH, SCP, rsync, remote Docker context, `docker compose up`, `systemctl`, Kubernetes apply, database migration, workflow import, or API activation step. The manual deployment workflow is a preflight only.

## Required evidence before a staging deployment implementation may be added

1. Read-only runtime audit with server identity, Compose labels, mount paths, networks, and candidate configuration paths.
2. Sanitized audit artifact SHA-256 committed or attached to the review.
3. `config/runtime-paths.json` updated to `VERIFIED` by one operator and independently reviewed by another.
4. Exact n8n image digest plus vulnerability evidence, SBOM, provenance, and signature verification.
5. Backup and isolated restore evidence for PostgreSQL and n8n state.
6. Staging secrets provisioned outside Git.
7. All live-write, delivery, messaging, dialing, publishing, crawler-writeback, and payment flags false.
8. Kong/Caddy route, identity mapping, rate-limit, allowlist, HMAC, duplicate-delivery, and replay tests.
9. Tested rollback with measured recovery time.
10. Explicit protected-environment approval for the exact release tuple.
