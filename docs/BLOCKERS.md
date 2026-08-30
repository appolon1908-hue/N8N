# Blockers

## N4 — command-envelope convention requires an owner decision (R6)

Status: **OPEN — cross-repository contract disagreement**

The N8N command envelope requires `tenant_id`, `correlation_id`, and
`idempotency_key` in the JSON body. The Klyrow integration manifest requires
the same routing metadata as `X-Tenant-ID`, `X-Correlation-ID`, and
`Idempotency-Key` headers. N8N also models a command as an unversioned `type`
plus a required integer `version`, while the Klyrow contract declares names
such as `email.message.send.v1`, with the version embedded in the type.

Both conventions currently validate independently, so a producer and consumer
can each be locally correct while disagreeing on the wire contract. This cannot
be resolved safely inside the N8N repository.

Recommended owner decision:

1. Keep tenant, correlation, and idempotency metadata in the signed/schema-
   validated body so it survives gateway rewriting.
2. Mirror those values into headers for gateway routing and observability, with
   Middleware rejecting header/body disagreement.
3. Use an unversioned command `type`; carry the schema version only in the
   separately required integer `version` field.
4. Publish the decision once in the estate integration authority, then update
   N8N, Middleware, and Klyrow together under cross-repository contract tests.

Until that decision is approved, all workflow exports remain inactive and no
external effects are enabled.
