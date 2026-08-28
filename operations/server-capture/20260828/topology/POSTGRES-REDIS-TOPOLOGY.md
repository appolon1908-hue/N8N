# PostgreSQL and Redis topology

## Production

- n8n service: `codestra-n8n-1`
- Database service: `codestra-postgres-1`
- Database: `codestra_n8n`
- Database role: `codestra_n8n`
- Persistent n8n volume: `codestra_n8n_data`
- Networks: `codestra_backend`, `codestra_edge`, `codestra-internal-integration`
- Execution mode: regular/main process; no production Redis queue configured

## Staging

- Main service: `codestra-n8n-staging-n8n-1`
- Webhook service: `codestra-n8n-staging-webhook-1`
- Worker services: `codestra-n8n-staging-worker-1` and `worker-2-1`
- Database service: `codestra-n8n-staging-postgres-1`
- Database and role: `n8n_staging`
- Redis service: `codestra-n8n-staging-redis-1`
- Execution mode: queue
- Persistent n8n volume: `codestra-n8n-staging_n8n_data`
- Persistent PostgreSQL volume: `codestra-n8n-staging_postgres_data`
- Persistent Redis volume: `codestra-n8n-staging_queue_redis_data`
- Networks: `codestra-n8n-staging_backend`, `codestra-n8n-staging_edge`,
  `codestra-n8n-middleware-staging-control`, and provisioning private network

Secret file paths and secret values are deliberately excluded from this
topology document. Mount destinations without values remain in runtime evidence.
