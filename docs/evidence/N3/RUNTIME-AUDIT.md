# N3 read-only runtime audit

Captured: `2026-08-30T16:33:46Z`  
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

Production Compose labels resolve to `/opt/codestra/compose` and four files:

- `compose.yaml`
- `compose.final-production-trust.yaml`
- `compose.n8n-db-host-remediation.yaml`
- `compose.odoo-n8n-hardening.yaml`

The directory is `root:codestra-admin`, mode `0750`; each file is `root:root`,
mode `0644`, on device `2306`. The production n8n data mount resolves to
`/var/lib/docker/volumes/codestra_n8n_data/_data` at `/home/node/.n8n`.

Staging Compose labels resolve to `/opt/codestra/n8n-staging/compose.yaml` and
`compose.queue.override.yaml`. The main, webhook, and two worker containers use
the same image digest and data volume. Staging PostgreSQL and Redis containers
are healthy and expose ports only inside their Compose networks.

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

## Audit command

```text
ssh codestra-app python3 - --component n8n --running-only --max-path-results 12 \
  < operations/runtime_path_audit.py
```

No service was restarted, no Compose configuration was rendered, no workflow
was imported or activated, and no production file was changed.
