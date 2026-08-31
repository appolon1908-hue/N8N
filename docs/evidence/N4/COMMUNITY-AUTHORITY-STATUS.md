# N4 community runtime authority status

Captured: `2026-08-30T20:40Z`
Deployment performed: `false`
Workflow activation performed: `false`
External effects enabled: `false`

## Merged source authority

- Keycloak PR 47: merge `76869680ff2f587e5f37fa67fdd95dc3c5eafba6`
- Kong PR 39: merge `14ee71d8d4c2ea6b7147f35be36e07b822683097`
- Kong PR 40: merge `95bb6308ed33704fc2d01d171c27a82552e73c9e`
- Caddy PR 12: merge `5dcc48e89e84627c6a122ed3d9429963e9b01869`
- Caddy PR 13: merge `74db25d0dd411e4dfa538e13750ad3da6e80fc6d`

The final contracts use the existing `n8n-automation` Client Credentials
identity, the existing `n8n_operator`/`n8n_admin` human roles, and a dedicated
confidential `n8n-editor-gateway` Authorization Code + PKCE client. Canonical
editor callbacks are under `codestra.co`, not the legacy-disabled
`codestra.agency` root.

## Validation

- Caddy complete configuration and repository authority: pass.
- Kong community route, firewall, manifests, and 121-test suite: pass.
- Keycloak exact source and synthetic merge-result validation: pass.
- Keycloak deterministic plan/apply/rollback/race rehearsal: pass.

## Staging blockers

1. Keycloak runtime-preflight run `33334205848` passed its merged-SHA guard but
   the required self-hosted `codestra-keycloak` inspection job remains queued.
   The repository currently reports zero registered Actions runners.
2. `n8n.codestra.co` and `n8n-staging.codestra.co` do not currently resolve.
3. Root-owned editor client/cookie secret files have not been provisioned or
   rotated, and the Keycloak desired-state plan has not been applied.
4. Caddy, Kong firewall, and n8n Compose changes have not been staged or
   restarted; rollback and negative-egress evidence therefore do not exist.

`config/n8n-policy.json` remains `UNVERIFIED`. These missing runtime facts may
not be replaced by source assertions. All workflows remain inactive.
