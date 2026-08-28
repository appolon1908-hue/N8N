# N8N server capture — 2026-08-28

This directory is a read-only capture of the live production and staging n8n
runtime on the Codestra middleware host. It was created on the unmerged branch
`import/server-n8n-20260828` before any n8n image upgrade or production
workflow activation.

## Capture identity

- Production n8n version: `2.30.8`
- Staging n8n version: `2.30.8`
- Image digest: `sha256:11524034450080bd0032754892b23ff20be43d72cf320ce75640f7c5475fdca8`
- Production workflows: 130 total, 1 active
- Staging workflows: 327 total, 11 active
- Production credential records: 4 metadata-only records
- Staging credential records: 9 metadata-only records
- Previous source authority main: `Codestra-SRL/codestra-n8n-workflows@5b7e7ba5e0e719194fb6a3fca1c1b05e80de7bee`
- New repository starting main: `appolon1908-hue/N8N@e89ed696635edff615e69abb7c1fac94c590aeac`

## Security treatment

No credential payload, database password, encryption key, API key, OAuth
token, SMTP password, or decrypted secret is stored here. Container environment
evidence contains key names only. Credential evidence contains names, types,
project ownership, roles, and timestamps only.

The staging export contained 150 hard-coded Authorization fields across 75
workflows and two nodes per workflow. Their values were replaced with
`<redacted-live-authorization-value>`. The affected workflow and node names are
listed in `workflows/staging.redactions.tsv`. The exact state exists only in the
encrypted recovery bundle outside Git.

Gitleaks' generic-key rule flags `idempotency_key` fixture text in the workflow
exports. Those 16 findings were reviewed as non-secret field names. No live
credential value is permitted in this branch.

## Evidence layout

- `workflows/`: sanitized full exports, active-state indexes, and redaction log
- `credentials/`: metadata only; never encrypted or decrypted credential data
- `config/`: deployed Compose and sanitized proxy configuration
- `runtime/`: image and container evidence with environment values removed
- `topology/`: PostgreSQL/Redis-facing Docker network membership and subnets
- `SHA256SUMS`: hashes of every capture artifact

This branch is evidence and reconciliation input. It must not be merged directly
into `main` as deployable workflow source.
