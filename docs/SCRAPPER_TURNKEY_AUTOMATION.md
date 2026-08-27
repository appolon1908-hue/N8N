# Scrapper Turnkey Automation

Status: inactive workflow contracts only. No workflow is activated and no external side effect is enabled by this branch.

## Boundary

n8n owns orchestration only. Codestra Middleware owns correctness, authorization, idempotency, retry, replay, dead-letter state, Odoo mappings, delivery receipts, and reconciliation.

n8n must not:

- expose the scraper directly to the public internet;
- call scraper PostgreSQL or Redis;
- write to Odoo from an unnormalized scraper payload;
- create a new command ID when retrying the same business action;
- treat workflow execution success as proof that a destination write succeeded;
- store service credentials inside workflow JSON.

## Event router

`workflows/scrapper/turnkey-event-router.v1.json` accepts only Middleware-normalized events. It validates the event type and required identity fields, then routes to contract-only branches. All side-effect nodes remain absent or disabled until a separately reviewed workflow implements them.

The route is private and must be invoked by Middleware using an approved service identity. Middleware has already performed signature, schema, duplicate, tenant, consent, suppression, and policy checks before n8n sees the event.

## Reverse commands

`workflows/scrapper/turnkey-command-request.v1.json` constructs only the three allowed v1 command types:

```text
scraper.crawl.requested
scraper.job.cancel.requested
scraper.source.validate.requested
```

The workflow sends the command to Codestra Middleware, not to the scraper. Middleware creates the durable outbox delivery to the scraper private integration endpoint. The HTTP node is disabled and disconnected in source until a staging credential, endpoint, mTLS path, and approval are present.

## Credentials

The workflow references a credential placeholder named `Codestra Middleware Service Identity`. A real credential must be created in n8n's credential store, scoped to the minimum required Middleware API, and never exported to Git.

## Retry and idempotency

- The command envelope ID is the idempotency key.
- A retry preserves the same command ID and body.
- n8n workflow retry is not the authoritative delivery retry; Middleware outbox state is.
- A timeout after success is reconciled through the Middleware command receipt.
- Failed permanent commands enter Middleware dead-letter state and require an audited replay decision.

## Activation gate

Before enabling either workflow:

1. import into a staging n8n project;
2. assign an owner and environment tag;
3. configure the private Middleware base URL;
4. create the least-privilege service credential;
5. confirm outbound access is limited to Middleware;
6. run duplicate and timeout-after-success tests;
7. verify Odoo remains write-disabled;
8. verify the scraper accepts reverse commands only through its durable inbox;
9. record rollback by disabling the workflow and revoking the credential;
10. obtain explicit approval naming workflow IDs and source SHA.

```text
N8N_SCRAPPER_EVENT_ROUTER_ACTIVE=false
N8N_SCRAPPER_COMMAND_WORKFLOW_ACTIVE=false
ODOO_WRITE=false
LIVE_WRITES=false
```
