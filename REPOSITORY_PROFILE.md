# Repository Profile — `appolon1908-hue/N8N`

## Identity

- **Category:** governed automation and orchestration source
- **Visibility:** public source repository; no secrets or customer payloads belong in Git
- **Default and protected branch:** `main`
- **Catalog authority:** `config/catalog-registry.v1.json`
- **Canonical design catalog:** `automations/catalog.v2.json`
- **Runtime posture:** source-only; production deployment and workflow activation remain blocked until separately certified
- **External effects:** disabled by repository policy and capability controls

## Purpose

This repository is the canonical governed source for Codestra n8n workflow designs, workflow-pack implementation backlog, consumed integration contracts, source validation, deployment-readiness controls, observability definitions, operational evidence, and recovery procedures.

It coordinates approved sequences. It does not replace the business systems, policy engines, identity provider, gateway, or deployment infrastructure that authorize and execute those sequences.

## Owns

- workflow definitions, inactive templates, workflow-family organization, and implementation status;
- catalog roles, compatibility aliases, product coverage, workflow-domain routing, and deduplicated design counts;
- orchestration timing, branching, bounded retries, reconciliation, dead-letter handling, and operator escalation;
- consumed event and command contract fixtures;
- workflow validation, source-only safety policy, release evidence, and recovery documentation;
- a repository-scoped, read-only deploy-key bootstrap whose private key must be generated and retained on the approved target host.

## Does not own

- authoritative business, ledger, CRM, identity, provider, or delivery state;
- direct provider execution or credentials;
- direct writes to Odoo, VICIdial, Jasmin/Telnexa, Klyrow/Postal, Kyqra, databases, Keycloak administration, or Kong administration;
- public callback termination;
- runtime secrets, customer payloads, execution histories, recordings, database dumps, or credential exports;
- production activation simply because source was merged.

## Required integration path

```text
approved event or schedule
        -> n8n orchestration
        -> reviewed Codestra Middleware API binding only
        -> Middleware authorization, idempotency, consent, suppression and kill switches
        -> governed service adapter
        -> system of record or provider
```

Public callbacks terminate at the approved edge and Middleware boundary. n8n receives normalized, tenant-bound work through governed internal contracts and returns results through Middleware.

## Repository authorities

| Area | Authoritative source |
|---|---|
| Catalog roles and counting | `config/catalog-registry.v1.json` |
| Product inventory | `config/products.json` |
| Canonical automation designs | `automations/catalog.v2.json` |
| Pack implementation backlog | `automations/packs/` |
| Workflow exports and templates | `workflows/` |
| Runtime and endpoint policy | `config/n8n-policy.json` |
| Source validation | `Makefile`, `scripts/`, and `.github/workflows/` |
| Deployment-readiness entry point | `.github/workflows/codestra-deploy-readiness.yml` |
| Read-only Git access bootstrap | `config/ssh-deploy-key-bootstrap.v1.json`, `ops/bootstrap_github_deploy_key.sh`, and `docs/ssh-deploy-key-bootstrap.md` |
| Architecture and operating boundaries | `docs/architecture.md` and `docs/COMMUNICATIONS_PLATFORM_AUTHORITY.md` |

## Change and release policy

1. Use short-lived branches and pull requests into protected `main`.
2. Validate the exact unchanged PR head and keep it current with `main`.
3. Satisfy the active repository ruleset, including required status checks, review, and conversation resolution.
4. Keep committed workflow exports inactive and free of secrets, execution data, direct provider endpoints, and prohibited nodes.
5. Treat source merge, immutable candidate publication, staging deployment, production read-only canary, and workflow activation as separate authorities.
6. Never interpret a merged source PR as permission to enable calls, email, SMS, social publishing, trading, wallet movement, provider delivery, or another external effect.

## Current source state

The repository has a reconciled catalog authority, an immutable deploy-readiness path, and source-ready read-only deploy-key bootstrap. The deploy-key server installation remains unverified, and active workflows remain zero. Endpoint, credential, editor-access, environment, and runtime evidence must still satisfy their separate fail-closed gates before any executable workflow or production effect is authorized.
