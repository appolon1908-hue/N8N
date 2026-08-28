# n8n 2.36.8 staging certification — 2026-08-28

## Candidate

- Version: `2.36.8`
- Image: `n8nio/n8n@sha256:cfe2704ff858395503d42548206c2c99ea351a205e941063a9d9b77b0f404478`
- Trivy with current database and `--ignore-unfixed`: 0 critical, 3 high findings (previous 2.30.8 baseline: 4 critical, 52 high)

## Passed

- Isolated migration on a private network with no host ports.
- 327 workflows before and after migration; 11 active states preserved.
- Nine credential records present and all nine decrypted successfully in tmpfs; plaintext was removed.
- Main, webhook, and two workers upgraded together and are healthy.
- Read-only root, UID/GID 1000:1000, all capabilities dropped, no-new-privileges, explicit tmpfs, and PID limit 256 are effective.
- Workflow export after upgrade returned 327 records.
- Queue Redis authentication/PING and worker readiness endpoints pass.
- Public webhook request is blocked by edge policy with HTTP 403.
- Pre-upgrade encrypted recovery point and isolated 2.30.8 restore rehearsal provide the rollback reference.

## Failed or incomplete

- The internal certification webhook registered and queued execution 566, but the no-authorization synthetic request failed in the Crypto node. Its authorization dependency is not represented by managed credential metadata, so the successful webhook path is not certified.
- External task-runner mode is not deployed. Internal JS runners registered; Python runner startup reports Python absent. This remains a production promotion blocker.
- A full rollback of live staging was not performed because that would discard the successful migrated state. Rollback is certified through restore of the immutable pre-upgrade database/volume/key recovery point, not by running 2.30.8 against a migrated database.

## Decision

Staging may remain on 2.36.8 for remediation and soak testing. Production promotion is **not approved** until the webhook dependency, external task runners, credential metadata gaps, workflow reconciliation, and a defined soak period pass.
