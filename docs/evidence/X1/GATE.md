# X1 Gate: Roadmap Packs

Status: `GO_SOURCE_ONLY`

Branch: `phase-x1/roadmap-packs`

## Measured Values

- `ROADMAP_PACKS: 4 of 4`
- `CANONICAL_WORKFLOWS_DESIGNED: 0 of 5`
- `ENDPOINT_BINDING: UNVERIFIED`
- `CREDENTIAL_BINDING: UNVERIFIED`
- `EDITOR_BINDING: UNVERIFIED`
- `POLICY_BINDING: PENDING_RUNTIME_VALIDATION`
- `N8N_WORKFLOW_ACTIVATION: false`
- `KILL_SWITCHES_ALL_FALSE: YES`
- `AI_AUTHORITY_ASSERTED_NONE: YES`
- `PRODUCTION_CHANGED: false`
- `WORKFLOWS_DECLARED: 81`
- `WORKFLOWS_BUILT: 0`
- `EXPECTED_MISSING: 81`

## Completed

- Added `automations/packs/codestra-marketing.v2.json`.
- Added `automations/packs/codestra-ai.v2.json`.
- Added `automations/packs/codestra-communication.v2.json`.
- Added `automations/packs/codestra-social.v2.json`.
- Registered roadmap products in `config/products.json`.
- Registered roadmap packs in `config/workflow-packs.v2.json`.
- Registered 16 roadmap workflow declarations in `automations/catalog.v2.json`.
- Added `scripts/validate_roadmap_packs.py` and wired it into `make validate`.
- Added `config/n8n-runtime-bindings.env` and `scripts/validate_n8n_runtime_bindings.py` to make the server-facing runtime binding state explicit.
- Resolved roadmap social naming to `Codestra Social` in `docs/ROADMAP-SYSTEM-REGISTRY.md`.
- Regenerated `docs/WORKFLOW_INVENTORY.md`.

## Guardrails

- All roadmap packs are `active: false`.
- Marketing prohibits direct advertising providers including `graph.facebook.com` and `googleads.googleapis.com`.
- AI is `advisory-only` and cannot authorize spend, publishing or customer delivery.
- Communication declares direct Klyrow/Telnexa access prohibited; consent remains outside n8n.
- Codestra Social publish workflows require approval and keep provider tokens out of n8n.
- Runtime binding status is locked to `UNVERIFIED` / `PENDING_RUNTIME_VALIDATION` and workflow activation is locked to `false`.

## Stop Condition

This branch is source-only. It does not create executable workflows, enable runtime bindings, activate workflows, change credentials, enable delivery, enable Odoo writes or make production changes.
