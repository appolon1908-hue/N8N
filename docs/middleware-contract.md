# Middleware contract

All requests use request and correlation identifiers, an explicit 10-second timeout, and the internal `middleware:8095` gateway. Event verification uses the four `X-Codestra-*` headers. Middleware validates exact-body HMAC and replay freshness; n8n never stores the HMAC secret.

Sprint 1 action endpoints are preview/test-only and accept only `TEST_SYN`. Idempotency returns the prior result for the same key and body and HTTP 409 when the payload differs.
