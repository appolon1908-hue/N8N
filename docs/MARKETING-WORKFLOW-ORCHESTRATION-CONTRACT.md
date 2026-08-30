# n8n — Marketing Workflow Orchestration Contract

## Mission
n8n coordinates approved cross-service workflows. It is an orchestrator, not the authoritative owner of CRM, campaign, communication, social, identity, AI or financial state.

## Owns
- Workflow definitions and versions
- Trigger-to-action orchestration
- Human approval workflow steps where explicitly designed
- Retryable orchestration state
- Operational workflow metadata

## Does Not Own
- Canonical customer or lead records
- Campaign budgets or paid-media authority
- Consent/suppression policy
- AI provider routing
- Identity or gateway policy
- Provider or downstream-service credentials

n8n may hold only its own Middleware service identity in approved secret management. Provider credentials and downstream-service credentials remain owned by the corresponding governed service or integration authority and are never exposed to workflow definitions.

## Canonical Workflows
1. New attributed lead -> governed Middleware command -> Marketing attribution -> Odoo upsert -> qualification -> communication -> appointment.
2. Campaign approved -> governed Middleware command -> provider synchronization -> status verification -> reporting.
3. Social content approved -> governed Middleware command -> Codestra Social -> social runtime -> publication result.
4. Lead inactivity -> governed Middleware command -> CRM rule -> follow-up message -> activity update.
5. Conversion/revenue outcome -> governed Middleware command -> Odoo -> Marketing attribution feedback.

## Safety Rules
- Every effect-producing workflow node calls the private Middleware API only. n8n does not call Odoo, Marketing, Communication, Social, AI, advertising providers, or other downstream services directly.
- Read-only local workflow metadata operations may remain inside n8n, but cross-service effects must use a governed Middleware command.
- Every mutation includes correlation and idempotency context.
- Production workflows must have explicit capability flags and environment scoping.
- Retries must distinguish safe/idempotent operations from non-repeatable actions.
- Human approval is required wherever the owning service policy requires it.
- Provider and downstream-service credentials are never owned by n8n.

## Implementation Order
1. Middleware-only service identity and credential reference
2. Standard governed Middleware command nodes/HTTP contracts
3. Canonical workflow identity registration
4. Lead intake workflow
5. Qualification/nurture workflow
6. Campaign sync workflow
7. Social publishing workflow
8. Conversion feedback workflow
9. Failure/replay/observability workflows
