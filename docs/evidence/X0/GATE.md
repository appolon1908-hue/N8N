# X0 Gate: One Envelope, One Path

Status: `NO_GO_R6`

Branch: `phase-x0/envelope-reconciliation`

## Measured Values

- `CANONICAL_WORKFLOWS_DESIGNED: 0 of 5`
- `ROADMAP_PACKS: 0 of 4`
- `ENDPOINT_BINDING: UNVERIFIED`
- `CREDENTIAL_BINDING: UNVERIFIED`
- `MIDDLEWARE_PATHS_DISTINCT: 1`
- `CANONICAL_COMMAND_PATH: /v2/automation/commands`
- `KILL_SWITCHES_ALL_FALSE: YES`
- `AI_AUTHORITY_ASSERTED_NONE: YES`
- `PRODUCTION_CHANGED: false`

## Completed

- `contracts/command-envelope.schema.json` now documents the required header contract and mirrors `X-Tenant-ID`, `X-Correlation-ID` and `Idempotency-Key` to body fields used for validation and durable replay.
- Command type patterns now reject trailing version suffixes such as `.v1`; version remains the separate integer field.
- `contracts/platform-control-plane.v1.json` now uses `POST /v2/automation/commands` and `GET /v2/automation/commands/{command_id}`.
- `contracts/middleware-surface.v1.json` declares every n8n-callable Middleware path, required headers, expected responses, idempotency behavior and timeout reconciliation.
- All six workflow templates use the declared Middleware surface and send the required headers for their declared path.
- Historical command aliases are documented in `docs/DECISIONS.md` and prohibited by validator policy.
- R6 blockers are documented in `docs/BLOCKERS.md` for Klyrow command type versioning and the unresolved Temporal control-plane component.
- Roadmap kill switches were added to `config/capabilities.json` and remain false.

## Local Evidence

- `python scripts/validate_workflows.py workflows` -> `WORKFLOW_VALIDATION=PASS`
- `python -m unittest tests.test_integration_contracts tests.test_policy_guards` -> `Ran 36 tests`, `OK`
- `python -m unittest tests.test_compose_semantics tests.test_integration_contracts tests.test_policy_guards tests.test_ruleset_contract` -> `Ran 44 tests`, `OK`
- `python scripts/scan_secrets.py .` -> `SECRET_SCAN=PASS`
- `python scripts/verify_runtime_paths.py --allow-unverified` -> `RUNTIME_PATH_VALIDATION=PASS`, `RUNTIME_PATHS=UNVERIFIED`
- `python scripts/validate_ruleset_contract.py` -> `GITHUB_RULESET_CONTRACT=PASS`
- `python scripts/validate_platform_control_plane.py` -> `PLATFORM_CONTROL_PLANE=PASS`
- `python scripts/validate_workflow_completeness.py` -> `WORKFLOW_COMPLETENESS=PASS`, `WORKFLOWS_DECLARED=65`, `WORKFLOWS_BUILT=0`, `EXPECTED_MISSING=65`
- Kill switch probe -> `KILL_SWITCHES_ALL_FALSE True`

## Local Limitation

`make validate`, direct Docker Compose rendering and `scripts/validate_repository.py` could not fully run on this Windows host because `make` and `docker` are not installed in the execution PATH. The equivalent non-Docker Python checks above were run directly.

## Stop Condition

X0 remains `NO_GO_R6` until owners resolve:

- Klyrow command type version convention: `email.message.send` + `version: 1` versus `email.message.send.v1`.
- Temporal control-plane role: real Middleware-owned runtime component needing a contract, or stale flow entry to remove through cross-repo agreement.

This branch does not activate workflows, enable delivery, enable Odoo writes, change credentials or apply production runtime changes.
