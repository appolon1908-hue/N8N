PHASE: N2 Shared foundation
COMMIT: 4cbb441b1e7d9c7d3d850a9ac9f26aae53639f1d
BASE_COMMIT: 2ead33d49d72ce1edc94cefb4d050334f7a145cd
TESTS_BEFORE / AFTER: 47 / 54
WORKFLOWS_DECLARED: 65
WORKFLOWS_BUILT: 0
SHARED_TEMPLATES: 8
VALIDATORS_GREEN: YES
MIDDLEWARE_PATHS_DISTINCT: 1
ACTIVE_WORKFLOWS: 0
EXTERNAL_EFFECTS_ENABLED: false
PRODUCTION_CHANGED: false
DEFECTS_CLOSED: PR #27 P1 failure-path, failure-envelope, and gateway-header findings
BLOCKERS: N4 cross-repository envelope convention remains open; no N2 blocker

## Template audit

- All eight templates are inactive, credential-free, Middleware-only, and
  accepted by `validate_workflows.py`.
- All three command-producing templates shape every required field from
  `command-envelope.schema.json` and send the required gateway headers.
- Every template declares explicit timeout reconciliation semantics and
  `automatic_retry_on_timeout: false`.
- No node enables `retryOnFail`; an indeterminate command outcome must be
  reconciled rather than repeated.
- `error-dead-letter.v2.json` ports the recursive error guard and classified
  failure handoff pattern found on both historical operations branches. Those
  two branches resolve to the same source commit (`81f45e8`) and contained no
  separate protected replay implementation.
- `human-approval.v2.json` creates a durable approval request through
  Middleware. It neither waits indefinitely nor grants approval inside n8n.
- Review remediation binds failure reporting to the runtime `job_id`, shapes
  the exact `FailureResult` body (including `lease_token`), and sends the full
  required gateway-header set from both new HTTP templates. Dynamic URL path
  interpolation is restricted to simple `$json` field segments in inactive
  templates and remains prohibited for verified production bindings.

## Evidence

```text
python3 -m pytest tests -q
54 passed, 65 xfailed, 3 subtests passed

python3 scripts/validate_workflow_completeness.py
WORKFLOW_COMPLETENESS=PASS
WORKFLOWS_DECLARED=65
WORKFLOWS_BUILT=0
EXPECTED_MISSING=65

python3 scripts/validate_workflows.py workflows
WORKFLOW_VALIDATION=PASS (8 templates)

python3 scripts/validate_repository.py
REPOSITORY_VALIDATION=PASS

python3 scripts/scan_secrets.py .
SECRET_SCAN=PASS

make validate
PASS
```

No runtime import, activation, credential binding, production change, or
external effect occurred.
