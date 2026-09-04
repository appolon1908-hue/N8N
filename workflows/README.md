# n8n workflows

All committed workflow exports must be inactive. Templates demonstrate structure only, contain no credential references, and are not approved production automations.

## Catalog and directory authority

`config/catalog-registry.v1.json` is the authority for catalog roles, product coverage, workflow-domain prefixes, and workflow directories. The registry resolves each workflow ID to exactly one domain directory by longest matching prefix.

The catalog metrics have different meanings and must not be added together:

- `automations/catalog.v2.json` is the canonical design catalog.
- Registered supplemental catalogs add only workflow IDs that are absent from the canonical catalog.
- `automations/catalog.json` is a compatibility view and contributes zero new designs after alias resolution.
- `automations/packs/*.json` is the implementation backlog. Pack declarations are not additional catalog designs.

Run `python3 scripts/validate_catalog_reconciliation.py` to verify those rules and `python3 scripts/generate_workflow_inventory.py` after an approved catalog or pack change.

## Endpoint binding

The n8n edition and the live middleware endpoint strategy are still unverified. For that reason, templates use the reserved non-routable host `https://middleware.invalid` and their outbound HTTP nodes are disabled.

Executable workflows are prohibited until `config/n8n-policy.json` records reviewed endpoint, credential-binding, and editor-access strategies. The later implementation must use one of these approved endpoint patterns:

- a verified n8n custom variable on an edition that supports it;
- a reviewed custom node that owns the middleware endpoint; or
- a fixed, verified private DNS name enforced by egress policy.

Environment-variable access from workflow nodes stays blocked. Do not use `$env` to work around endpoint governance. Credential references are permitted only in future executable exports when their exact n8n credential types and names are approved by the verified policy; templates declare `credential_binding=NO_CREDENTIALS`.

## Rules

- Outbound HTTP may target only the Codestra middleware endpoint selected by the reviewed policy.
- Do not embed secret values or credential exports. Future executable exports may reference only exact credential types and names approved by policy; direct database nodes, provider endpoints, public service URLs, and IP literals remain prohibited.
- Public webhooks are prohibited. Provider callbacks terminate at Kong/middleware, where signatures and replay controls are enforced before n8n receives an internal event.
- Each workflow needs a deterministic idempotency key, bounded retry path, dead-letter path, and capability declaration before implementation review.
- Export workflow JSON without execution data, pin data, credential material, or active state.
- Code, Execute Command, local file, SSH, FTP, and Git nodes remain excluded until a separate security design is approved. If Code is ever enabled, external task-runner isolation is mandatory.

Run:

```bash
python3 scripts/validate_workflows.py workflows
```
