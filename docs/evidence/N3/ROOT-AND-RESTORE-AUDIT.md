# N3 protected-path and restore audit

Captured through: `2026-08-30T17:17Z`
Host: `middleware` (`65.109.65.169`, `10.40.0.1`)
Operator: `codestra-admin` through the configured `codestra-app` identity
Policy: fixed targets, no secret output, isolated restore only

## Protected path metadata

The metadata collection used one temporary container with a locally cached,
digest-pinned Alpine image. It had no network, a read-only root filesystem,
all capabilities dropped, `no-new-privileges`, and only explicit read-only
bind mounts. It executed `stat` and was removed immediately afterward.

| Runtime item | Canonical host path | Type | UID:GID | Mode | Device |
|---|---|---|---:|---:|---:|
| repository checkout | `/root/codestra-production-completion` | directory | 0:0 | 0755 | 2306 |
| production Compose | `/opt/codestra/compose/compose.yaml` | file | 0:0 | 0644 | 2306 |
| staging Compose | `/opt/codestra/n8n-staging/compose.yaml` | file | 0:0 | 0640 | 2306 |
| staging queue override | `/opt/codestra/n8n-staging/compose.queue.override.yaml` | file | 0:0 | 0600 | 2306 |
| production n8n data | `/var/lib/docker/volumes/codestra_n8n_data/_data` | directory | 1000:1000 | 2755 | 2306 |
| staging n8n data | `/var/lib/docker/volumes/codestra-n8n-staging_n8n_data/_data` | directory | 1000:1000 | 0755 | 2306 |
| staging PostgreSQL data | `/var/lib/docker/volumes/codestra-n8n-staging_postgres_data/_data` | directory | 70:70 | 0700 | 2306 |
| staging Redis data | `/var/lib/docker/volumes/codestra-n8n-staging_queue_redis_data/_data` | directory | 999:1000 | 0755 | 2306 |
| production secret provider | `/etc/codestra/secrets/codestra-compose` | directory | 0:0 | 0700 | 2306 |
| staging secret provider | `/etc/codestra/secrets/n8n-staging` | directory | 0:0 | 0700 | 2306 |
| internal reverse proxy | `/opt/codestra/middleware/deploy/internal-n8n-private/Caddyfile` | file | 0:0 | 0644 | 2306 |
| n8n recovery backup | `/opt/codestra/backups/n8n-recovery` | directory | 0:0 | 0700 | 2306 |
| legacy n8n backup | `/opt/codestra/backups/n8n` | directory | 0:0 | 0750 | 2306 |

No file contents or directory listings were emitted. The temporary metadata
container was confirmed absent after the audit.

## Edition evidence

`n8n license:info` reported no initialized/valid license certificate and zero
entitlements for production n8n `2.30.8` and staging n8n `2.36.8`. This is the
unlicensed/community feature state. No license mutation command was executed.
The staging CLI acquired and released its normal startup migration lock without
executing a migration.

## Isolated restore rehearsal

Source recovery set: `20260830T072022Z`

The latest encrypted recovery artifact was mounted read-only. Its configured
backup key was used inside a network-disabled temporary decrypt container; key
material and decrypted customer data were never printed or persisted outside
temporary Docker storage. The encrypted SHA-256 manifest and every plaintext
manifest entry passed.

Validated artifacts:

- production and staging PostgreSQL custom-format dumps;
- production and staging n8n data archives;
- production and staging workflow exports;
- configuration, runtime-image/network metadata, credential metadata, and
  required encryption-key recovery files.

Both database dumps were restored with `--no-owner --no-privileges
--exit-on-error` into a network-disabled PostgreSQL 17.11 container backed only
by tmpfs:

```text
ENCRYPTED_CHECKSUM=PASS
PLAINTEXT_CHECKSUMS=PASS
VOLUME_ARCHIVES=PASS
WORKFLOW_EXPORTS=PASS
PRODUCTION_DATABASE_RESTORE=PASS
PRODUCTION_PUBLIC_TABLES=114
STAGING_DATABASE_RESTORE=PASS
STAGING_PUBLIC_TABLES=130
LIVE_DATABASES_TOUCHED=NO
EXTERNAL_NETWORK_USED=NO
TEMPORARY_RESOURCES_REMOVED=YES
```

Three earlier isolated attempts stopped safely before database restoration: one
PostgreSQL initialization constraint and two temporary dump traversal-permission
constraints. Cleanup removed their containers and volumes. The successful run
changed traversal/read modes only inside its disposable decrypted artifact
volume; source backup permissions were unchanged.

One mistyped local-image digest caused Docker to attempt and fail a registry
resolution before any restore container started. The successful rehearsal used
only already-cached tagged images and `--network none` containers.

## Safety conclusion

No live database or live n8n volume was written, no service was restarted, no
workflow was imported or activated, no secret value was displayed, and no
external effect was enabled. The only host mutations were creation and removal
of explicitly named temporary audit/restore containers and volumes.
