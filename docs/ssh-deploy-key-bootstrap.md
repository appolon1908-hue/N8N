# Read-only GitHub deploy-key bootstrap

This procedure creates a repository-specific ED25519 key on the target server and registers only the public key with `appolon1908-hue/N8N`. It does not clone code, change an existing checkout, restart a service, import an n8n workflow, or deploy an application.

## Security properties

- The private key is generated on the target host and is never printed or uploaded.
- GitHub receives the `.pub` value with `read_only=true`.
- The key is scoped to one repository. Do not reuse it for another repository.
- SSH uses a dedicated host alias, key file, and known-hosts file.
- `IdentitiesOnly yes`, strict host-key checking, no password authentication, and no agent forwarding are enforced.
- GitHub's scanned ED25519 host key must match its published fingerprint before it is trusted.
- Existing key files and symbolic links are not overwritten.
- The script validates SSH authentication and `git ls-remote` only.

## Prerequisites

Run as the Unix account that will perform future read-only Git operations. The host needs `bash`, `gh`, `git`, `jq`, and OpenSSH client tools. `gh auth status --hostname github.com` must succeed with repository-administration permission long enough to add a deploy key. Remove that broad API credential from the server after the deploy key is verified if it is not otherwise required.

## Run from the infrastructure branch

```bash
set -Eeuo pipefail
TMP_SCRIPT="$(mktemp)"
gh api \
  -H 'Accept: application/vnd.github.raw+json' \
  'repos/appolon1908-hue/N8N/contents/ops/bootstrap_github_deploy_key.sh?ref=infra/ssh-deploy-key-bootstrap' \
  >"$TMP_SCRIPT"
chmod 0700 "$TMP_SCRIPT"
bash -n "$TMP_SCRIPT"
REPOSITORY='appolon1908-hue/N8N' bash "$TMP_SCRIPT"
rm -f "$TMP_SCRIPT"
```

The expected final output includes:

```text
SSH_DEPLOY_KEY_BOOTSTRAP=PASS
DEPLOY_KEY_MODE=READ_ONLY
LIVE_APPLICATION_DEPLOYMENT=NO
```

## Use the key

The script prints the repository-specific URL:

```text
git@github-n8n-readonly:appolon1908-hue/N8N.git
```

Validate it again without changing a checkout:

```bash
git ls-remote git@github-n8n-readonly:appolon1908-hue/N8N.git HEAD
```

Do not change a production checkout remote until its actual path and ownership are verified by the separate runtime-path audit.

## Revoke

Delete the deploy key from the repository's **Settings → Deploy keys**, then remove the dedicated private/public key files, SSH alias file, and dedicated known-hosts file from the server. Review deploy keys periodically and remove obsolete keys.
