#!/usr/bin/env python3
"""Apply the reviewed n8n observability delta to the current main authority."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise SystemExit(f"{label}: expected one source marker")
    return text.replace(old, new, 1)


def update_makefile() -> None:
    path = ROOT / "Makefile"
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        "tests.test_middleware_surface tests.test_policy_guards",
        "tests.test_middleware_surface tests.test_observability_authority tests.test_policy_guards",
        "observability policy-test registration",
    )
    path.write_text(source, encoding="utf-8")


def update_rules() -> None:
    path = ROOT / "observability/n8n-readiness.rules.yml"
    path.write_text(
        '''groups:
  - name: n8n-readiness
    rules:
      - alert: CodestraN8nComponentDownOrUnready
        expr: |
          up{job=~"codestra-n8n-(main|webhook|worker.*)"} == 0
          or
          probe_success{job=~"codestra-n8n-(main|webhook|worker.*)-readiness"} == 0
        for: 2m
        labels: {severity: critical, service: n8n}
        annotations: {summary: "n8n component is unavailable or unready", description: "A main, webhook, or worker component is unreachable or has failed its private readiness probe."}
      - alert: CodestraN8nQueueBacklogWarning
        expr: n8n_scaling_mode_queue_jobs_waiting > 25
        for: 5m
        labels: {severity: warning, service: n8n, environment: staging}
        annotations: {summary: "n8n queue backlog is elevated", description: "More than 25 execution jobs have remained ready for five minutes."}
      - alert: CodestraN8nQueueBacklogCritical
        expr: n8n_scaling_mode_queue_jobs_waiting > 100
        for: 5m
        labels: {severity: critical, service: n8n, environment: staging}
        annotations: {summary: "n8n queue backlog is critical", description: "More than 100 execution jobs have remained ready for five minutes."}
      - alert: CodestraN8nFailedExecutions
        expr: increase(codestra_n8n_execution_failures_total[1h]) > 0
        for: 2m
        labels: {severity: warning, service: n8n}
        annotations: {summary: "n8n executions are failing", description: "The structured-log failure event counter increased during the last hour."}
      - alert: CodestraN8nRedisDown
        expr: redis_up{service="n8n-queue",environment="staging"} == 0
        for: 2m
        labels: {severity: critical, service: redis, environment: staging}
        annotations: {summary: "n8n queue Redis is unavailable", description: "The staging queue Redis authentication and PING check failed."}
      - alert: CodestraN8nPostgresConnectionsHigh
        expr: pg_stat_database_numbackends / on() group_left pg_settings_max_connections > 0.80
        for: 5m
        labels: {severity: warning, service: postgres}
        annotations: {summary: "PostgreSQL connection capacity is high", description: "PostgreSQL is using more than 80 percent of configured connections."}
      - alert: CodestraN8nBackupStale
        expr: time() - codestra_n8n_backup_last_success_timestamp_seconds > 90000
        for: 15m
        labels: {severity: critical, service: n8n-backup, environment: production}
        annotations: {summary: "n8n recovery point is stale", description: "The latest complete encrypted n8n recovery point is older than 24 hours."}
      - alert: CodestraN8nRestoreRehearsalOverdue
        expr: time() - codestra_n8n_restore_last_success_timestamp_seconds > 604800
        for: 1h
        labels: {severity: critical, service: n8n-recovery, environment: production}
        annotations: {summary: "n8n restore rehearsal is overdue", description: "No successful isolated n8n restore rehearsal has been recorded in seven days."}
''',
        encoding="utf-8",
    )


def update_contract() -> None:
    path = ROOT / "observability/n8n-scrape-contract.v1.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    by_component = {item["component"]: item for item in contract["targets"]}
    by_component.setdefault(
        "webhook",
        {
            "component": "webhook",
            "endpoint": "/metrics",
            "health_endpoint": "/healthz",
            "network_scope": "private",
            "metrics_source": "n8n-native",
        },
    )
    for component in ("main", "webhook", "worker"):
        by_component[component]["readiness_endpoint"] = "/healthz/readiness"
    contract["targets"] = [by_component[name] for name in ("main", "webhook", "worker")]
    contract["readiness_probes"] = [
        {
            "component": name,
            "job": f"codestra-n8n-{name}-readiness",
            "endpoint": "/healthz/readiness",
            "metric": "probe_success",
            "network_scope": "private",
        }
        for name in ("main", "webhook", "worker")
    ]
    contract["structured_log_metrics"] = [
        {
            "metric": "codestra_n8n_execution_failures_total",
            "type": "counter",
            "source": "n8n-json-stdout-execution-failure-events",
            "collector": "alloy-private-log-pipeline",
            "payload_capture": False,
        }
    ]
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")


def update_compose() -> None:
    path = ROOT / "deploy/compose/compose.staging.yml"
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '''    N8N_LOG_LEVEL: info
    LIVE_ADVERTISING_ENABLED: "false"
''',
        '''    N8N_LOG_LEVEL: info
    N8N_LOG_FORMAT: json
    N8N_LOG_OUTPUT: console
    N8N_OTEL_ENABLED: "true"
    N8N_OTEL_EXPORTER_OTLP_ENDPOINT: http://alloy:4318
    N8N_OTEL_EXPORTER_SERVICE_NAME: codestra-n8n
    N8N_OTEL_TRACES_SAMPLE_RATE: "0.10"
    N8N_OTEL_TRACES_INCLUDE_NODE_SPANS: "true"
    N8N_OTEL_TRACES_PRODUCTION_ONLY: "true"
    N8N_OTEL_TRACES_INJECT_OUTBOUND: "true"
    N8N_AGENTS_TRACING_ENABLED: "false"
    N8N_AGENTS_TRACING_RECORD_INPUTS: "false"
    N8N_AGENTS_TRACING_RECORD_OUTPUTS: "false"
    LIVE_ADVERTISING_ENABLED: "false"
''',
        "structured logging and staging tracing",
    )
    source = replace_once(
        source,
        '''  networks:
    - middleware_network
  logging:
''',
        '''  networks:
    - middleware_network
    - telemetry_network
  logging:
''',
        "private telemetry attachment",
    )
    source = replace_once(
        source,
        '''  n8n-worker:
    <<: *n8n-common
''',
        '''  n8n-webhook:
    <<: *n8n-common
    command:
      - webhook
    expose:
      - "5678"
    healthcheck:
      test:
        - CMD
        - node
        - -e
        - "fetch('http://127.0.0.1:5678/healthz/readiness').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 60s

  n8n-worker:
    <<: *n8n-common
''',
        "dedicated webhook process",
    )
    source = replace_once(
        source,
        '''networks:
  middleware_network:
    external: true
    name: ${MIDDLEWARE_NETWORK:?MIDDLEWARE_NETWORK must be verified before use}

secrets:
''',
        '''networks:
  middleware_network:
    external: true
    name: ${MIDDLEWARE_NETWORK:?MIDDLEWARE_NETWORK must be verified before use}
  telemetry_network:
    external: true
    name: ${TELEMETRY_NETWORK:?TELEMETRY_NETWORK must be a reviewed private external network}

secrets:
''',
        "external telemetry network",
    )
    path.write_text(source, encoding="utf-8")


def update_compose_policy() -> None:
    path = ROOT / "scripts/policy_compose.py"
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        'EXPECTED_SERVICES = {"n8n-main", "n8n-worker"}',
        'EXPECTED_SERVICES = {"n8n-main", "n8n-webhook", "n8n-worker"}',
        "expected services",
    )
    source = replace_once(
        source,
        '''    "${MIDDLEWARE_NETWORK:?": "verified private-network input",
}''',
        '''    "${MIDDLEWARE_NETWORK:?": "verified private-network input",
    "${TELEMETRY_NETWORK:?": "reviewed private telemetry-network input",
}''',
        "telemetry static token",
    )
    source = replace_once(
        source,
        '''    "N8N_LOG_LEVEL": "info",
    "LIVE_ADVERTISING_ENABLED": "false",
''',
        '''    "N8N_LOG_LEVEL": "info",
    "N8N_LOG_FORMAT": "json",
    "N8N_LOG_OUTPUT": "console",
    "N8N_OTEL_ENABLED": "true",
    "N8N_OTEL_EXPORTER_OTLP_ENDPOINT": "http://alloy:4318",
    "N8N_OTEL_EXPORTER_SERVICE_NAME": "codestra-n8n",
    "N8N_OTEL_TRACES_SAMPLE_RATE": "0.10",
    "N8N_OTEL_TRACES_INCLUDE_NODE_SPANS": "true",
    "N8N_OTEL_TRACES_PRODUCTION_ONLY": "true",
    "N8N_OTEL_TRACES_INJECT_OUTBOUND": "true",
    "N8N_AGENTS_TRACING_ENABLED": "false",
    "N8N_AGENTS_TRACING_RECORD_INPUTS": "false",
    "N8N_AGENTS_TRACING_RECORD_OUTPUTS": "false",
    "LIVE_ADVERTISING_ENABLED": "false",
''',
        "telemetry environment policy",
    )
    source = replace_once(
        source,
        '''    network = (model.get("networks") or {}).get("middleware_network")
    if not isinstance(network, dict) or network.get("external") is not True:
        errors.append("middleware_network must be an externally provisioned Compose network")
    top_secrets = model.get("secrets") or {}
''',
        '''    network = (model.get("networks") or {}).get("middleware_network")
    if not isinstance(network, dict) or network.get("external") is not True:
        errors.append("middleware_network must be an externally provisioned Compose network")
    telemetry_network = (model.get("networks") or {}).get("telemetry_network")
    if not isinstance(telemetry_network, dict) or telemetry_network.get("external") is not True:
        errors.append("telemetry_network must be an externally provisioned Compose network")
    top_secrets = model.get("secrets") or {}
''',
        "telemetry network validation",
    )
    source = replace_once(
        source,
        '''        if _names(service.get("networks")) != {"middleware_network"}:
            errors.append(f"service {service_name} must attach only to middleware_network")
''',
        '''        if _names(service.get("networks")) != {"middleware_network", "telemetry_network"}:
            errors.append(
                f"service {service_name} must attach only to the reviewed middleware and telemetry networks"
            )
''',
        "service telemetry boundary",
    )
    source = replace_once(
        source,
        '''    main = services.get("n8n-main") if isinstance(services.get("n8n-main"), dict) else {}
    worker = services.get("n8n-worker") if isinstance(services.get("n8n-worker"), dict) else {}
    if not _health_contains(main, "http://127.0.0.1:5678/healthz/readiness"):
        errors.append("n8n-main lacks the reviewed readiness probe")
''',
        '''    main = services.get("n8n-main") if isinstance(services.get("n8n-main"), dict) else {}
    webhook = services.get("n8n-webhook") if isinstance(services.get("n8n-webhook"), dict) else {}
    worker = services.get("n8n-worker") if isinstance(services.get("n8n-worker"), dict) else {}
    if not _health_contains(main, "http://127.0.0.1:5678/healthz/readiness"):
        errors.append("n8n-main lacks the reviewed readiness probe")
    if not _health_contains(webhook, "http://127.0.0.1:5678/healthz/readiness"):
        errors.append("n8n-webhook lacks the reviewed readiness probe")
    webhook_command = webhook.get("command") if isinstance(webhook, dict) else None
    if "webhook" not in " ".join(str(value) for value in webhook_command or []):
        errors.append("n8n-webhook command does not start a webhook process")
''',
        "webhook policy checks",
    )
    path.write_text(source, encoding="utf-8")


def update_compose_tests() -> None:
    path = ROOT / "tests/test_compose_semantics.py"
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '''            "networks": {"middleware_network": None},
''',
        '''            "networks": {"middleware_network": None, "telemetry_network": None},
''',
        "telemetry fixture attachment",
    )
    source = replace_once(
        source,
        '''        worker = copy.deepcopy(common)
        worker["environment"] = {
''',
        '''        webhook = copy.deepcopy(common)
        webhook["command"] = ["webhook"]
        webhook["healthcheck"] = {
            "test": [
                "CMD",
                "node",
                "-e",
                "fetch('http://127.0.0.1:5678/healthz/readiness')",
            ]
        }
        worker = copy.deepcopy(common)
        worker["environment"] = {
''',
        "webhook semantic fixture",
    )
    source = replace_once(
        source,
        '"services": {"n8n-main": main, "n8n-worker": worker},',
        '"services": {"n8n-main": main, "n8n-webhook": webhook, "n8n-worker": worker},',
        "webhook fixture registration",
    )
    source = replace_once(
        source,
        '''            "networks": {
                "middleware_network": {"name": "middleware", "external": True}
            },
''',
        '''            "networks": {
                "middleware_network": {"name": "middleware", "external": True},
                "telemetry_network": {"name": "telemetry", "external": True},
            },
''',
        "telemetry network fixture",
    )
    source = replace_once(
        source,
        'any("attach only to middleware_network" in error for error in errors)',
        'any("reviewed middleware and telemetry networks" in error for error in errors)',
        "network mutation assertion",
    )
    source = replace_once(
        source,
        '''    def test_missing_node_exclusion_is_rejected(self) -> None:
''',
        '''    def test_webhook_process_and_readiness_are_required(self) -> None:
        model = self.valid_model()
        model["services"]["n8n-webhook"]["command"] = ["worker"]
        model["services"]["n8n-webhook"]["healthcheck"] = {}
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("webhook process" in error for error in errors))
        self.assertTrue(any("n8n-webhook lacks" in error for error in errors))

    def test_telemetry_network_must_be_external(self) -> None:
        model = self.valid_model()
        model["networks"]["telemetry_network"].pop("external")
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("telemetry_network" in error for error in errors))

    def test_missing_node_exclusion_is_rejected(self) -> None:
''',
        "webhook and telemetry mutation tests",
    )
    path.write_text(source, encoding="utf-8")


def update_observability_tests() -> None:
    path = ROOT / "tests/test_observability_authority.py"
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '''    def test_no_privileged_observability_collector(self):
''',
        '''    def test_readiness_and_failure_event_contracts_are_complete(self):
        contract = json.loads(
            (ROOT / "observability/n8n-scrape-contract.v1.json").read_text()
        )
        self.assertEqual(
            {"main", "webhook", "worker"},
            {target["component"] for target in contract["targets"]},
        )
        self.assertTrue(
            all(
                target["readiness_endpoint"] == "/healthz/readiness"
                for target in contract["targets"]
            )
        )
        self.assertEqual(
            {"main", "webhook", "worker"},
            {probe["component"] for probe in contract["readiness_probes"]},
        )
        self.assertTrue(
            all(
                probe["metric"] == "probe_success"
                for probe in contract["readiness_probes"]
            )
        )
        metric = contract["structured_log_metrics"][0]
        self.assertEqual("codestra_n8n_execution_failures_total", metric["metric"])
        self.assertEqual("counter", metric["type"])
        self.assertFalse(metric["payload_capture"])

    def test_alerts_use_readiness_and_a_monotonic_failure_counter(self):
        rules = (ROOT / "observability/n8n-readiness.rules.yml").read_text()
        self.assertIn("probe_success", rules)
        self.assertIn("codestra_n8n_execution_failures_total", rules)
        self.assertNotIn("increase(n8n_scaling_mode_queue_jobs_failed", rules)

    def test_no_privileged_observability_collector(self):
''',
        "observability regressions",
    )
    path.write_text(source, encoding="utf-8")


def update_readme() -> None:
    path = ROOT / "observability/README.md"
    source = path.read_text(encoding="utf-8")
    note = '''## Readiness and failure-event authority

Prometheus scrape reachability is not runtime readiness. The private platform
must probe `/healthz/readiness` for main, webhook, and worker processes and
publish `probe_success` under the exact readiness jobs declared in
`n8n-scrape-contract.v1.json`.

`n8n_scaling_mode_queue_jobs_failed` is a queue-depth gauge and must never be
used with `increase()`. Alloy derives the monotonic
`codestra_n8n_execution_failures_total` counter from structured JSON execution
failure events without recording workflow inputs, outputs, credentials, or
payloads.

'''
    if "## Readiness and failure-event authority" not in source:
        source = note + source
    path.write_text(source, encoding="utf-8")


def main() -> int:
    update_makefile()
    update_rules()
    update_contract()
    update_compose()
    update_compose_policy()
    update_compose_tests()
    update_observability_tests()
    update_readme()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
