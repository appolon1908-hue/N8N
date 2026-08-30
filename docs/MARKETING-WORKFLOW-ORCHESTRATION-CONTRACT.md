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
- Provider credentials outside approved secret management

## Canonical Workflows
1. New attributed lead -> Odoo -> qualification -> communication -> appointment.
2. Campaign approved -> provider synchronization -> status verification -> reporting.
3. Social content approved -> Codestra Social -> social runtime -> publication result.
4. Lead inactivity -> CRM rule -> follow-up message -> activity update.
5. Conversion/revenue outcome -> Odoo -> Marketing attribution feedback.

## Safety Rules
- Workflow nodes call supported service APIs; they do not write another service's database.
- Every mutation includes correlation and idempotency context.
- Production workflows must have explicit capability flags and environment scoping.
- Retries must distinguish safe/idempotent operations from non-repeatable actions.
- Human approval is required wherever the owning service policy requires it.

## Implementation Order
1. Canonical credential references
2. Standard Codestra API nodes/HTTP contracts
3. Lead intake workflow
4. Qualification/nurture workflow
5. Campaign sync workflow
6. Social publishing workflow
7. Conversion feedback workflow
8. Failure/replay/observability workflows