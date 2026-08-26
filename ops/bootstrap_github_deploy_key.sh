#!/usr/bin/env bash
# Generate and register a repository-scoped, read-only GitHub deploy key.
# The private key is created on this host and is never printed or uploaded.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

REPOSITORY="${REPOSITORY:-appolon1908-hue/N8N}"
HOST_ALIAS="${HOST_ALIAS:-github-n8n-readonly}"
SSH_DIRECTORY="${SSH_DIRECTORY:-${HOME}/.ssh}"
KEY_PATH="${KEY_PATH:-${SSH_DIRECTORY}/n8n_readonly_deploy_ed25519}"
PUBLIC_KEY_PATH="${KEY_PATH}.pub"
CONFIG_DIRECTORY="${SSH_DIRECTORY}/config.d"
CONFIG_PATH="${CONFIG_DIRECTORY}/n8n-readonly.conf"
MAIN_CONFIG_PATH="${SSH_DIRECTORY}/config"
KNOWN_HOSTS_PATH="${SSH_DIRECTORY}/known_hosts.github-n8n"
EXPECTED_GITHUB_ED25519_FINGERPRINT="SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU"
API_VERSION="2026-03-10"

fail() {
  printf 'ERROR=%s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

for command_name in gh git jq ssh ssh-keygen ssh-keyscan; do
  require_command "$command_name"
done

[[ "$REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] \
  || fail "REPOSITORY must use owner/name syntax"
[[ "$HOST_ALIAS" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] \
  || fail "HOST_ALIAS contains unsupported characters"
[[ "$KEY_PATH" = /* ]] || fail "KEY_PATH must be absolute"
[[ "$SSH_DIRECTORY" = /* ]] || fail "SSH_DIRECTORY must be absolute"

printf 'TARGET_REPOSITORY=%s\n' "$REPOSITORY"
printf 'TARGET_HOSTNAME=%s\n' "$(hostname -f 2>/dev/null || hostname)"
printf 'TARGET_USER=%s\n' "$(id -un)"
printf 'LIVE_APPLICATION_DEPLOYMENT=NO\n'

install -d -m 0700 "$SSH_DIRECTORY" "$CONFIG_DIRECTORY"
for protected_path in "$PUBLIC_KEY_PATH" "$CONFIG_PATH" "$MAIN_CONFIG_PATH" "$KNOWN_HOSTS_PATH"; do
  [[ ! -L "$protected_path" ]] || fail "refusing to use symbolic link: $protected_path"
done

if [[ -e "$KEY_PATH" ]]; then
  [[ -f "$KEY_PATH" && ! -L "$KEY_PATH" ]] || fail "existing key path is not a regular file"
  if [[ ! -e "$PUBLIC_KEY_PATH" ]]; then
    ssh-keygen -y -f "$KEY_PATH" >"$PUBLIC_KEY_PATH"
  fi
else
  [[ ! -e "$PUBLIC_KEY_PATH" ]] || fail "public key exists without its private key"
  ssh-keygen \
    -q \
    -t ed25519 \
    -N '' \
    -C "deploy:${REPOSITORY}@$(hostname -f 2>/dev/null || hostname)" \
    -f "$KEY_PATH"
fi

chmod 0600 "$KEY_PATH"
chmod 0644 "$PUBLIC_KEY_PATH"
[[ "$(ssh-keygen -y -f "$KEY_PATH")" = "$(cut -d' ' -f1-2 "$PUBLIC_KEY_PATH")" ]] \
  || fail "private and public deploy key files do not match"

PUBLIC_KEY="$(cat "$PUBLIC_KEY_PATH")"
[[ "$PUBLIC_KEY" == ssh-ed25519\ * ]] || fail "deploy key must be ED25519"
KEY_FINGERPRINT="$(ssh-keygen -lf "$PUBLIC_KEY_PATH" -E sha256 | awk '{print $2}')"
[[ "$KEY_FINGERPRINT" == SHA256:* ]] || fail "unable to calculate deploy-key fingerprint"

SCAN_PATH="$(mktemp "${SSH_DIRECTORY}/github-host-key.XXXXXX")"
API_RESPONSE_PATH="$(mktemp "${SSH_DIRECTORY}/github-api-response.XXXXXX")"
cleanup() {
  rm -f "$SCAN_PATH" "$API_RESPONSE_PATH"
}
trap cleanup EXIT

GITHUB_HOST="github.com"
GITHUB_PORT="22"
if ! ssh-keyscan -T 10 -t ed25519 github.com >"$SCAN_PATH" 2>/dev/null; then
  GITHUB_HOST="ssh.github.com"
  GITHUB_PORT="443"
  ssh-keyscan -T 10 -p 443 -t ed25519 ssh.github.com >"$SCAN_PATH" 2>/dev/null \
    || fail "unable to obtain GitHub's ED25519 host key on ports 22 or 443"
fi

SCANNED_FINGERPRINTS="$(ssh-keygen -lf "$SCAN_PATH" -E sha256 | awk '{print $2}' | sort -u)"
[[ "$SCANNED_FINGERPRINTS" = "$EXPECTED_GITHUB_ED25519_FINGERPRINT" ]] \
  || fail "GitHub host-key fingerprint mismatch: ${SCANNED_FINGERPRINTS}"
install -m 0600 "$SCAN_PATH" "$KNOWN_HOSTS_PATH"

cat >"$CONFIG_PATH" <<EOF_CONFIG
Host ${HOST_ALIAS}
  HostName ${GITHUB_HOST}
  Port ${GITHUB_PORT}
  User git
  IdentityFile ${KEY_PATH}
  IdentitiesOnly yes
  PreferredAuthentications publickey
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  StrictHostKeyChecking yes
  UserKnownHostsFile ${KNOWN_HOSTS_PATH}
  ForwardAgent no
EOF_CONFIG
chmod 0600 "$CONFIG_PATH"

INCLUDE_LINE="Include ${CONFIG_DIRECTORY}/*"
touch "$MAIN_CONFIG_PATH"
chmod 0600 "$MAIN_CONFIG_PATH"
UPDATED_CONFIG="$(mktemp "${SSH_DIRECTORY}/config.XXXXXX")"
{
  printf '%s\n\n' "$INCLUDE_LINE"
  grep -Fvx "$INCLUDE_LINE" "$MAIN_CONFIG_PATH" || true
} >"$UPDATED_CONFIG"
chmod 0600 "$UPDATED_CONFIG"
mv -f "$UPDATED_CONFIG" "$MAIN_CONFIG_PATH"
ssh -F "$MAIN_CONFIG_PATH" -G "$HOST_ALIAS" >/dev/null \
  || fail "generated SSH configuration is invalid"

gh auth status --hostname github.com >/dev/null 2>&1 \
  || fail "GitHub CLI is not authenticated on this host"

gh api \
  -H 'Accept: application/vnd.github+json' \
  -H "X-GitHub-Api-Version: ${API_VERSION}" \
  "repos/${REPOSITORY}/keys?per_page=100" >"$API_RESPONSE_PATH"

if jq -e --arg key "$PUBLIC_KEY" 'any(.[]; .key == $key)' "$API_RESPONSE_PATH" >/dev/null; then
  printf 'GITHUB_DEPLOY_KEY=ALREADY_PRESENT\n'
else
  FINGERPRINT_SUFFIX="$(printf '%s' "${KEY_FINGERPRINT#SHA256:}" | tr '/+' '_-' | cut -c1-16)"
  KEY_TITLE="N8N read-only deploy key - $(hostname -s) - ${FINGERPRINT_SUFFIX}"
  gh api \
    --method POST \
    -H 'Accept: application/vnd.github+json' \
    -H "X-GitHub-Api-Version: ${API_VERSION}" \
    "repos/${REPOSITORY}/keys" \
    -f "title=${KEY_TITLE}" \
    -f "key=${PUBLIC_KEY}" \
    -F read_only=true >"$API_RESPONSE_PATH"
  [[ "$(jq -r '.read_only' "$API_RESPONSE_PATH")" = "true" ]] \
    || fail "GitHub did not record the deploy key as read-only"
  printf 'GITHUB_DEPLOY_KEY=CREATED_READ_ONLY\n'
fi

set +e
SSH_RESULT="$(ssh -F "$MAIN_CONFIG_PATH" -o BatchMode=yes -o ConnectTimeout=15 -T "$HOST_ALIAS" 2>&1)"
SSH_STATUS=$?
set -e
if ! grep -Fq "successfully authenticated" <<<"$SSH_RESULT"; then
  printf '%s\n' "$SSH_RESULT" >&2
  fail "GitHub SSH authentication did not return the expected success message (status ${SSH_STATUS})"
fi

GIT_SSH_COMMAND="ssh -F \"${MAIN_CONFIG_PATH}\" -o BatchMode=yes -o ConnectTimeout=15" \
  git ls-remote "git@${HOST_ALIAS}:${REPOSITORY}.git" HEAD >/dev/null

printf 'SSH_DEPLOY_KEY_BOOTSTRAP=PASS\n'
printf 'DEPLOY_KEY_MODE=READ_ONLY\n'
printf 'DEPLOY_KEY_FINGERPRINT=%s\n' "$KEY_FINGERPRINT"
printf 'PRIVATE_KEY_PATH=%s\n' "$KEY_PATH"
printf 'PUBLIC_KEY_PATH=%s\n' "$PUBLIC_KEY_PATH"
printf 'SSH_HOST_ALIAS=%s\n' "$HOST_ALIAS"
printf 'GIT_REMOTE_URL=git@%s:%s.git\n' "$HOST_ALIAS" "$REPOSITORY"
printf 'LIVE_APPLICATION_DEPLOYMENT=NO\n'
