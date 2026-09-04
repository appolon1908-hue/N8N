# Architecture

## Control plane

```mermaid
flowchart LR
    Client[Users and machine clients] --> Caddy[Caddy TLS edge]
    Caddy --> Kong[Kong API gateway]
    Kong --> Keycloak[Keycloak identity validation]
    Kong --> Middleware[Codestra middleware]
    Middleware --> Inbox[Durable signed inbox]
    Middleware --> Outbox[Transactional outbox]
    Outbox --> N8N[n8n orchestration workers]
    N8N --> Middleware
    Middleware --> Odoo[Odoo 19]
    Middleware --> VICIdial[VICIdial]
    Middleware --> Jasmin[Jasmin SMS]
    Middleware --> Postal[Postal / Klyrow email]
    Middleware --> Kyqra[Kyqra crawler]
```

## Catalog authority

`config/catalog-registry.v1.json` defines the single canonical catalog, registered supplemental catalogs, the non-additive legacy compatibility view, product coverage, and workflow-domain directory rules.

`automations/catalog.v2.json` is the canonical design catalog. Supplemental catalogs may add only workflow IDs that do not exist in the canonical catalog. `automations/catalog.json` is a compatibility view and contributes no new designs after alias resolution. Workflow packs are a separate implementation backlog; pack declarations are not added to catalog-design totals.

The generated `docs/WORKFLOW_INVENTORY.md` reports canonical, supplemental, compatibility, deduplicated, and pack metrics separately. CI rejects unregistered catalogs, unknown products, ambiguous workflow namespaces, duplicate authoritative IDs, or stale generated inventory.

## Trust boundaries

### Public edge

Caddy terminates public TLS. Kong enforces route-specific authentication, rate limits, allowlists, and machine identity mapping. Public callbacks must not terminate directly at n8n.

### Middleware boundary

Middleware is the only component allowed to translate automation intent into service-specific commands. It owns:

- tenant and actor authorization
- idempotency and optimistic concurrency
- timestamped HMAC verification and replay protection
- suppression, consent, privacy deletion, and retention rules
- per-integration pause controls and the global external-delivery kill switch
- durable inbox/outbox state, retries, dead-letter handling, and audit records

### n8n boundary

n8n coordinates approved sequences. It does not own authorization, canonical business state, credentials for direct database access, or policy decisions. Workflow exports are inactive in Git and may reference only the reviewed Middleware binding.

## Data ownership

| Domain | System of record | n8n role |
|---|---|---|
| Identity and machine clients | Keycloak / middleware identity map | consume scoped identity context |
| CRM records | Odoo through middleware | orchestrate approved commands |
| Calls and dispositions | VICIdial plus middleware audit | schedule and reconcile |
| SMS delivery | Jasmin through middleware | sequence approved sends |
| Email delivery | Postal/Klyrow through middleware | sequence approved sends |
| Crawl jobs and results | Kyqra through middleware | schedule and reconcile |
| Delivery state | middleware inbox/outbox | monitor, retry only through governed APIs |
| Workflow definitions | this repository | reviewed source of truth |
| Catalog roles and count semantics | `config/catalog-registry.v1.json` | validate and generate inventory |

## Isolation

Every command carries tenant, correlation, event, and idempotency identifiers. Batch jobs must preserve per-company isolation: one company failure cannot roll back, unlock, or replay another company without an explicit operator action.
