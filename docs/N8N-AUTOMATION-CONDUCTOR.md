# n8n Automation Conductor Doctrine

n8n is the automation conductor.

It coordinates approved actions across Codestra systems, but it never becomes the owner of important business data, provider credentials, consent policy, budget authority, identity authority, delivery state or canonical customer records.

## Canonical Lead Flow

```text
Meta lead
  -> Middleware
  -> Odoo
  -> n8n
     -> request AI qualification through Middleware
     -> request email through Middleware
     -> request SMS through Middleware
     -> request follow-up creation through Middleware
     -> request call scheduling through Middleware
     -> notify salesperson through Middleware-approved channel
```

Important: `send email` and `send SMS` mean n8n requests governed Middleware commands. n8n must not call SMTP, Klyrow, Telnexa, Postal, Jasmin, social providers or Odoo directly.

## Conversion Feedback Flow

```text
Odoo deal won
  -> Middleware event/read-back
  -> n8n orchestration
  -> Middleware
  -> Marketing attribution
  -> Conversion attribution
```

Odoo remains the CRM system of record. Marketing owns attribution semantics. Middleware owns command state, authorization, idempotency, policy checks, adapter calls and reconciliation.

## Non-Negotiable Boundary

- n8n may call only the declared Codestra Middleware automation API.
- n8n may not store provider credentials for systems it does not own.
- n8n may not directly bypass Middleware for external business writes.
- n8n may not directly change Odoo, SMTP/email, SMS, social, crawler, database, Redis, Keycloak, Kong or provider state.
- A successful n8n execution is orchestration evidence, not proof that a destination write succeeded.
- Destination read-back and final operation state come from Middleware.

This doctrine applies to every workflow pack, roadmap design and future executable export.
