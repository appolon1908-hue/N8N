# Platform Control Plane v1

This repository owns orchestration only. The reviewed integration path is:

`n8n -> Kong -> Middleware -> Temporal -> Odoo/provider`

n8n does not own provider credentials, direct database access, or direct Odoo/provider writes. The source contract is `contracts/platform-control-plane.v1.json`.

## N8N command boundary

The prepared command endpoint is:

- `POST https://api.codestra.co/v1/integrations/n8n/commands`
- `GET https://api.codestra.co/v1/integrations/n8n/operations/{command_id}`

The service identity is `n8n-automation`, audience `middleware-api`. Submit requires `middleware.request.forward`; status reads require `middleware.status.read`. Requests carry `X-Tenant-ID`, `X-Request-ID`, `X-Correlation-ID`, and `Idempotency-Key` in addition to the bearer token.

Middleware independently validates the Keycloak token, tenant claim, command policy, capability, idempotency identity, and durable command state. Kong is the network/API gateway but is not the cross-system write authority.

## Promotion rule

Templates remain `active=false` and their HTTP command nodes remain disabled. `config/n8n-policy.json` intentionally remains `UNVERIFIED` until staging proves the endpoint binding, the `n8n-automation` credential binding, editor access policy, and egress controls. Do not weaken the validator to make an executable workflow pass early.

A template may be promoted only after a reviewed n8n credential is bound from n8n's credential store. No token, client secret, provider credential, database credential, or HMAC secret belongs in workflow JSON or Git.

## Odoo commands

The first executable provider slice is intentionally narrow:

- `crm.lead.create.v1` -> target `odoo-19` -> capability `ODOO_WRITE`
- `crm.lead.update.v1` -> target `odoo-19` -> capability `ODOO_WRITE`

Middleware performs the Odoo call and mandatory read-back. n8n never calls Odoo directly.

## Safety state

This branch prepares source integration only. It does not activate workflows or change runtime credentials. `ODOO_WRITE` and all external-delivery flags remain false until a separate staging activation is approved and verified.
