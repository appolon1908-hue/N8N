# Credential metadata audit — 2026-08-28

No secret values are recorded here. The audit decrypted credentials only inside each container's tmpfs to verify recoverability, extracted non-secret metadata, and immediately unlinked the plaintext exports.

## Production (4 records)

| Credential | Type | Owner | System | Allowed domains | Scope | Rotation evidence | Environment | Disposition |
|---|---|---|---|---|---|---|---|---|
| Codestra Middleware Header Auth | httpHeaderAuth | Evelin / personal project | Codestra Middleware | Not encoded in credential | Unrecorded | Last metadata update 2026-08-17; no rotation date | Production | Block until domain, least-privilege scope, and rotation owner are documented |
| Codestra Middleware Event Signer | httpCustomAuth | Evelin / personal project | Codestra Middleware event signing | Not encoded in credential | Unrecorded | Last metadata update 2026-08-17; no rotation date | Production | Block until signing-key rotation and accepted destinations are documented |
| Codestra n8n Communications OAuth | oAuth2Api | Evelin / personal project | Communications control plane | `auth.codestra.co` token endpoint; resource domains unrecorded | Read/dispatch/result scopes for messages, SMS, and email | Last metadata update 2026-08-22; no rotation date | Production | Scope is broad; split dispatch scopes by channel before activation |
| Codestra n8n Campaign Production OAuth | oAuth2Api | Evelin / personal project | Campaign control plane | `auth.codestra.co` token endpoint; resource domains unrecorded | `n8n.policy.check n8n.results.submit` | Last metadata update 2026-08-22; no rotation date | Production | Closest to least privilege; still requires resource-domain allowlist and rotation date |

## Staging (9 records)

All nine records are owned by the Codestra Staging personal project and are staging-only. None has an explicit rotation date. Header/basic/JWT/crypto credentials do not encode an allowed-domain boundary, so network egress policy must supply it.

| Credential | Type | System | Scope/domain evidence | Disposition |
|---|---|---|---|---|
| Codestra Odoo 19 Staging API | httpHeaderAuth | Odoo 19 staging | Scope and domain unrecorded | Retain staging-only; bind to Odoo staging allowlist |
| Middleware Staging API | httpHeaderAuth | Middleware staging | Scope and domain unrecorded | Retain staging-only; bind to middleware staging allowlist |
| VICIdial Synthetic-Test API Placeholder | httpBasicAuth | VICIdial synthetic test | Placeholder, no domain | Keep disabled; never promote |
| Test SMTP Placeholder | smtp | Synthetic email | Placeholder; host is not represented as an approved URL domain | Keep disabled; never promote |
| Test AI Provider Placeholder | openAiApi | Synthetic AI | Placeholder, no domain | Keep disabled; never promote |
| Test Carrier SMS Provider Placeholder | httpHeaderAuth | Synthetic SMS | Placeholder, no domain | Keep disabled; never promote |
| Internal Webhook Staging JWT | jwtAuth | Internal staging webhook | Algorithm/key metadata only | Retain staging-only; document audience and issuer |
| Codestra Staging Callback Signing | httpHeaderAuth | Staging callback signing | Scope and domain unrecorded | Retain staging-only; document callback allowlist and rotation |
| Codestra Runtime HMAC | crypto | Staging runtime signing | HMAC secret metadata only | Retain staging-only; document key ID and rotation |

## Required remediation

1. Move credentials from personal projects to named service-owned projects with a primary and backup owner.
2. Record system, exact resource-domain allowlist, granted operations, issued date, rotation due date, and revocation procedure outside secret material.
3. Replace the 75 staging workflow exports containing hardcoded Authorization values before any Git reconciliation or production promotion.
4. Never export decrypted credential values into Git; metadata-only stubs are the maximum permitted representation.
