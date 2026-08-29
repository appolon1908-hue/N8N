#!/usr/bin/env bash
set -euo pipefail
umask 077

backup_root=${CODESTRA_N8N_BACKUP_ROOT:-/opt/codestra/backups/n8n-recovery}
gpg_home=${CODESTRA_DATABASE_BACKUP_GPG_HOME:-/etc/codestra/backup-gpg}
gpg_recipient=${CODESTRA_DATABASE_BACKUP_GPG_RECIPIENT:-Codestra Backup Recipient}
retention_count=${CODESTRA_N8N_BACKUP_RETENTION_COUNT:-14}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 0700 "$backup_root"
[[ "$retention_count" =~ ^[0-9]+$ ]] && (( retention_count >= 2 ))
work=$(mktemp -d "$backup_root/.work-$stamp.XXXXXX")
archive="$work.tar.gz"
final="$backup_root/$stamp"
paused=()

resume() {
  local container rc=0
  local still_paused=()
  for container in "${paused[@]}"; do
    if ! docker unpause "$container" >/dev/null 2>&1; then
      still_paused+=("$container")
      rc=1
    fi
  done
  paused=("${still_paused[@]}")
  return "$rc"
}

cleanup() {
  resume || true
  if [[ -d "$work" && "$work" == "$backup_root"/.work-20*T*Z.* ]]; then
    find "$work" -xdev -type f -delete 2>/dev/null || true
    find "$work" -depth -type d -empty -delete 2>/dev/null || true
  fi
  test ! -e "$archive" || unlink "$archive"
}
trap cleanup EXIT
trap 'printf "N8N_RECOVERY_BACKUP=FAIL\n" >&2' ERR

install -d -m 0700 "$final" "$work/database" "$work/volumes" "$work/secrets" "$work/workflows" "$work/credentials" "$work/config" "$work/runtime"
gpg --homedir "$gpg_home" --batch --list-keys "$gpg_recipient" >/dev/null

docker exec codestra-n8n-1 n8n export:workflow --all --output=/home/node/.n8n/n8n-recovery-workflows.json >/dev/null
docker cp codestra-n8n-1:/home/node/.n8n/n8n-recovery-workflows.json "$work/workflows/production.json"
docker exec codestra-n8n-1 unlink /home/node/.n8n/n8n-recovery-workflows.json
docker exec codestra-n8n-staging-n8n-1 n8n export:workflow --all --output=/home/node/.n8n/n8n-recovery-workflows.json >/dev/null
docker cp codestra-n8n-staging-n8n-1:/home/node/.n8n/n8n-recovery-workflows.json "$work/workflows/staging.json"
docker exec codestra-n8n-staging-n8n-1 unlink /home/node/.n8n/n8n-recovery-workflows.json

for container in codestra-n8n-1 codestra-n8n-staging-n8n-1 codestra-n8n-staging-webhook-1 codestra-n8n-staging-worker-1 codestra-n8n-staging-worker-2-1; do
  docker pause "$container" >/dev/null
  paused+=("$container")
done

docker exec codestra-postgres-1 pg_dump -U postgres -d codestra_n8n -Fc > "$work/database/production.dump"
docker exec codestra-n8n-staging-postgres-1 pg_dump -U n8n_staging -d n8n_staging -Fc > "$work/database/staging.dump"

docker run --rm --entrypoint /bin/sh --user 0:0 \
  -v codestra_n8n_data:/production:ro \
  -v codestra-n8n-staging_n8n_data:/staging:ro \
  -v "$work/volumes":/backup \
  n8nio/n8n@sha256:cfe2704ff858395503d42548206c2c99ea351a205e941063a9d9b77b0f404478 -c 'tar -czf /backup/production-n8n-data.tar.gz -C /production . && tar -czf /backup/staging-n8n-data.tar.gz -C /staging .'

resume

install -m 0400 /etc/codestra/secrets/n8n-staging/files/n8n_encryption_key "$work/secrets/staging-n8n-encryption-key"
install -m 0400 /etc/codestra/secrets/n8n-staging/files/n8n_jwt_secret "$work/secrets/staging-n8n-jwt-secret"
docker cp codestra-n8n-1:/run/secrets/n8n_encryption_key "$work/secrets/production-n8n-encryption-key"
chmod 0400 "$work/secrets/production-n8n-encryption-key"

docker exec codestra-postgres-1 psql -U postgres -d codestra_n8n -At -F $'\t' -c "select c.name,c.type,p.name,sp.role,c.\"createdAt\",c.\"updatedAt\" from credentials_entity c join shared_credentials sp on sp.\"credentialsId\"=c.id join project p on p.id=sp.\"projectId\" order by c.name" > "$work/credentials/production-metadata.tsv"
docker exec codestra-n8n-staging-postgres-1 psql -U n8n_staging -d n8n_staging -At -F $'\t' -c "select c.name,c.type,p.name,sp.role,c.\"createdAt\",c.\"updatedAt\" from credentials_entity c join shared_credentials sp on sp.\"credentialsId\"=c.id join project p on p.id=sp.\"projectId\" order by c.name" > "$work/credentials/staging-metadata.tsv"

install -m 0600 /opt/codestra/compose/compose.yaml "$work/config/production-compose.yaml"
install -m 0600 /opt/codestra/compose/compose.final-production-trust.yaml "$work/config/production-final-trust.yaml"
install -m 0600 /opt/codestra/compose/compose.n8n-db-host-remediation.yaml "$work/config/production-db-remediation.yaml"
install -m 0600 /opt/codestra/compose/compose.odoo-n8n-hardening.yaml "$work/config/production-hardening.yaml"
install -m 0600 /opt/codestra/n8n-staging/compose.yaml "$work/config/staging-compose.yaml"
install -m 0600 /opt/codestra/n8n-staging/compose.queue.override.yaml "$work/config/staging-queue.yaml"
install -m 0600 /opt/codestra/config/caddy/Caddyfile "$work/config/Caddyfile"

for container in codestra-n8n-1 codestra-n8n-staging-n8n-1 codestra-n8n-staging-webhook-1 codestra-n8n-staging-worker-1 codestra-n8n-staging-worker-2-1 codestra-n8n-staging-postgres-1 codestra-n8n-staging-redis-1; do
  docker inspect "$container" > "$work/runtime/$container.json"
done
docker network inspect codestra_backend codestra-n8n-staging_backend codestra-n8n-staging_edge > "$work/runtime/networks.json"
docker image inspect n8nio/n8n@sha256:11524034450080bd0032754892b23ff20be43d72cf320ce75640f7c5475fdca8 n8nio/n8n@sha256:cfe2704ff858395503d42548206c2c99ea351a205e941063a9d9b77b0f404478 > "$work/runtime/images.json"

(
  cd "$work"
  # The output file is excluded from find before the pipeline writes it.
  # shellcheck disable=SC2094
  find . -type f ! -name PLAINTEXT-SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > PLAINTEXT-SHA256SUMS
  sha256sum -c PLAINTEXT-SHA256SUMS >/dev/null
  tar -czf "$archive" .
)
gpg --homedir "$gpg_home" --no-random-seed-file --batch --yes --trust-model always --recipient "$gpg_recipient" --encrypt --output "$final/n8n-recovery-$stamp.tar.gz.gpg" "$archive"
(
  cd "$final"
  sha256sum "n8n-recovery-$stamp.tar.gz.gpg" > SHA256SUMS
  sha256sum -c SHA256SUMS >/dev/null
)
cat > "$final/STATUS.txt" <<EOF
RECOVERY_CAPTURE=PASS
TIMESTAMP=$stamp
PRODUCTION_DATABASE=PASS
STAGING_DATABASE=PASS
VOLUMES=2
ENCRYPTION_KEYS=2
WORKFLOW_EXPORTS=PASS
CREDENTIAL_METADATA=PASS
CONFIG_RUNTIME_EVIDENCE=PASS
ENCRYPTION=PASS
RESTORE_REHEARSAL=PENDING
EOF
sha256sum "$final/STATUS.txt" > "$final/EVIDENCE-SHA256SUMS"

mapfile -t complete_recoveries < <(
  find "$backup_root" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' |
    grep -E '^20[0-9]{6}T[0-9]{6}Z$' |
    sort -r |
    while IFS= read -r directory; do
      grep -qx 'RECOVERY_CAPTURE=PASS' "$backup_root/$directory/STATUS.txt" 2>/dev/null || continue
      find "$backup_root/$directory" -maxdepth 1 -type f -name 'n8n-recovery-*.tar.gz.gpg' -print -quit | grep -q . || continue
      printf '%s\n' "$directory"
    done
)
for directory in "${complete_recoveries[@]:retention_count}"; do
  find "$backup_root/$directory" -xdev -type f -delete
  find "$backup_root/$directory" -depth -type d -empty -delete
done
printf 'N8N_RECOVERY_BACKUP=PASS\nN8N_RECOVERY_DIRECTORY=%s\n' "$final"
