# N4 n8n runtime-policy audit

Captured: `2026-08-30T18:02Z`
Host: `middleware` (`65.109.65.169`, `10.40.0.1`)
Auditor: `codestra-admin` through the configured `codestra-app` identity
Production-service mutation performed: `false`
Audit-host mutation performed: `true` (one temporary container, removed)

## Decision

`config/n8n-policy.json` must remain `UNVERIFIED`. Endpoint, credential,
editor-session, and live node-exclusion controls do not yet meet the repository's
verified-policy contract. No workflow export may become executable on the basis
of this audit.

## Edition and versions

- Production: n8n `2.30.8`, unlicensed/community state, zero entitlements.
- Staging: n8n `2.36.8`, unlicensed/community state, zero entitlements.

## Endpoint and egress

The estate contract declares `https://api.codestra.co` as the canonical gateway
host, but no reviewed network egress control proves that n8n can reach only that
Middleware boundary. Staging also exposes internal HTTP candidates such as
`http://middleware-staging:8095`; these are not an approved HTTPS base under the
repository policy. Therefore none of the allowed endpoint strategies can yet be
selected truthfully.

Required remediation:

1. Choose one HTTPS endpoint strategy and record its exact production/staging
   base URLs.
2. Enforce and test an n8n egress allowlist limited to the approved Middleware
   and essential infrastructure destinations.
3. Prove denial for Odoo, provider, arbitrary Internet, PostgreSQL, Redis, and
   other direct-service targets from every n8n execution role.

## Credential binding

The reviewed metadata inventory contains four production credentials. All are
owned by a personal project. The Middleware header/signing records lack a
resource-domain boundary, scope record, and rotation date. The two OAuth records
have partial scope metadata but still lack resource-domain and rotation evidence.
Staging has nine staging-only records with the same metadata gaps, plus disabled
provider placeholders. Existing staging exports also include hardcoded
Authorization remnants.

Required remediation:

1. Create a named service-owned n8n project with primary and backup owners.
2. Bind a least-privilege Middleware credential whose audience, scopes, allowed
   base URL, issue date, rotation due date, revocation procedure, and owner are
   recorded outside secret material.
3. Remove hardcoded Authorization values from every candidate export.
4. Re-audit metadata only; never place decrypted values in Git or evidence.

## Editor and session controls

- Production and staging n8n ports have no host binding.
- Anonymous HTTPS requests to both editor domains returned HTTP 403 through the
  edge with HSTS, `X-Content-Type-Options: nosniff`, and
  `X-Frame-Options: SAMEORIGIN`.
- Both instances report `N8N_SECURE_COOKIE=true` and HTTPS editor base URLs.
- Exact session lifetime, inactivity timeout, native-auth owner policy, gateway
  identity mapping, and revocation behavior were not evidenced.

The editor is not directly published, but the full
`verified-gateway-oidc-and-native-auth` strategy cannot be approved until those
session and identity controls are tested and independently reviewed.

## Execution security and retention

Observed in both instances:

- environment access in nodes blocked;
- public API disabled;
- community and unverified packages disabled;
- secure cookies enabled;
- execution pruning enabled (production 336 hours, staging 168 hours).

Observed conflict:

- `NODES_EXCLUDE` is absent in production and staging;
- staging certification records internal JavaScript runners as active;
- external task runners are not deployed.

This conflicts with the source claim `code_node_enabled=false`. A reviewed
runtime change must exclude every dangerous non-Code node in all execution
roles. Code must also remain excluded unless matching hardened external task
runners are deployed and certified; task runners do not isolate Execute Command,
SSH, FTP, Git, or local-file nodes. The safer current decision is to exclude the
entire dangerous-node set. It requires an authorized Compose/env change, exact
render review, controlled restart, readiness/queue verification, and rollback
evidence.

## Safety boundary

The audit read only an explicit allowlist of non-secret configuration keys,
Docker labels/bindings, existing source evidence, and anonymous response
metadata. It did not inspect credential values, passwords, tokens, customer
payloads, workflow data, database rows, or logs. One temporary no-network,
read-only, capability-free container mounted the root-only production env file
and emitted none of its contents because no allowlisted keys were present; it
was removed immediately. No service was restarted and no production file was
changed.
