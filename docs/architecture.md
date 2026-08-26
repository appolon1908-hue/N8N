# Architecture

Sprint 1 uses one inactive event router, five shared sub-workflows, five business processors, and one error/dead-letter workflow. n8n only orchestrates. All context retrieval, verification, idempotency, and authorized action previews cross the Middleware boundary. The isolated test network has no external route and aliases its disposable mock as `middleware`.
