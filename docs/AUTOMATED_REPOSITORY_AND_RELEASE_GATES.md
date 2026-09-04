# Automated Repository and Release Gates

## Status and authority

This document explains the automation model. It does not change GitHub settings, deploy a runtime, activate a workflow, or authorize an external effect.

The enforceable source contract for protected `main` is `config/github-main-ruleset.v1.json`. Repository settings and the active GitHub ruleset remain authoritative if this document ever drifts.

## Current protected-main merge policy

The reviewed ruleset requires:

- pull-request merge into `main`;
- one approving review;
- Code Owner review;
- approval after the latest push;
- resolution of review conversations;
- the strict, up-to-date `Validate exact repository SHA` status check;
- blocked branch deletion and non-fast-forward updates;
- no configured bypass actors.

Repository auto-merge may be used to complete a merge after all of those gates pass. Auto-merge is not self-approval and does not bypass a stale review, failing status check, unresolved conversation, or protected-branch rule.

A future proposal to change the required review count must update the authoritative ruleset contract, validation, evidence, and GitHub settings together. A Markdown statement alone cannot reduce protection.

## Automated source validation

Every candidate must prove the exact PR head and run the repository safety suite, including:

- Python/tooling compilation;
- repository and n8n policy validation;
- catalog authority and inventory reconciliation;
- workflow completeness and inactive-export checks;
- consumed-contract and Middleware-surface tests;
- dangerous-node and runtime denylist checks;
- secret scanning;
- Compose and runtime-path validation;
- protected ruleset-contract checks.

Any pushed change invalidates prior exact-head evidence and, under the reviewed ruleset, requires approval of the latest push.

## Immutable candidate automation

`.github/workflows/codestra-deploy-readiness.yml` delegates to an exact SHA-pinned reusable workflow. The automated path separates five operations:

1. `verify` — read-only source validation;
2. `release` — build and publish an immutable signed source/configuration candidate;
3. `deploy-staging-readonly` — protected staging deployment with external effects denied;
4. `certify-staging-readonly` — protected staging certification and evidence capture;
5. `promote-production-readonly` — maximum one-percent GET/HEAD-only production canary.

Pull-request events receive read-only validation jobs. Candidate publication is limited to protected branch authority. Staging and production operations require manual workflow dispatch, fixed confirmation text, protected environments, approved self-hosted runner labels, and the exact immutable candidate.

## Separation of authorities

The following are deliberately not equivalent:

```text
source approval
    != source merge
    != immutable candidate publication
    != staging deployment
    != staging certification
    != production read-only canary
    != workflow activation
    != external-effect authorization
```

A source merge can never, by itself, authorize provider delivery or live business effects.

## Production safety invariants

- No administrator bypass is part of the normal merge or release path.
- Force pushes and protected-branch deletion remain blocked.
- Releases use exact source SHAs and immutable digests/checksums.
- Staging and production promotion must not rebuild or retag the certified candidate.
- Backup, isolated restore, rollback rehearsal, source/digest readback, readiness, and monitoring evidence remain required before production promotion.
- A production canary remains read-only, limited to GET/HEAD, and no more than one percent.
- Workflow activation and each effect capability remain separately gated.
- Calls, email, SMS, social publishing, provider delivery, trading, payments, deposits, withdrawals, transfers, custody, and chain broadcast remain disabled unless explicitly authorized by a separate protected change.
- SSH access policy is outside this repository and must not be weakened by an automation change.

## Failure behavior

Automation fails closed on any stale source head, missing review, failing required check, unresolved review thread, source/digest mismatch, signature or attestation failure, secret finding, unsafe workflow export, unavailable monitoring, readiness failure, unproven rollback, write request in a read-only phase, or movement in an external-effect counter.
