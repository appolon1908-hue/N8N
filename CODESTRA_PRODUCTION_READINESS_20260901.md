# Codestra Production Readiness Gate — n8n

Status: NOT PRODUCTION CERTIFIED

Governed by `Infustruction-repo/CODESTRA_PRODUCTION_READINESS_WAVE_20260901.md`.

Required: exact-head CI; Critical=0; High=0; workflow source authority; immutable workflow/release identity; Keycloak service identity; OpenBao-delivered Middleware-client credentials only; no direct provider secrets; dangerous-node exclusions; durable command/status reconciliation; staging E2E; observability; rollback/export evidence.

Keep production workflows and external provider writes disabled until separately certified. Do not modify SSH access.
