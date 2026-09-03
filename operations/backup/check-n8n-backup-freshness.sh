#!/usr/bin/env bash
set -Eeuo pipefail
fail() { printf 'N8N_BACKUP_FRESHNESS=FAIL\nERROR=%s\n' "$*" >&2; exit 1; }
[[ $# -eq 2 ]] || fail "usage: check-n8n-backup-freshness.sh /absolute/backup/directory MAX_AGE_SECONDS"
root=$1
max_age=$2
: "${CODESTRA_DATABASE_BACKUP_GPG_HOME:?CODESTRA_DATABASE_BACKUP_GPG_HOME is required}"
: "${CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT:?CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT is required}"
[[ "$root" == /* && -d "$root" && ! -L "$root" ]] || fail "backup directory must be absolute and real"
[[ "$max_age" =~ ^[1-9][0-9]*$ ]] || fail "maximum age must be a positive integer"
[[ "$CODESTRA_DATABASE_BACKUP_GPG_HOME" == /* && -d "$CODESTRA_DATABASE_BACKUP_GPG_HOME" && ! -L "$CODESTRA_DATABASE_BACKUP_GPG_HOME" ]] || fail "GPG home must be absolute and real"
[[ "$CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT" =~ ^[A-Fa-f0-9]{40}$ ]] || fail "backup signing fingerprint is invalid"
signer=${CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT^^}
[[ -f "$root/LAST_SUCCESS" && ! -L "$root/LAST_SUCCESS" ]] || fail "success marker is missing"
stamp=$(tr -d '\r\n' <"$root/LAST_SUCCESS")
[[ "$stamp" =~ ^20[0-9]{6}T[0-9]{6}Z$ ]] || fail "invalid success marker"
artifact="$root/$stamp"
archive_name="n8n-recovery-$stamp.tar.gz.gpg"
for name in "$archive_name" STATUS.txt SIGNED-MANIFEST SIGNED-MANIFEST.sig SHA256SUMS; do
  [[ -f "$artifact/$name" && ! -L "$artifact/$name" ]] || fail "backup evidence is incomplete"
done
(cd "$artifact" && sha256sum -c SHA256SUMS >/dev/null) || fail "backup checksum failed"
signature_status=$(gpg --homedir "$CODESTRA_DATABASE_BACKUP_GPG_HOME" --batch --status-fd=1 --verify "$artifact/SIGNED-MANIFEST.sig" "$artifact/SIGNED-MANIFEST" 2>/dev/null) || fail "backup signature verification failed"
valid_fingerprint=$(awk '$1 == "[GNUPG:]" && $2 == "VALIDSIG" {print toupper($3)}' <<<"$signature_status")
[[ "$valid_fingerprint" == "$signer" ]] || fail "backup signing identity mismatch"
(cd "$artifact" && sha256sum -c SIGNED-MANIFEST >/dev/null) || fail "signed manifest verification failed"
status_value() { sed -n "s/^$1=//p" "$artifact/STATUS.txt"; }
[[ "$(status_value RECOVERY_CAPTURE)" == PASS ]] || fail "recovery capture did not pass"
[[ "$(status_value TIMESTAMP)" == "$stamp" ]] || fail "backup marker does not match signed status"
[[ "$(status_value SIGNING_FINGERPRINT)" == "$signer" ]] || fail "status signing identity mismatch"
[[ "$(status_value RELEASE_SHA)" =~ ^[0-9a-f]{40}$ ]] || fail "release SHA is invalid"
[[ "$(status_value PRODUCTION_IMAGE_DIGEST)" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "production image digest is invalid"
[[ "$(status_value STAGING_IMAGE_DIGEST)" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "staging image digest is invalid"
stamp_iso="${stamp:0:4}-${stamp:4:2}-${stamp:6:2}T${stamp:9:2}:${stamp:11:2}:${stamp:13:2}Z"
age=$(( $(date -u +%s) - $(date -u -d "$stamp_iso" +%s) ))
(( age >= -300 && age <= max_age )) || fail "backup evidence is stale or future-dated"
printf 'N8N_BACKUP_FRESHNESS=PASS\nBACKUP_AGE_SECONDS=%s\n' "$age"
