#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
fixture=$(mktemp -d)
trap 'rm -rf -- "$fixture"' EXIT
stamp=$(date -u +%Y%m%dT%H%M%SZ)
recovery="$fixture/$stamp"
content="$fixture/content"
mkdir -p "$fixture/bin" "$fixture/gpg" "$fixture/evidence" "$recovery" \
  "$content/database" "$content/volumes" "$content/secrets" "$content/workflows"
chmod 0700 "$fixture/gpg"
printf 'production-dump\n' >"$content/database/production.dump"
printf 'staging-dump\n' >"$content/database/staging.dump"
printf 'key\n' >"$content/secrets/production-n8n-encryption-key"
printf 'key\n' >"$content/secrets/staging-n8n-encryption-key"
printf '[]\n' >"$content/workflows/production.json"
printf '[]\n' >"$content/workflows/staging.json"
mkdir "$fixture/volume"
printf 'fixture\n' >"$fixture/volume/config"
tar -czf "$content/volumes/production-n8n-data.tar.gz" -C "$fixture/volume" .
tar -czf "$content/volumes/staging-n8n-data.tar.gz" -C "$fixture/volume" .
(cd "$content" && find . -type f ! -name PLAINTEXT-SHA256SUMS -print0 | sort -z | xargs -0 sha256sum >PLAINTEXT-SHA256SUMS)
tar -czf "$recovery/n8n-recovery-$stamp.tar.gz.gpg" -C "$content" .
(cd "$recovery" && sha256sum "n8n-recovery-$stamp.tar.gz.gpg" >SHA256SUMS)
cat >"$recovery/STATUS.txt" <<EOF
RECOVERY_CAPTURE=PASS
TIMESTAMP=$stamp
RELEASE_SHA=1111111111111111111111111111111111111111
PRODUCTION_IMAGE_DIGEST=sha256:$(printf '2%.0s' {1..64})
STAGING_IMAGE_DIGEST=sha256:$(printf '3%.0s' {1..64})
RESTORE_REHEARSAL=PENDING
EOF
(cd "$recovery" && sha256sum STATUS.txt >EVIDENCE-SHA256SUMS)

cat >"$fixture/bin/gpg" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
output=''
input=''
while (($#)); do
  case "$1" in --output) output=$2; shift 2 ;; --*) shift ;; *) input=$1; shift ;; esac
done
cp -- "$input" "$output"
SH
cat >"$fixture/bin/pg_restore" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
exit 0
SH
cat >"$fixture/bin/psql" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
count=0
[[ ! -f "$TEST_PSQL_COUNT" ]] || read -r count <"$TEST_PSQL_COUNT"
count=$((count + 1))
printf '%s\n' "$count" >"$TEST_PSQL_COUNT"
if ((count % 2 == 1)); then printf '0\n'; else printf '3\n'; fi
SH
chmod 0700 "$fixture/bin/gpg" "$fixture/bin/pg_restore" "$fixture/bin/psql"
printf 'fixture\n' >"$fixture/production.pgpass"
printf 'fixture\n' >"$fixture/staging.pgpass"
chmod 0600 "$fixture/production.pgpass" "$fixture/staging.pgpass"

export PATH="$fixture/bin:/usr/local/bin:/usr/bin:/bin"
export TEST_PSQL_COUNT="$fixture/psql.count"
export CODESTRA_DATABASE_BACKUP_GPG_HOME="$fixture/gpg"
export N8N_PRODUCTION_RESTORE_URL='postgresql://restore@isolated.internal:5432/codestra_n8n_restore'
export N8N_PRODUCTION_RESTORE_PGPASSFILE="$fixture/production.pgpass"
export N8N_STAGING_RESTORE_URL='postgresql://restore@isolated.internal:5432/n8n_staging_restore'
export N8N_STAGING_RESTORE_PGPASSFILE="$fixture/staging.pgpass"
export N8N_RESTORE_EVIDENCE_DIR="$fixture/evidence"
export ALLOW_ISOLATED_N8N_RESTORE=true

"$ROOT_DIR/operations/backup/verify-n8n-recovery.sh" "$recovery" >/dev/null
[[ "$(cat "$TEST_PSQL_COUNT")" == 4 ]]
"$ROOT_DIR/operations/backup/check-n8n-recovery-freshness.sh" "$N8N_RESTORE_EVIDENCE_DIR" 300 >/dev/null
result=$(find "$N8N_RESTORE_EVIDENCE_DIR" -maxdepth 1 -type f -name 'RESTORE-RESULT-*' ! -name '*.sha256' -print -quit)
printf 'tampered\n' >>"$result"
if "$ROOT_DIR/operations/backup/check-n8n-recovery-freshness.sh" "$N8N_RESTORE_EVIDENCE_DIR" 300 >/dev/null 2>&1; then
  printf 'ERROR=tampered_restore_evidence_was_accepted\n' >&2
  exit 1
fi

rm -f "$TEST_PSQL_COUNT"
export N8N_PRODUCTION_RESTORE_URL='postgresql://restore@isolated.internal:5432/codestra_n8n_restore?dbname=codestra_n8n'
if "$ROOT_DIR/operations/backup/verify-n8n-recovery.sh" "$recovery" >/dev/null 2>&1; then
  printf 'ERROR=database_override_was_accepted\n' >&2
  exit 1
fi
[[ ! -e "$TEST_PSQL_COUNT" ]]

printf 'N8N_RECOVERY_CONTRACT_TEST=PASS\n'
