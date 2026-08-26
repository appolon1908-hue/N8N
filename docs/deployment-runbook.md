# Deployment runbook

## Phase 0 — source review

1. Review the final pull-request diff.
2. Confirm exact-head CI and unchanged head SHA.
3. Confirm all workflows are inactive and all external-effect capabilities are false.
4. Obtain independent approval.
5. Merge through protected controls.

## Phase 1 — runtime verification

1. Run `ops/runtime_path_audit.py` read-only on the target server.
2. Sanitize and hash the output.
3. Update `config/runtime-paths.json` in a separate PR.
4. Verify Compose paths, n8n data path, reverse-proxy path, secret locations, networks, ownership, and backup locations.
5. Do not deploy in this phase.

## Phase 2 — immutable release preparation

1. Build from the exact protected merged SHA.
2. Publish by immutable digest, never by a mutable tag alone.
3. Generate and verify SBOM, provenance, signature, vulnerability evidence, and release tuple.
4. Create `deploy/manifests/release.json` outside the feature branch and run the preflight workflow.

## Phase 3 — isolated staging

1. Restore a sanitized backup into isolated PostgreSQL and n8n storage.
2. Keep every capability in `config/capabilities.json` false.
3. Start staging only after runtime-path and secret-provider verification.
4. Validate health, readiness, version identity, restart behavior, migrations, rollback, HMAC replay rejection, idempotency, tenant isolation, dead-letter replay, Odoo/n8n duplicate delivery, and Kong/Caddy controls.
5. Confirm zero calls, messages, emails, lead publications, payments, callbacks, or provider writes.

## Phase 4 — production canary

A later, separately approved change may add a production deployment implementation. The first production deployment must still keep external effects disabled, validate the exact runtime digest, and exercise rollback before any narrowly scoped canary capability is enabled.

## Rollback invariant

Rollback selects a previously approved immutable image and compatible schema state. It never rebuilds from source during an incident and never assumes a database downgrade is safe without tested rollback evidence.
