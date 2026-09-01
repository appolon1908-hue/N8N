#!/usr/bin/env bash
set -Eeuo pipefail
fail() { printf 'N8N_RECOVERY_FRESHNESS=FAIL\nERROR=%s\n' "$*" >&2; exit 1; }
[[ $# -eq 2 ]] || fail "usage: check-n8n-recovery-freshness.sh /absolute/evidence/directory MAX_AGE_SECONDS"
root=$1
max_age=$2
[[ "$root" == /* && -d "$root" && ! -L "$root" ]] || fail "evidence directory must be absolute and real"
[[ "$max_age" =~ ^[1-9][0-9]*$ ]] || fail "maximum age must be a positive integer"
[[ -f "$root/LAST_SUCCESS" && ! -L "$root/LAST_SUCCESS" ]] || fail "success marker is missing"
stamp=$(tr -d '\r\n' <"$root/LAST_SUCCESS")
[[ "$stamp" =~ ^20[0-9]{6}T[0-9]{6}Z$ ]] || fail "invalid success marker"
name="RESTORE-RESULT-$stamp"
[[ -f "$root/$name" && ! -L "$root/$name" && -f "$root/$name.sha256" && ! -L "$root/$name.sha256" ]] || fail "restore evidence is incomplete"
read -r digest recorded extra <"$root/$name.sha256" || fail "checksum is unreadable"
[[ "$digest" =~ ^[0-9a-f]{64}$ && "$recorded" == "$name" && -z "${extra:-}" ]] || fail "checksum is not bound"
[[ "$(sha256sum -- "$root/$name" | awk '{print $1}')" == "$digest" ]] || fail "checksum failed"
grep -qx 'RESTORE=PASS' "$root/$name" || fail "restore did not pass"
stamp_iso="${stamp:0:4}-${stamp:4:2}-${stamp:6:2}T${stamp:9:2}:${stamp:11:2}:${stamp:13:2}Z"
age=$(( $(date -u +%s) - $(date -u -d "$stamp_iso" +%s) ))
(( age >= -300 && age <= max_age )) || fail "restore evidence is stale or future-dated"
printf 'N8N_RECOVERY_FRESHNESS=PASS\nRESTORE_AGE_SECONDS=%s\n' "$age"
