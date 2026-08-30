# Branching strategy

## Baseline branch

Current work branches from protected `main`. The former `platform/services-middleware-automations-designs` umbrella branch is retired; it remains historical evidence only and must not be used as the base for new implementation or contract work.

## Implementation branches

Create focused branches from current protected `main` rather than placing every executable workflow into one pull request:

- `automation/odoo-crm`
- `automation/vicidial-telephony`
- `automation/jasmin-sms`
- `automation/postal-email`
- `automation/kyqra-crawler`
- `automation/moneybee-loans`
- `automation/breero-marketplace`
- `automation/larim-a-booking`
- `automation/freight-operations`
- `operations/delivery-dead-letter-replay`
- `privacy/suppression-deletion-retention`
- `infra/runtime-path-verification`
- `infra/staging-deployment-implementation`

Each branch must include its contract, inactive workflow exports, tests, failure paths, rollback notes, and capability impact. Dependency branches merge in order; do not merge a final stacked branch directly into `main` while its prerequisites remain open.
