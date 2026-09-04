# N8N Automation Platform

Canonical governed source for Codestra n8n workflow packs, consumed contracts, deployment policy, operational evidence, and release controls.

## Current state

- **Canonical repository:** `appolon1908-hue/N8N`
- **Protected branch:** `main`
- **Live server:** unchanged
- **Runtime paths:** `VERIFIED` for production and staging
- **n8n edition/endpoint/credential/editor policy:** `UNVERIFIED`
- **Catalog authority:** reconciled through `config/catalog-registry.v1.json`
- **Operator theme/SSO adoption:** `SOURCE_ONLY_NO_GO`
- **External delivery:** disabled
- **Production deployment:** blocked
- **Workflow activation:** disabled by policy and CI

This repository contains no secret values and no live-server write or SSH deployment action. Product automations remain workflow packs in this repository; separate product-specific n8n repositories are prohibited.

## Architecture boundary

n8n may call the Codestra middleware API only. It must not connect directly to Odoo, VICIdial, Jasmin, Postal/Klyrow, Kyqra, PostgreSQL, Redis, Keycloak administration, Kong administration, or provider APIs. The middleware owns authorization, tenant isolation, idempotency, replay protection, suppression checks, kill switches, auditing, and delivery state.

```text
Caddy -> Kong -> Keycloak identity -> Codestra middleware -> governed service adapters
                                      ^
                                      |
                                  n8n workers
```

## Catalog authority and counting

`automations/catalog.v2.json` is the canonical design catalog. Registered supplemental catalogs contribute only unique workflow IDs. `automations/catalog.json` is a compatibility view and contributes zero new designs after alias resolution. Workflow-pack declarations are a separate implementation backlog and must not be added to catalog-design totals.

The registry, validation rules, and generated current counts are documented in:

- `config/catalog-registry.v1.json`
- `docs/CATALOG_RECONCILIATION.md`
- `docs/WORKFLOW_INVENTORY.md`

## Authority and governance documents

- `REPOSITORY_PROFILE.md` — repository purpose, ownership, integration boundary, and current source posture.
- `docs/COMMUNICATIONS_PLATFORM_AUTHORITY.md` — communications workflow ownership, Middleware-only command path, and activation gates.
- `docs/AUTOMATED_REPOSITORY_AND_RELEASE_GATES.md` — exact-head CI, protected-main review, immutable candidate, staging, canary, and effect-separation rules.
- `orbit/adoption-manifest.json` — source-only contract for a protected n8n operator theme and SSO integration; runtime remains unverified and unauthorized.

## Repository map

| Path | Purpose |
|---|---|
| `automations/` | Canonical, compatibility, supplemental, product, and service automation catalogs |
| `config/catalog-registry.v1.json` | Catalog roles, aliases, product coverage, workflow domains, and count semantics |
| `config/products.json` | Complete registered product inventory used by all catalogs |
| `config/` | Capabilities, services, products, n8n security/endpoint policy, and runtime-path state |
| `contracts/` | Consumed integration schemas; canonical Middleware source lives elsewhere |
| `deploy/` | Non-applying Compose and release-preflight templates |
| `docs/` | Architecture, authority, catalog reconciliation, generated inventory, security review, branching, and runbooks |
| `observability/` | Monitoring and alerting definitions for n8n dependencies |
| `operations/` | Read-only inventory, recovery, release, and audit tooling |
| `orbit/` | Source-only protected operator theme/SSO adoption contract |
| `scripts/` | Repository, catalog, workflow, secret, runtime, and release validators |
| `tests/` | Policy, catalog, contract, deployment, and workflow validation |
| `workflows/` | Inactive, governed workflow packs and safe templates |

## Local validation

```bash
make validate
```

The manual `deployment-preflight` workflow performs validation only. Runtime paths are checked for its selected production or staging target. The preflight remains blocked until the n8n endpoint/security/credential/editor policy is independently verified and a complete immutable release manifest exists. It never connects to or changes the live server.

The SHA-pinned `codestra-deploy-readiness` workflow adds immutable source-candidate publication and protected read-only staging/canary entry points. Pull-request execution remains validation-only; runtime operations require the reviewed protected-branch, fixed-confirmation, protected-environment, exact-artifact, and no-external-effect gates.

After an approved deployment, read the five non-secret umbrella controls from the effective container configuration with:

```bash
python3 scripts/readback_umbrella_controls.py \
  <n8n-container> \
  <approved-repository@sha256-configured-image> \
  <approved-sha256-runtime-image-id>
```

The command emits sanitized JSON containing only the named controls and the configured/runtime image and Compose-service identity. It exits non-zero when a control is missing, duplicated, malformed, or not exactly `false`, or when the container is not the reviewed digest-pinned n8n service starting through the read-only, checksum-bound umbrella guard.

While the umbrella controls are closed, the staging scaffold also excludes the HTTP Request, provider-delivery, database/cache, Code, command, file-transfer, and shell node classes at n8n startup. The flags are therefore not passive metadata: a workflow cannot reach Middleware or a provider through those node classes. Enabling any effect requires a separate reviewed policy/Compose change, staging certification, and runtime evidence; changing a flag alone makes the guard refuse startup.

Templates use a disabled request to `https://middleware.invalid`. Executable workflow exports are blocked until the deployed n8n edition, a safe middleware endpoint-binding strategy, an approved credential-binding profile, and a protected editor-access strategy are verified. Code and other high-risk local-execution nodes are excluded from the deployment template.

## Required merge gates

1. Exact-head CI passes on the unchanged PR SHA.
2. Catalog roles, aliases, product coverage, workflow-domain routing, and generated inventory reconcile on the unchanged PR SHA.
3. Runtime-path state may be `VERIFIED` only with target-specific evidence and independent review.
4. Every n8n workflow remains inactive in Git; only disabled templates are allowed while endpoint binding is unverified.
5. All external-effect capability flags remain false.
6. No direct service credentials, direct service endpoints, public webhooks, IP literals, Code nodes, or local-execution nodes appear in workflow exports.
7. The n8n edition, endpoint binding, credential binding, editor access, and runtime paths remain unverified unless separate evidence-backed reviews approve them.
8. An independent reviewer approves the final unchanged SHA.
9. Merge occurs through protected branch controls without admin bypass.
