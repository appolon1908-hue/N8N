# Marketing Workflow Foundation

n8n orchestrates approved cross-service effects through Middleware only; it is not a system of record.

## Canonical workflow identities

The workflow key format is `<product>.<domain>.<action>.v<major>`.

- `codestra.crm.lead-intake.v1` is the existing canonical key for lead intake.
- Nurture, approved social publishing, conversion feedback, and campaign analysis must be registered in the canonical workflow catalog before executable workflow exports are created or imported.
- No ad-hoc aliases such as `lead-intake-v1` are permitted because workflow identity is enforced by the platform control plane.

## Initial workflow designs
1. `codestra.crm.lead-intake.v1`: verified inbound lead -> governed Middleware command -> Marketing attribution -> Odoo upsert.
2. Nurture: Odoo-qualified lead -> governed Middleware command -> Communication request -> delivery/status feedback; canonical key registration required first.
3. Approved social publishing: approved Social post -> governed Middleware command -> runtime adapter -> status reconciliation; canonical key registration required first.
4. Conversion feedback: Odoo opportunity outcome -> governed Middleware command -> Marketing attribution/revenue feedback; canonical key registration required first.
5. Campaign analysis: Marketing metrics -> governed Middleware command -> Codestra AI analysis -> recommendation record only; canonical key registration required first.

## Safety
No workflow may activate paid advertising, increase budgets, publish unapproved social content, bypass consent, call providers directly, call downstream service APIs directly, or own provider credentials. Each effect-producing mutation uses the private Middleware API with correlation/idempotency identifiers. External write capability flags remain false until separately approved and promoted.
