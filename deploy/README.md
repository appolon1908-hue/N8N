# Deployment scaffolding

This directory is intentionally non-applying.

- `compose/compose.staging.yml` is a hardened template that publishes no host port and requires externally provisioned secrets, PostgreSQL, Redis, middleware network, and an immutable image digest.
- `env/ci.env` contains non-secret syntax-validation values only.
- `env/staging.example.env` contains placeholders only.
- `manifests/release.example.json` documents the release evidence contract.
- The GitHub `deployment-preflight` workflow validates evidence and exits. It contains no remote connection or deploy command.

Do not run the Compose template against the live server until `config/runtime-paths.json` is verified and a separate deployment-implementation pull request is approved.
