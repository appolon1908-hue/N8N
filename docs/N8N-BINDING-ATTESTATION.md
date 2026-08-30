# n8n binding attestation

`config/n8n-policy.json` is an attestation about a real deployment, not
configuration that changes behaviour. It stays `UNVERIFIED` in Git until two
named people have checked a running system and produced evidence.

`scripts/attest_n8n_policy.py` records that attestation. It computes every
evidence hash from a file on disk, so an attestation cannot be written from
values somebody typed. Missing or empty artifacts, a placeholder endpoint, or
one person acting as both verifier and reviewer all fail the run and leave the
policy untouched.

## Where each control is actually enforced

| Control | Enforcement point | State |
| --- | --- | --- |
| Dangerous-node exclusions | `NODES_EXCLUDE` in `deploy/compose/compose.staging.yml`, cross-checked against the policy by `scripts/policy_compose.py` | **Enforced in this repo** |
| Code node, public API, env access in nodes | `compose.staging.yml` environment, required by `policy_compose.py` | **Enforced in this repo** |
| Egress restriction | the external `middleware_network` | Attested, enforced outside this repo |
| Fixed HTTPS Middleware routing | `endpoint_binding.approved_base_url` | Attested |
| Dedicated service-owner credential | n8n credential store | Attested |
| Editor protection | `appolon1908-hue/Caddy` and `appolon1908-hue/Kong` | Attested, enforced outside this repo |

Only the first two rows are things this repository can enforce by itself. That
is deliberate, and it is why the remaining rows carry evidence hashes instead of
configuration.

## Egress

`scripts/policy_compose.py` requires every service to attach to exactly
`middleware_network` and to nothing else. There is therefore no second network
to add, and no place in this repository to express an egress rule. Egress is a
property of that network, which is provisioned externally.

The network must be created without external routing, for example:

```bash
docker network create --internal --driver bridge codestra-middleware
```

The egress artifact must show that the running n8n containers cannot reach an
arbitrary internet host and can reach the approved Middleware origin. Capture
the network inspection and both reachability attempts, from inside the running
container, in one file.

## Editor access

n8n Community Edition has no enterprise SSO, so the editor cannot be bound to
Keycloak on its own. The reviewed community-compatible strategy is
`verified-gateway-oidc-and-native-auth`:

1. Caddy refuses any source outside `CADDY_EDITOR_ADMIN_CIDRS`.
2. Kong performs the Keycloak authorization-code browser flow for the editor
   host. This is a browser flow, not the bearer-only method used for the
   service routes.
3. n8n's native owner login stays enabled behind the gateway, so a gateway
   bypass alone does not grant editor access.

The editor artifact must show an unauthenticated request being refused before it
reaches n8n. The session-policy artifact must show the session lifetime, idle
timeout, and cookie flags actually in force.

## Credentials

The service-owner credential is a dedicated n8n credential used only for
Middleware calls. It must not be the editor owner's personal login, and it must
not be an environment variable read by a node — `N8N_BLOCK_ENV_ACCESS_IN_NODE`
is already `true`, which blocks that route.

The credential artifact must show the credential's type and name and that no
other credential can reach the Middleware origin.

## Recording the attestation

Dry run first; the tool prints the policy it would write and validates it with
the same checker CI uses:

```bash
python3 scripts/attest_n8n_policy.py --edition "n8n Community Edition <version>" --verified-by "<verifier>" --independent-reviewer "<reviewer>" --approved-base-url "https://<middleware-host>" --endpoint-strategy verified-fixed-private-dns --credential-strategy verified-n8n-credential --credential-type httpHeaderAuth --credential-name codestra-middleware-service-owner --editor-strategy verified-gateway-oidc-and-native-auth --evidence evidence/overall.txt --egress-evidence evidence/egress.txt --credential-evidence evidence/credential.txt --editor-evidence evidence/editor.txt --session-policy-evidence evidence/session-policy.txt
```

Add `--write` once the dry run is correct. Keep the artifacts wherever your
evidence retention policy requires; the hashes in the policy are what tie the
attestation to them, so the files must not be edited afterwards.
