# n8n Connected Systems Registry

The n8n boundary is source-enforced through:

- `config/n8n-connected-systems.v1.json`
- `systems/<system>/integrations/n8n/manifest.v1.json`
- `scripts/validate_connected_system_manifests.py`

The runtime rule is:

```text
n8n -> Middleware -> system
```

Forbidden paths:

```text
n8n -> system
system -> n8n
n8n -> Odoo
n8n -> database / Redis / SMTP / SMS / telephony / social / crawler provider
```

## Tiers

Tier 1 is n8n. It sequences work, waits, retries, and routes human review. It is
not a source of truth and does not hold provider credentials.

Tier 2 is Codestra Middleware. It owns tenant mapping, authorization,
idempotency, durable commands, replay protection, delivery policy, adapters,
DLQ, and reconciliation.

Tier 3 contains the domain systems: Odoo, VICIdial, Telnexa, Klyrow, Kyqra,
Postiz, MoneyBee, Beyvra, LARIM-A, Freight, Breero, Provisioning,
Booked4Seasons, and Trading.

## Manifest Rule

Every Tier 3 system has a manifest. The `n8n` block, `integration_boundary`, and
`invariants` block must match the registry baseline exactly. Exceptions require
a separate architecture decision; editing one manifest is not enough.

Beyvra and Trading are intentionally separate manifests. Their event and command
arrays must remain non-overlapping until a reviewed architecture decision says
otherwise.

Kyqra targets `appolon1908-hue/kyqra-crawler` as the future canonical repository
while preserving `appolon1908-hue/scrapper` lineage until cutover is complete.

## Validation

Run:

```bash
python scripts/validate_connected_system_manifests.py
```

The validator checks:

- exactly 14 Tier 3 domain systems are registered, with no duplicates;
- every registry system has a manifest;
- manifest keys match the standard shape, with only approved optional metadata;
- repository references use `owner/repo` slugs;
- fixed n8n and invariant blocks match byte-for-byte as parsed JSON objects;
- every capability defaults to false;
- event and command names match the owning system prefix and are globally unique;
- workflow names are owned by exactly one manifest and resolve to committed
  workflow export names under `workflows/`;
- critical, high, medium-high, and TBD risk manifests require human review;
- TBD risk manifests declare `risk_review_status=REQUIRES_ENUMERATION` and a
  review reason;
- financial-data manifests declare positive retention;
- workflow JSON is inactive in Git;
- workflow JSON does not contain workflow-level credentials, node-level
  credentials, direct Tier 3 HTTP hosts, direct Odoo hosts, non-HTTPS HTTP
  targets, or database/Redis/provider node types.

The N8N trunk is `main`. Broadcast pushing one commit to the Stage 4 branch
family is now marked disallowed in the registry; branch reconciliation should
precede additional Stage 4 work.
