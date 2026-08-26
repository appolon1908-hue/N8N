# n8n workflows

All committed exports must be inactive. Templates are examples of structure, not approved production automations.

## Rules

- Outbound HTTP nodes may reference only `MIDDLEWARE_BASE_URL`.
- Do not embed credentials, credential IDs tied to production, direct database nodes, provider endpoints, or public service URLs.
- Public webhooks are prohibited. Inbound provider callbacks terminate at Kong/middleware, where signatures and replay controls are enforced before n8n receives an internal event.
- Each workflow needs a deterministic idempotency key, bounded retry path, dead-letter path, and capability declaration before implementation review.
- Export workflow JSON without execution data, pin data, credential material, or active state.

Run:

```bash
python3 scripts/validate_workflows.py workflows
```
