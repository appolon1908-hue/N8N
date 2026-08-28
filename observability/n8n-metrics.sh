#!/usr/bin/env bash
set -euo pipefail

output=/var/lib/node_exporter/textfile_collector/codestra_n8n.prom
scratch=$(mktemp "${output}.tmp.XXXXXX")
trap 'test ! -e "$scratch" || unlink "$scratch"' EXIT

component_metric() {
  local container=$1 environment=$2 component=$3
  local value=0
  if docker inspect "$container" --format '{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>/dev/null | grep -Eq '^true (healthy|none)$'; then
    value=1
  fi
  printf 'codestra_n8n_component_up{environment="%s",component="%s",container="%s"} %s\n' "$environment" "$component" "$container" "$value" >> "$scratch"
}

database_metrics() {
  local container=$1 database=$2 user=$3 environment=$4
  docker exec "$container" psql -U "$user" -d "$database" -At -F ' ' -c "
    select 'codestra_n8n_workflows_total{environment=\"$environment\"}', count(*) from workflow_entity;
    select 'codestra_n8n_workflows_active{environment=\"$environment\"}', count(*) filter (where active) from workflow_entity;
    select 'codestra_n8n_credentials_total{environment=\"$environment\"}', count(*) from credentials_entity;
    select 'codestra_n8n_failed_executions_1h{environment=\"$environment\"}', count(*) filter (where status='error' and \"startedAt\" > now() - interval '1 hour') from execution_entity;
    select 'codestra_n8n_running_executions{environment=\"$environment\"}', count(*) filter (where status in ('running','new','waiting')) from execution_entity;
    select 'codestra_n8n_oldest_running_execution_age_seconds{environment=\"$environment\"}', coalesce(extract(epoch from now() - (min(\"startedAt\") filter (where status in ('running','new','waiting')))),0)::bigint from execution_entity;
    select 'codestra_n8n_database_size_bytes{environment=\"$environment\"}', pg_database_size(current_database());
  " >> "$scratch"
}

component_metric codestra-n8n-1 production main
component_metric codestra-n8n-staging-n8n-1 staging main
component_metric codestra-n8n-staging-webhook-1 staging webhook
component_metric codestra-n8n-staging-worker-1 staging worker-1
component_metric codestra-n8n-staging-worker-2-1 staging worker-2

database_metrics codestra-postgres-1 codestra_n8n postgres production
database_metrics codestra-n8n-staging-postgres-1 n8n_staging n8n_staging staging

redis_up=0
queue_ready=0
queue_active=0
queue_failed=0
if docker exec codestra-n8n-staging-redis-1 sh -ec 'redis-cli --no-auth-warning --user "$(cat /run/secrets/redis-n8n-username)" --pass "$(cat /run/secrets/redis-n8n-password)" ping | grep -qx PONG'; then
  redis_up=1
  queue_ready=$(docker exec codestra-n8n-staging-redis-1 sh -ec 'redis-cli --raw --no-auth-warning --user "$(cat /run/secrets/redis-n8n-username)" --pass "$(cat /run/secrets/redis-n8n-password)" LLEN bull:jobs:wait')
  queue_active=$(docker exec codestra-n8n-staging-redis-1 sh -ec 'redis-cli --raw --no-auth-warning --user "$(cat /run/secrets/redis-n8n-username)" --pass "$(cat /run/secrets/redis-n8n-password)" LLEN bull:jobs:active')
  queue_failed=$(docker exec codestra-n8n-staging-redis-1 sh -ec 'redis-cli --raw --no-auth-warning --user "$(cat /run/secrets/redis-n8n-username)" --pass "$(cat /run/secrets/redis-n8n-password)" ZCARD bull:jobs:failed')
fi
printf 'codestra_n8n_redis_up{environment="staging"} %s\n' "$redis_up" >> "$scratch"
printf 'codestra_n8n_queue_depth{environment="staging",state="ready"} %s\n' "$queue_ready" >> "$scratch"
printf 'codestra_n8n_queue_depth{environment="staging",state="active"} %s\n' "$queue_active" >> "$scratch"
printf 'codestra_n8n_queue_depth{environment="staging",state="failed"} %s\n' "$queue_failed" >> "$scratch"

recovery_root=/opt/codestra/backups/n8n-recovery
latest_recovery=$(find "$recovery_root" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort | tail -1)
recovery_dir="$recovery_root/$latest_recovery"
grep -qx 'RECOVERY_CAPTURE=PASS' "$recovery_dir/STATUS.txt"
grep -qx 'ENCRYPTION=PASS' "$recovery_dir/STATUS.txt"
grep -qx 'RESTORE_REHEARSAL=PASS' "$recovery_dir/STATUS.txt"
backup_file=$(find "$recovery_dir" -maxdepth 1 -type f -name 'n8n-recovery-*.tar.gz.gpg' -print -quit)
backup_epoch=$(stat -c %Y "$backup_file")
restore_epoch=$(stat -c %Y "$recovery_dir/RESTORE-REHEARSAL.txt")
printf 'codestra_n8n_backup_last_success_timestamp_seconds %s\n' "$backup_epoch" >> "$scratch"
printf 'codestra_n8n_restore_last_success_timestamp_seconds %s\n' "$restore_epoch" >> "$scratch"

chmod 0644 "$scratch"
mv -f "$scratch" "$output"
trap - EXIT
