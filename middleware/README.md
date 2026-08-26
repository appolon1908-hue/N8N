# Middleware contracts

n8n is an orchestration client of Codestra middleware. The middleware remains the policy and delivery authority.

## Canonical machine-event headers

```text
X-Timestamp: <unix-seconds>
X-Event-Id: <uuid>
X-Signature: sha256=<hex-hmac>
Content-Type: application/json
```

Canonical signing input:

```text
<timestamp>.<event-id>.<raw-request-body>
```

The receiver must compare signatures in constant time, reject timestamps outside the configured replay window, reserve the event id durably before side effects, and return the original outcome for a valid duplicate.

## Command rules

- `tenant_id`, `event_id`, `correlation_id`, and `idempotency_key` are mandatory.
- Authorization is evaluated against the resolved machine or human identity, never a caller-supplied role string.
- A command is accepted before provider delivery and completed only after a durable result.
- Suppression, consent, retention, integration-pause, and global kill-switch rules are rechecked immediately before dispatch.
- Retries preserve the same idempotency key and never cross tenant/company boundaries.
- Dead-letter replay requires an operator reason, immutable source event reference, and audit record.
