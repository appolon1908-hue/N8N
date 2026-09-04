# Catalog Reconciliation

## Decision

`config/catalog-registry.v1.json` is the source of truth for catalog roles, product coverage, compatibility aliases, workflow-domain routing, and count semantics.

The repository now uses three independent metrics:

1. **Canonical designs** — workflow IDs in `automations/catalog.v2.json`.
2. **Deduplicated intended designs** — canonical IDs plus unique IDs from registered supplemental catalogs.
3. **Pack implementation backlog** — workflow files declared by `automations/packs/*.json`.

These metrics are not additive. A workflow ID is counted at most once in the deduplicated design inventory, and compatibility-view rows never increase that count.

## Catalog roles

| Catalog | Role | Counting behavior |
|---|---|---|
| `automations/catalog.v2.json` | `CANONICAL` | Authoritative design IDs |
| `automations/catalog.json` | `COMPATIBILITY_VIEW` | Adds zero designs; every row resolves to a canonical ID |
| `automations/beyvra.catalog.v2.json` | `SUPPLEMENTAL` | Adds unique Beyvra operational designs |
| `automations/trading.catalog.v1.json` | `SUPPLEMENTAL` | Adds unique nonfinancial trading and real-wallet designs |
| `automations/marketing.catalog.v1.json` | `SUPPLEMENTAL` | Registers the existing governed marketing lead-intake design |

## Legacy alias decisions

Two legacy compatibility IDs did not have exact canonical-name matches. They now resolve explicitly:

| Legacy ID | Canonical ID | Reason |
|---|---|---|
| `kyqra.crawler.job-result.v1` | `kyqra.crawler.result-received.v1` | Same result-ingestion responsibility under the canonical v2 naming convention |
| `codestra.privacy.suppression-delete.v1` | `codestra.privacy.data-deletion.v1` | Legacy combined wording resolves to the approval-gated canonical deletion operation |

The aliases preserve discovery of the legacy names without treating them as new designs or changing any runtime route.

## Product and domain coverage

`config/products.json` contains every product used by the registered catalogs. Non-product workflow groupings such as Contact Center, Social, Marketing, Operations, Privacy, Trading, and Real Wallet are represented as workflow domains in the catalog registry. This avoids inventing duplicate products merely to mirror folder names.

Every catalog ID and every pack ID must resolve to exactly one registered workflow directory by longest matching namespace prefix. Existing workflow directories must also be registered, so adding an untracked folder or catalog causes CI to fail.

## Enforcement

The following commands are part of `make validate`:

```bash
python3 scripts/validate_catalog_reconciliation.py
python3 scripts/validate_workflow_completeness.py
```

They fail closed when:

- a catalog file is unregistered or missing;
- more than one canonical catalog exists;
- a compatibility row cannot resolve to a canonical workflow ID;
- a supplemental catalog duplicates a canonical ID;
- a catalog references an unknown product;
- a product has no catalog scope;
- a workflow ID has no unambiguous domain/directory mapping;
- a workflow directory is unregistered;
- catalog or pack workflow IDs are duplicated;
- a catalog workflow becomes active or ceases to be `DESIGN_ONLY`; or
- `docs/WORKFLOW_INVENTORY.md` is stale.

## Runtime safety

This reconciliation changes source metadata, validation, and inactive design inventory only. It does not activate workflows, bind credentials, change provider routes, deploy n8n, enable external delivery, or authorize production runtime execution.
