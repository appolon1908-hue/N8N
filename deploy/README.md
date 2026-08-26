# Deployment scaffolding

This directory is intentionally non-applying.

- `compose/compose.staging.yml` is a hardened template that publishes no host port and requires externally provisioned secrets, PostgreSQL, Redis, a middleware network, and immutable image input.
- `env/ci.env` contains non-secret syntax-validation values only.
- `env/staging.example.env` contains placeholders only.
- `manifests/release.example.json` documents the fail-closed release evidence contract.
- The GitHub `deployment-preflight` workflow validates evidence and exits. It contains no remote connection or deploy command.

The template disables n8n's public API and API playground, blocks workflow access to environment variables and local n8n files, excludes dangerous nodes including Code and Execute Command, uses database binary-data mode because queue mode does not support filesystem binary storage, and gives each worker a local readiness probe for its database and Redis connections.

The middleware endpoint, credential, and editor-access bindings are deliberately unresolved. Templates use `middleware.invalid` with no credential reference; no routable endpoint or authentication profile is introduced until the n8n edition, private DNS/network path, egress policy, credential mechanism, and non-public editor access are verified.

Do not run the Compose template against the live server until `config/runtime-paths.json` and `config/n8n-policy.json` are verified and a separate deployment-implementation pull request is approved.
