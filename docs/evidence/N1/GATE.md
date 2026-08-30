PHASE: N1 One Middleware contract
COMMIT: d6e9cc6ca6b25facf88ea87b184ce5dc59c63585
BASE_COMMIT: 4d9f30fe3e89d65b1a66bda02943191e3dd8d118
TESTS_BEFORE / AFTER: 43 / 47
WORKFLOWS_DECLARED: 65
WORKFLOWS_BUILT: 0
VALIDATORS_GREEN: YES
MIDDLEWARE_PATHS_DISTINCT: 1
ACTIVE_WORKFLOWS: 0
EXTERNAL_EFFECTS_ENABLED: false
PRODUCTION_CHANGED: false
DEFECTS_CLOSED: N3
BLOCKERS: N4 cross-repository envelope convention (R6; documented in docs/BLOCKERS.md)

## Contract decision

The single command submission endpoint is:

```text
POST /v1/integrations/n8n/commands
```

Command reconciliation uses:

```text
GET /v1/integrations/n8n/operations/{command_id}
```

Claim, result reporting, and reconciliation are distinct operations rather
than competing command endpoints. Their current internal paths remain in the
surface with `implementation_status: CONTRACT_PENDING`; no workflow depending
on them is active.

## Evidence

```text
python3 -m pytest tests -q
47 passed, 65 xfailed

python3 scripts/validate_workflow_completeness.py
WORKFLOW_COMPLETENESS=PASS
WORKFLOWS_DECLARED=65
WORKFLOWS_BUILT=0
EXPECTED_MISSING=65

python3 scripts/validate_workflows.py workflows
WORKFLOW_VALIDATION=PASS

python3 scripts/validate_repository.py
REPOSITORY_VALIDATION=PASS

python3 scripts/scan_secrets.py .
SECRET_SCAN=PASS

make validate
PASS
```

The only remaining literal `/v2/automation/commands` occurrence is an
intentional negative validator test proving the retired path is rejected.

No workflow was activated, no production N8N configuration changed, and no
external effect was enabled.
