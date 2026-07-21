# n8n secret references

All Middleware HTTP Request nodes reference the n8n credential ID
`codestraMiddlewareBearer` with display name `Codestra Middleware Bearer`.
Workflow JSON contains no credential value.

The credential must be provisioned separately from the root-managed runtime
secret file `/run/secrets/middleware_bearer_token`. It is an HTTP Header Auth
credential whose header name is `Authorization` and whose value is assembled
by the provisioning process. Never place the value in workflow JSON, Git,
Compose environment text, an n8n Code node, or execution data.

Missing credentials are an activation blocker. Imports must remain inactive,
and production activation must fail until a test request proves authenticated
Middleware access with no live-write flags enabled.
