# Observability And Secrets Integration

This is the Stage 4 preparation contract for Grafana, Prometheus,
Alertmanager, Loki, Tempo, OpenTelemetry, Superset, exporters, Alloy, and
OpenBao.

These repositories are infrastructure/control components. They are not added to
the n8n connected domain-system count. n8n must not call them as workflow
destinations and must not store their credentials in workflow JSON.

## Runtime Shape

```text
n8n runtime metrics/logs/traces
        |
        v
Alloy / OpenTelemetry
        |
        +--> Prometheus <--- Node Exporter / cAdvisor / PostgreSQL Exporter / Redis Exporter / Blackbox Exporter
        |        |
        |        v
        |   Alertmanager
        |
        +--> Loki
        |
        +--> Tempo

Grafana reads Prometheus, Loki, Tempo, and Alertmanager.
Superset reads approved reporting datasets only.
OpenBao stores runtime secrets and policy; Git stores aliases and manifests only.
```

## Configuration Order

1. Publish a default branch/HEAD for
   `appolon1908-hue/Codestra-Postgres-Exporter` so the PostgreSQL exporter can
   be pinned by immutable SHA.
2. Prepare OpenBao policies and secret aliases for n8n, Prometheus,
   Alertmanager, Grafana, Loki, Tempo, Alloy, Superset, PostgreSQL exporter,
   and Redis exporter.
3. Enable n8n metrics and runtime labels: tenant, workflow group, correlation
   id, command id, job id, delivery flag, and capability state.
4. Configure Alloy/OpenTelemetry pipelines for redacted logs, metrics, and
   traces. Do not forward raw customer payloads, tokens, provider credentials,
   message bodies, call recordings, or SMTP secrets.
5. Configure Prometheus scrape jobs for n8n, Middleware, exporters, and
   blackbox probes.
6. Configure Alertmanager routes for workflow failures, stuck leases, DLQ
   growth, unknown command outcomes, delivery-flag changes, target-down
   incidents, and OpenBao sealed/unavailable.
7. Configure Grafana datasources and dashboards from Prometheus, Loki, Tempo,
   and Alertmanager.
8. Configure Superset only against approved analytical/reporting data sources.
9. Run staging proof with delivery flags off before promoting any production
   observability route or dashboard as authoritative.

## Source Gate

Run:

```bash
python scripts/validate_observability_stack.py
```

The gate enforces the 14-component stack, blocks n8n writes to observability and
OpenBao, requires OpenBao as the secret authority, keeps the integration in
`PREPARED_NOT_APPLIED`, and records unresolved repository/runtime blockers.
