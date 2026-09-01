#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

fail() { printf 'N8N_RESTORE_VERIFICATION=FAIL\nERROR=%s\n' "$*" >&2; exit 1; }
[[ $# -eq 1 ]] || fail "usage: verify-n8n-recovery.sh /absolute/recovery/directory"
recovery_dir=$1
[[ "$recovery_dir" == /* && -d "$recovery_dir" && ! -L "$recovery_dir" ]] || fail "recovery directory must be absolute and real"
stamp=$(basename -- "$recovery_dir")
[[ "$stamp" =~ ^20[0-9]{6}T[0-9]{6}Z$ ]] || fail "invalid recovery directory stamp"

required_env=(CODESTRA_DATABASE_BACKUP_GPG_HOME N8N_PRODUCTION_RESTORE_URL N8N_PRODUCTION_RESTORE_PGPASSFILE N8N_STAGING_RESTORE_URL N8N_STAGING_RESTORE_PGPASSFILE N8N_RESTORE_EVIDENCE_DIR)
for name in "${required_env[@]}"; do [[ -n "${!name:-}" ]] || fail "missing required setting: $name"; done
[[ "${ALLOW_ISOLATED_N8N_RESTORE:-false}" == "true" ]] || fail "isolated restore requires explicit authorization"
for command_name in gpg sha256sum python3 pg_restore psql install flock sync date mv stat id basename; do
  command -v "$command_name" >/dev/null || fail "missing command: $command_name"
done
[[ "$CODESTRA_DATABASE_BACKUP_GPG_HOME" == /* && -d "$CODESTRA_DATABASE_BACKUP_GPG_HOME" && ! -L "$CODESTRA_DATABASE_BACKUP_GPG_HOME" ]] || fail "GPG home must be absolute and real"
case "$(stat -c '%a' "$CODESTRA_DATABASE_BACKUP_GPG_HOME")" in 700) ;; *) fail "GPG home mode must be 0700" ;; esac
[[ "$(stat -c '%u' "$CODESTRA_DATABASE_BACKUP_GPG_HOME")" == "$(id -u)" ]] || fail "GPG home owner mismatch"

archive_name="n8n-recovery-$stamp.tar.gz.gpg"
archive="$recovery_dir/$archive_name"
for file in "$archive" "$recovery_dir/SHA256SUMS" "$recovery_dir/STATUS.txt" "$recovery_dir/EVIDENCE-SHA256SUMS"; do
  [[ -f "$file" && ! -L "$file" ]] || fail "recovery evidence is incomplete"
done
read -r archive_digest recorded_archive extra <"$recovery_dir/SHA256SUMS" || fail "archive checksum is unreadable"
[[ "$archive_digest" =~ ^[0-9a-f]{64}$ && "$recorded_archive" == "$archive_name" && -z "${extra:-}" ]] || fail "archive checksum is not bound"
[[ "$(sha256sum -- "$archive" | awk '{print $1}')" == "$archive_digest" ]] || fail "archive checksum failed"
read -r status_digest recorded_status extra <"$recovery_dir/EVIDENCE-SHA256SUMS" || fail "status checksum is unreadable"
[[ "$status_digest" =~ ^[0-9a-f]{64}$ && "$recorded_status" == "STATUS.txt" && -z "${extra:-}" ]] || fail "status checksum is not bound"
[[ "$(sha256sum -- "$recovery_dir/STATUS.txt" | awk '{print $1}')" == "$status_digest" ]] || fail "status checksum failed"
grep -qx 'RECOVERY_CAPTURE=PASS' "$recovery_dir/STATUS.txt" || fail "recovery capture is not successful"

status_value() { sed -n "s/^$1=//p" "$recovery_dir/STATUS.txt"; }
release_sha=$(status_value RELEASE_SHA)
production_image_digest=$(status_value PRODUCTION_IMAGE_DIGEST)
staging_image_digest=$(status_value STAGING_IMAGE_DIGEST)
[[ "$release_sha" =~ ^[0-9a-f]{40}$ ]] || fail "recovery release SHA is not immutable"
[[ "$production_image_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "production image digest is not immutable"
[[ "$staging_image_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "staging image digest is not immutable"

for passfile in "$N8N_PRODUCTION_RESTORE_PGPASSFILE" "$N8N_STAGING_RESTORE_PGPASSFILE"; do
  [[ "$passfile" == /* && -f "$passfile" && ! -L "$passfile" ]] || fail "restore passfile must be absolute and real"
  case "$(stat -c '%a' "$passfile")" in 400|600) ;; *) fail "restore passfile mode must be 0400 or 0600" ;; esac
  [[ "$(stat -c '%u' "$passfile")" == "$(id -u)" ]] || fail "restore passfile owner mismatch"
done

readarray -t restore_databases < <(python3 - <<'PY'
import os
from urllib.parse import parse_qsl, urlsplit

overrides = {"dbname", "database", "host", "hostaddr", "port", "user", "service"}
for name in ("N8N_PRODUCTION_RESTORE_URL", "N8N_STAGING_RESTORE_URL"):
    parsed = urlsplit(os.environ[name])
    keys = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    valid = (
        parsed.scheme in {"postgres", "postgresql"}
        and parsed.username is not None
        and parsed.password is None
        and parsed.hostname is not None
        and parsed.path not in {"", "/"}
        and parsed.fragment == ""
        and not any("password" in key or "passfile" in key for key in keys)
        and keys.isdisjoint(overrides)
    )
    if not valid:
        raise SystemExit(f"invalid credential-free restore URL: {name}")
    print(parsed.path.lstrip("/"))
PY
) || fail "restore URL validation failed"
[[ ${#restore_databases[@]} -eq 2 ]] || fail "restore URL identity extraction failed"
production_target=${restore_databases[0]}
staging_target=${restore_databases[1]}
[[ "$production_target" =~ (^|_)restore(_|$) && "$production_target" != "codestra_n8n" && "$production_target" != "n8n_staging" ]] || fail "production restore target is not isolated"
[[ "$staging_target" =~ (^|_)restore(_|$) && "$staging_target" != "codestra_n8n" && "$staging_target" != "n8n_staging" ]] || fail "staging restore target is not isolated"
[[ "$production_target" != "$staging_target" ]] || fail "restore targets must be distinct"

work=$(mktemp -d)
cleanup() { find "$work" -mindepth 1 -delete 2>/dev/null || true; rmdir "$work" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
gpg --homedir "$CODESTRA_DATABASE_BACKUP_GPG_HOME" --batch --quiet --decrypt --output "$work/recovery.tar.gz" "$archive"
mkdir "$work/content"
python3 - "$work/recovery.tar.gz" "$work/content" <<'PY' || fail "unsafe or invalid recovery archive"
import pathlib, sys, tarfile
archive, destination = sys.argv[1:]
with tarfile.open(archive, "r:gz") as bundle:
    members = bundle.getmembers()
    if not members:
        raise SystemExit("empty archive")
    for member in members:
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
            raise SystemExit("unsafe archive member")
    bundle.extractall(destination, filter="data")
PY
for file in database/production.dump database/staging.dump volumes/production-n8n-data.tar.gz volumes/staging-n8n-data.tar.gz secrets/production-n8n-encryption-key secrets/staging-n8n-encryption-key workflows/production.json workflows/staging.json PLAINTEXT-SHA256SUMS; do
  [[ -f "$work/content/$file" && ! -L "$work/content/$file" ]] || fail "required recovery artifact is missing: $file"
done
(cd "$work/content" && sha256sum -c PLAINTEXT-SHA256SUMS >/dev/null) || fail "plaintext artifact checksum failed"
python3 - "$work/content/workflows/production.json" "$work/content/workflows/staging.json" "$work/content/volumes/production-n8n-data.tar.gz" "$work/content/volumes/staging-n8n-data.tar.gz" <<'PY' || fail "workflow or volume artifact validation failed"
import json, pathlib, sys, tarfile
for filename in sys.argv[1:3]:
    value = json.loads(pathlib.Path(filename).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise SystemExit("workflow export must be an array")
for filename in sys.argv[3:]:
    with tarfile.open(filename, "r:gz") as bundle:
        members = bundle.getmembers()
        if not members:
            raise SystemExit("empty volume archive")
        for member in members:
            path = pathlib.PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise SystemExit("unsafe volume archive member")
PY

verify_database() {
  local url=$1 passfile=$2 dump=$3 label=$4
  local before required
  before=$(PGPASSFILE="$passfile" psql "$url" -XAtq -v ON_ERROR_STOP=1 -c "select count(*) from information_schema.tables where table_schema='public';")
  [[ "$before" == "0" ]] || fail "$label restore database must be empty"
  pg_restore --list "$dump" >/dev/null || fail "$label dump inventory failed"
  PGPASSFILE="$passfile" pg_restore --dbname="$url" --no-owner --no-acl --exit-on-error "$dump"
  required=$(PGPASSFILE="$passfile" psql "$url" -XAtq -v ON_ERROR_STOP=1 -c "select count(*) from information_schema.tables where table_schema='public' and table_name in ('workflow_entity','credentials_entity','migrations');")
  [[ "$required" == "3" ]] || fail "$label required n8n schema verification failed"
}
verify_database "$N8N_PRODUCTION_RESTORE_URL" "$N8N_PRODUCTION_RESTORE_PGPASSFILE" "$work/content/database/production.dump" production
verify_database "$N8N_STAGING_RESTORE_URL" "$N8N_STAGING_RESTORE_PGPASSFILE" "$work/content/database/staging.dump" staging

install -d -m 0700 "$N8N_RESTORE_EVIDENCE_DIR"
exec 8>"$N8N_RESTORE_EVIDENCE_DIR/.restore.lock"
flock -n 8 || fail "another restore verification is publishing evidence"
result_name="RESTORE-RESULT-$stamp"
result="$N8N_RESTORE_EVIDENCE_DIR/$result_name"
partial="$N8N_RESTORE_EVIDENCE_DIR/.$result_name.partial"
checksum_partial="$N8N_RESTORE_EVIDENCE_DIR/.$result_name.sha256.partial"
[[ ! -e "$result" && ! -e "$result.sha256" && ! -e "$partial" && ! -e "$checksum_partial" ]] || fail "restore evidence collision"
trap 'cleanup; rm -f -- "${partial:-}" "${checksum_partial:-}" "${marker_partial:-}"' EXIT INT TERM
cat >"$partial" <<EOF
SCHEMA=codestra-n8n-restore-result.v1
STAMP=$stamp
BACKUP_SHA256=$archive_digest
RELEASE_SHA=$release_sha
PRODUCTION_IMAGE_DIGEST=$production_image_digest
STAGING_IMAGE_DIGEST=$staging_image_digest
TARGET_CLASS=ISOLATED
PRODUCTION_SCHEMA=PASS
STAGING_SCHEMA=PASS
WORKFLOWS=PASS
VOLUMES=PASS
ENCRYPTION_KEYS=PRESENT_NOT_EXPOSED
RESTORE=PASS
EOF
sync "$partial"
mv "$partial" "$result"
sync "$result"
printf '%s  %s\n' "$(sha256sum -- "$result" | awk '{print $1}')" "$result_name" >"$checksum_partial"
sync "$checksum_partial"
mv "$checksum_partial" "$result.sha256"
sync "$result.sha256"
marker_partial="$N8N_RESTORE_EVIDENCE_DIR/.LAST_SUCCESS-$stamp"
printf '%s\n' "$stamp" >"$marker_partial"
sync "$marker_partial"
mv "$marker_partial" "$N8N_RESTORE_EVIDENCE_DIR/LAST_SUCCESS"
sync "$N8N_RESTORE_EVIDENCE_DIR/LAST_SUCCESS"
sync -d "$N8N_RESTORE_EVIDENCE_DIR"
trap cleanup EXIT INT TERM
printf 'N8N_RESTORE_VERIFICATION=PASS\nRESTORE_EVIDENCE=%s\n' "$result"
