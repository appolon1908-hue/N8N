# Observability

The n8n processes expose their native `/metrics`, `/healthz`, and readiness
endpoints only on private runtime networks. The production platform owns the
Prometheus/Alloy scrape configuration and supplies dependency, container,
backup, and restore evidence through separately authorized exporters.

`n8n-scrape-contract.v1.json` is the hand-off contract. It deliberately forbids
Docker socket access, container exec/inspect, database superuser access, secret
reads, and direct traversal of backup storage. The removed legacy collector
required all of those privileges and is not an approved production mechanism.

Native n8n queue metrics are enabled in Compose. Logs use JSON on stdout so the
platform collector can attach runtime labels and ship them without mounting a
log file or a secret into n8n. Alert definitions must be validated in staging
before production rollout. Merging this source does not install a scraper or
activate workflows.

The non-applying staging profile also enables n8n's preview OpenTelemetry
exporter at ten-percent sampling over OTLP/HTTP to `alloy:4318` on a reviewed
private external telemetry network. W3C context propagation remains enabled,
while agent tracing and agent input/output recording are explicitly disabled.
This is staging-soak configuration, not production trace certification: the
platform receiver/network must be reviewed and an isolated trace-to-log test
must pass before any production rollout.
