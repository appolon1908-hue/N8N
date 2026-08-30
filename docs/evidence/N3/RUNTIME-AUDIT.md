# N3 read-only runtime audit

Captured: `2026-08-30T16:54:13Z`
Auditor: `codestra-admin` through the configured `codestra-app` SSH identity
Host: `middleware` (`65.109.65.169`, `10.40.0.1`)
Policy: `READ_ONLY_NO_SECRET_CONTENT`
Mutation performed: `false`

## Verified observations

Docker metadata identifies two distinct, healthy n8n installations:

| Scope | Compose project/service | Version | Immutable image digest | State |
|---|---|---:|---|---|
| production | `codestra/n8n` | 2.30.8 | `sha256:11524034450080bd0032754892b23ff20be43d72cf320ce75640f7c5475fdca8` | healthy |
| staging main/webhook/workers | `codestra-n8n-staging` | 2.36.8 | `sha256:cfe2704ff858395503d42548206c2c99ea351a205e941063a9d9b77b0f404478` | healthy |

Both n8n images run as `1000:1000`, with a read-only root filesystem,
`CapDrop=ALL`, `no-new-privileges:true`, and immutable digest references.
The audit inspected no environment values, secret contents, database rows,
workflow data, or container logs.

Production Compose labels resolve to `/opt/codestra/compose`. The corrected
audit derives active Compose paths directly from matching container labels,
including generic filenames that do not contain `n8n`. All accessible active
production files were regular root-owned files on device `2306`, mode `0644`,
except `compose.phase-n2-activation.yaml`, which was mode `0600`.

The directory is `root:codestra-admin`, mode `0750`. The production n8n data mount resolves to
`/var/lib/docker/volumes/codestra_n8n_data/_data` at `/home/node/.n8n`.

Staging Compose labels resolve to `/opt/codestra/n8n-staging/compose.yaml` and
`compose.queue.override.yaml`. The main, webhook, and two worker containers use
the same image digest and data volume. Staging PostgreSQL and Redis containers
are healthy. Explicit Docker binding evidence records `published: false` for
the n8n, webhook, worker, PostgreSQL, and Redis container ports; this conclusion
is no longer inferred from port keys alone.

## Remaining verification blockers

`config/runtime-paths.json` remains `UNVERIFIED`. The restricted auditor can
read Docker metadata but cannot stat the staging Compose files or Docker volume
data directories. The following required evidence is therefore incomplete:

- owner, group, mode, and filesystem identity for staging Compose files;
- owner, group, mode, and filesystem identity for production/staging n8n data,
  staging PostgreSQL data, and staging Redis data directories;
- backup destination and restore evidence;
- n8n edition/licensed-feature confirmation;
- independent reviewer identity and review timestamp.

No runtime-path state transition is claimed until those items are collected by
a narrowly authorized read-only operator and independently reviewed.

The missing root-owned metadata can be collected without granting arbitrary
`stat`, shell, or file-read access by running the repository's fixed-allowlist
helper as root:

```text
python3 operations/runtime_path_privileged_stat.py
```

The helper accepts no path arguments, reads no file contents or directory
listings, and reports only type, UID, GID, mode, device, and inode.

## Supplemental evidence

- Docker volume inspection confirmed the four expected local volume names and
  mountpoints for production n8n, staging n8n, staging PostgreSQL, and staging
  Redis.
- In-container `stat` recorded production n8n data as `1000:1000/2755`, staging
  n8n data as `1000:1000/0755`, staging PostgreSQL data as `70:70/0700`, and
  staging Redis data as `999:1000/0755`, all on device `2306`.
- `n8n license:info` reported no initialized or valid license certificate and
  zero entitlements for production 2.30.8 and staging 2.36.8. The staging CLI
  briefly acquired and released its normal database migration lock during
  startup; it executed no migration or state-changing license command.
- `codestra-n8n-recovery-backup.timer` is active. Its last service run completed
  successfully at `2026-08-30T03:20:36-04:00`; the next run is scheduled for
  `2026-08-31T03:15:56-04:00`. This establishes backup execution, not restore
  success; reviewed restore evidence remains outstanding.

## Audit command

```text
ssh codestra-app python3 - --component n8n --running-only --max-path-results 12 \
  < operations/runtime_path_audit.py
```

No service was restarted, no Compose configuration was rendered, no workflow
was imported or activated, and no production file was changed.
