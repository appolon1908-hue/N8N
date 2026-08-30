# N1 Gate: Middleware Contract

Status: `NO_GO_R6`

Branch: `phase-n1/middleware-contract`

## Completed

- Canonical n8n command endpoint selected: `POST /v2/automation/commands`.
- Legacy command aliases prohibited by `contracts/middleware-surface.v1.json`:
  - `/internal/v1/automation/commands`
  - `/v1/integrations/n8n/commands`
- Distinct non-command operations remain declared for claim, heartbeat, step, complete, fail, command read, approval, DLQ replay, reconciliation and capability read.
- Workflow validator now enforces the declared Middleware surface for HTTP node paths.
- Platform control-plane contract and Odoo proof template now use the canonical command endpoint.
- Klyrow envelope/header convention conflict documented in `docs/BLOCKERS.md`.

## Local Evidence

- `python scripts/validate_workflows.py workflows` -> `WORKFLOW_VALIDATION=PASS`
- `python -m unittest tests.test_integration_contracts tests.test_policy_guards` -> `Ran 33 tests`, `OK`
- `python -m unittest tests.test_compose_semantics tests.test_integration_contracts tests.test_policy_guards tests.test_ruleset_contract` -> `Ran 41 tests`, `OK`
- `python scripts/scan_secrets.py .` -> `SECRET_SCAN=PASS`
- `python scripts/verify_runtime_paths.py --allow-unverified` -> `RUNTIME_PATH_VALIDATION=PASS`
- `python scripts/validate_ruleset_contract.py` -> `GITHUB_RULESET_CONTRACT=PASS`
- `python scripts/validate_platform_control_plane.py` -> `PLATFORM_CONTROL_PLANE=PASS`
- `python scripts/validate_workflow_completeness.py` -> `WORKFLOW_COMPLETENESS=PASS`

## Local Limitation

`make validate` and direct Docker Compose rendering could not run on this Windows host because `make` and `docker` are not installed in the execution PATH. The equivalent non-Docker Python checks above were run directly.

## Stop Condition

N1 remains `NO_GO_R6` until Klyrow and Middleware owners decide the shared command envelope/header convention documented in `docs/BLOCKERS.md`. This branch does not activate workflows, enable external effects, change credentials or apply production runtime changes.
