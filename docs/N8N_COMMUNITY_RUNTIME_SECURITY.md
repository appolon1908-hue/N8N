# n8n Community runtime security contract

Status: **prepared in source; not applied or verified**.

This repository keeps the operational policy `UNVERIFIED` until runtime evidence exists. The exact desired community state is nevertheless canonical and machine-validated through:

- `config/n8n-policy.json` (`staging_binding_contract`, `desired_state`, and `activation_policy`);
- `release/staging-runtime-bindings.v1.yaml`;
- `config/n8n-community-runtime.v1.json`;
- `deploy/egress/n8n-egress-policy.v1.json`;
- `deploy/compose/compose.staging.yml`;
- `scripts/policy_community_runtime.py` and the repository gate.

The staging declaration is not a second source of truth. It is a human-readable projection of the canonical policy and is checked for the exact HTTPS route, service owner, Community editor strategy, dangerous-node posture, default-deny egress, and disabled activation state. Any stale `base_url_source` indirection or reintroduction of direct private Middleware routing fails repository validation.

## Editor boundary

The editor does not depend on n8n Enterprise SSO. The reviewed path is:

```text
browser -> Caddy HTTPS -> oauth2-proxy -> private n8n editor
```

oauth2-proxy authenticates against Keycloak with Authorization Code and PKCE S256 and requires either `n8n_operator` or `n8n_admin`. n8n's native owner login remains a separate second gate. The native owner identity is the dedicated `codestra-n8n-service-owner`, never a personal administrator account.

The Caddy source authority is responsible for proving that the editor host never
proxies directly to n8n port 5678. Until OpenBao is commissioned, the Keycloak
client, oauth2-proxy cookie, and native n8n owner bootstrap material use
root-owned secret files outside Git with 90-day rotation. The Middleware OAuth2
credential is then held only in n8n's encrypted credential store. This source
must not claim live OpenBao delivery before OpenBao itself is deployed and
verified.

## Middleware credential and route

A single service-owned generic OAuth2 credential is approved as the desired state:

- name: `Codestra Middleware Service`;
- owner: `codestra-n8n-service-owner`;
- n8n credential type: `oAuth2Api`;
- grant: client credentials;
- Keycloak client: `n8n-automation`;
- audience: `middleware-api`;
- scopes: `middleware.request.forward` and `middleware.status.read`.

The credential secret is never stored in workflow JSON or this repository.

All future executable HTTP Request nodes must use the fixed HTTPS origin `https://api.codestra.co` and only these routes:

- `POST /v1/integrations/n8n/commands`;
- `GET /v1/integrations/n8n/operations/{command_id}`.

Direct private Middleware listeners, Odoo, provider APIs, databases, Kong Admin, and Keycloak Admin are not workflow destinations.

## Node and egress controls

The Compose template excludes Code, Execute Command, FTP, Git, Local File Trigger, Read/Write Files, and SSH nodes. The workflow validator separately default-denies node types and rejects direct provider, database, and internal-service references.

Application SSRF protection is enabled with only `api.codestra.co` and `auth.codestra.co` approved by hostname and all IPv4/IPv6 ranges blocked by default. This is defense in depth, not the sole network boundary.

A runtime firewall or equivalent network policy remains mandatory. It must default deny and allow only:

- HTTPS to the Caddy/Kong Middleware gateway;
- HTTPS to the Keycloak token endpoint;
- the reviewed PostgreSQL and Redis endpoints;
- approved DNS resolvers.

Runtime egress evidence must be independently captured before the operational policy can move to `VERIFIED`. Source validation rejects fabricated evidence while the contract remains `PREPARED_NOT_APPLIED`.

## Non-actions

This change does not activate workflows, create credentials, mutate Keycloak, deploy oauth2-proxy, apply a firewall, restart n8n, reload Caddy, or change production.
