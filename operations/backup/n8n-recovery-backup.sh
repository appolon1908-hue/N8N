#!/usr/bin/env bash
set -euo pipefail
umask 077

backup_root=${CODESTRA_N8N_BACKUP_ROOT:-/opt/codestra/backups/n8n-recovery}
work_root=${CODESTRA_N8N_BACKUP_WORK_ROOT:-/run/codestra/n8n-recovery-work}
gpg_home=${CODESTRA_DATABASE_BACKUP_GPG_HOME:-/etc/codestra/backup-gpg}
gpg_recipient=${CODESTRA_DATABASE_BACKUP_GPG_RECIPIENT:-Codestra Backup Recipient}
retention_count=${CODESTRA_N8N_BACKUP_RETENTION_COUNT:-14}
for command_name in docker gpg sha256sum install date stat flock sync mktemp tar find sort xargs mv chmod; do
  command -v "$command_name" >/dev/null || { printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=missing_command_%s\n' "$command_name" >&2; exit 1; }
done
: "${CODESTRA_RELEASE_SHA:?CODESTRA_RELEASE_SHA is required}"
: "${CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST:?CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST is required}"
: "${CODESTRA_N8N_STAGING_IMAGE_DIGEST:?CODESTRA_N8N_STAGING_IMAGE_DIGEST is required}"
: "${CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT:?CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT is required}"
[[ "$CODESTRA_RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]]
[[ "$CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]
[[ "$CODESTRA_N8N_STAGING_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]
[[ "$CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT" =~ ^[A-Fa-f0-9]{40}$ ]]
CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT=${CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT^^}
install -d -m 0700 "$backup_root"
install -d -m 0700 "$work_root"
[[ "$backup_root" == /* && -d "$backup_root" && ! -L "$backup_root" ]] || { printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=backup_root_invalid\n' >&2; exit 1; }
[[ "$work_root" == /* && -d "$work_root" && ! -L "$work_root" ]] || { printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=work_root_invalid\n' >&2; exit 1; }
[[ "$(stat -f -c %T "$work_root")" == "tmpfs" ]] || {
  printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=plaintext_work_root_must_be_tmpfs\n' >&2
  exit 1
}
[[ "$gpg_home" == /* && -d "$gpg_home" && ! -L "$gpg_home" ]] || { printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=gpg_home_invalid\n' >&2; exit 1; }
[[ "$(stat -c '%a' "$gpg_home")" == 700 && "$(stat -c '%u' "$gpg_home")" == "$(id -u)" ]] || { printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=gpg_home_ownership_or_mode_invalid\n' >&2; exit 1; }
[[ "$retention_count" =~ ^[0-9]+$ ]] && (( retention_count >= 2 ))
exec 9>"$backup_root/.backup.lock"
flock -n 9 || { printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=backup_already_running\n' >&2; exit 1; }
stamp=$(date -u +%Y%m%dT%H%M%SZ)
work=$(mktemp -d "$work_root/.work-$stamp.XXXXXX")
archive="$work_root/.archive-$stamp.tar.gz"
final="$backup_root/$stamp"
publish="$backup_root/.$stamp.partial"
[[ ! -e "$final" && ! -e "$publish" ]] || {
  printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=backup_stamp_collision\n' >&2
  exit 1
}
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
  if [[ -d "$work" && "$work" == "$work_root"/.work-20*T*Z.* ]]; then
    find "$work" -xdev -type f -delete 2>/dev/null || true
    find "$work" -depth -type d -empty -delete 2>/dev/null || true
  fi
  test ! -e "$archive" || unlink "$archive"
  test -z "${marker_partial:-}" || test ! -e "$marker_partial" || unlink "$marker_partial"
  if [[ -d "$publish" && "$publish" == "$backup_root"/.20*T*Z.partial ]]; then
    find "$publish" -xdev -type f -delete 2>/dev/null || true
    find "$publish" -depth -type d -empty -delete 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'printf "N8N_RECOVERY_BACKUP=FAIL\n" >&2' ERR

install -d -m 0700 "$publish" "$work/database" "$work/volumes" "$work/secrets" "$work/workflows" "$work/credentials" "$work/config" "$work/runtime"
gpg --homedir "$gpg_home" --batch --list-keys "$gpg_recipient" >/dev/null
gpg --homedir "$gpg_home" --batch --list-secret-keys "$CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT" >/dev/null

production_image_ref=$(docker inspect -f '{{.Config.Image}}' codestra-n8n-1)
[[ "$production_image_ref" == *@"$CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST" ]] || {
  printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=production_image_digest_mismatch\n' >&2
  exit 1
}
for container in codestra-n8n-staging-n8n-1 codestra-n8n-staging-webhook-1 codestra-n8n-staging-worker-1 codestra-n8n-staging-worker-2-1; do
  staging_image_ref=$(docker inspect -f '{{.Config.Image}}' "$container")
  [[ "$staging_image_ref" == *@"$CODESTRA_N8N_STAGING_IMAGE_DIGEST" ]] || {
    printf 'N8N_RECOVERY_BACKUP=FAIL\nERROR=staging_image_digest_mismatch\n' >&2
    exit 1
  }
done

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
docker image inspect "n8nio/n8n@$CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST" "n8nio/n8n@$CODESTRA_N8N_STAGING_IMAGE_DIGEST" > "$work/runtime/images.json"

(
  cd "$work"
  # The output file is excluded from find before the pipeline writes it.
  # shellcheck disable=SC2094
  find . -type f ! -name PLAINTEXT-SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > PLAINTEXT-SHA256SUMS
  sha256sum -c PLAINTEXT-SHA256SUMS >/dev/null
  tar -czf "$archive" .
)
gpg --homedir "$gpg_home" --no-random-seed-file --batch --yes --trust-model always --recipient "$gpg_recipient" --encrypt --output "$publish/n8n-recovery-$stamp.tar.gz.gpg" "$archive"
cat > "$publish/STATUS.txt" <<EOF
RECOVERY_CAPTURE=PASS
TIMESTAMP=$stamp
RELEASE_SHA=$CODESTRA_RELEASE_SHA
PRODUCTION_IMAGE_DIGEST=$CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST
STAGING_IMAGE_DIGEST=$CODESTRA_N8N_STAGING_IMAGE_DIGEST
SIGNING_FINGERPRINT=$CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT
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
(
  cd "$publish"
  sha256sum "n8n-recovery-$stamp.tar.gz.gpg" STATUS.txt > SIGNED-MANIFEST
  gpg --homedir "$gpg_home" --batch --yes --local-user "$CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT" \
    --detach-sign --output SIGNED-MANIFEST.sig SIGNED-MANIFEST
  sha256sum "n8n-recovery-$stamp.tar.gz.gpg" STATUS.txt SIGNED-MANIFEST SIGNED-MANIFEST.sig > SHA256SUMS
  sha256sum -c SHA256SUMS >/dev/null
)
chmod 0600 "$publish"/*
sync "$publish/n8n-recovery-$stamp.tar.gz.gpg" "$publish/STATUS.txt" "$publish/SIGNED-MANIFEST" "$publish/SIGNED-MANIFEST.sig" "$publish/SHA256SUMS"
sync -d "$publish"
mv "$publish" "$final"
sync -d "$backup_root"
marker_partial="$backup_root/.LAST_SUCCESS-$stamp"
printf '%s\n' "$stamp" >"$marker_partial"
chmod 0600 "$marker_partial"
sync "$marker_partial"
mv "$marker_partial" "$backup_root/LAST_SUCCESS"
sync -d "$backup_root"

mapfile -t complete_recoveries < <(
  find "$backup_root" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' |
    grep -E '^20[0-9]{6}T[0-9]{6}Z$' |
    sort -r |
    while IFS= read -r directory; do
      evidence_dir="$backup_root/$directory"
      [[ -f "$evidence_dir/SIGNED-MANIFEST" && ! -L "$evidence_dir/SIGNED-MANIFEST" ]] || continue
      [[ -f "$evidence_dir/SIGNED-MANIFEST.sig" && ! -L "$evidence_dir/SIGNED-MANIFEST.sig" ]] || continue
      signature_status=$(gpg --homedir "$gpg_home" --batch --status-fd=1 --verify \
        "$evidence_dir/SIGNED-MANIFEST.sig" "$evidence_dir/SIGNED-MANIFEST" 2>/dev/null) || continue
      valid_fingerprint=$(awk '$1 == "[GNUPG:]" && $2 == "VALIDSIG" {print toupper($3)}' <<<"$signature_status")
      [[ "$valid_fingerprint" == "$CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT" ]] || continue
      (cd "$evidence_dir" && sha256sum -c SIGNED-MANIFEST >/dev/null 2>&1) || continue
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
