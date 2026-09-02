# n8n Rapid Domain + Campaign Onboarding

n8n is orchestration only. It consumes durable Middleware events for site/campaign onboarding and must not become the authority for domains, campaigns, telephony or provider credentials.

Expected events: site.onboarding.requested, site.onboarding.ready, campaign.sync.requested, campaign.synchronized, campaign.reconciliation_required, campaign.suspended, campaign.retired.

Workflows may coordinate notifications, CRM follow-up, content setup, QA checks and other approved tasks, but all consequential Odoo/VICIdial/provider mutations must be requested through Middleware using tenant, correlation, idempotency and operation identifiers.

Do not store VICIdial admin credentials, provider master secrets, OpenBao tokens or direct Odoo DB credentials in workflows. Production workflow activation remains gated until staging E2E, identity/scopes, secret delivery and rollback pass.
