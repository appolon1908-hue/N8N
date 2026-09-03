#!/usr/bin/env python3
"""Complete the current-main n8n observability authority remediation."""

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
            "readiness_endpoint": "/healthz/readiness",
            "network_scope": "private",
            "metrics_source": "n8n-native",
        },
    )
    for component in ("main", "webhook", "worker"):
        target = by_component[component]
        target["readiness_endpoint"] = "/healthz/readiness"
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
    marker = '''  n8n-worker:
    <<: *n8n-common
'''
    block = '''  n8n-webhook:
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
'''
    source = replace_once(source, marker, block, "webhook Compose service")
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
    old = '''    main = services.get("n8n-main") if isinstance(services.get("n8n-main"), dict) else {}
    worker = services.get("n8n-worker") if isinstance(services.get("n8n-worker"), dict) else {}
    if not _health_contains(main, "http://127.0.0.1:5678/healthz/readiness"):
        errors.append("n8n-main lacks the reviewed readiness probe")
'''
    new = '''    main = services.get("n8n-main") if isinstance(services.get("n8n-main"), dict) else {}
    webhook = services.get("n8n-webhook") if isinstance(services.get("n8n-webhook"), dict) else {}
    worker = services.get("n8n-worker") if isinstance(services.get("n8n-worker"), dict) else {}
    if not _health_contains(main, "http://127.0.0.1:5678/healthz/readiness"):
        errors.append("n8n-main lacks the reviewed readiness probe")
    if not _health_contains(webhook, "http://127.0.0.1:5678/healthz/readiness"):
        errors.append("n8n-webhook lacks the reviewed readiness probe")
    webhook_command = webhook.get("command") if isinstance(webhook, dict) else None
    if "webhook" not in " ".join(str(value) for value in webhook_command or []):
        errors.append("n8n-webhook command does not start a webhook process")
'''
    source = replace_once(source, old, new, "webhook policy checks")
    path.write_text(source, encoding="utf-8")


def update_tests() -> None:
    compose_path = ROOT / "tests/test_compose_semantics.py"
    compose = compose_path.read_text(encoding="utf-8")
    old = '''        worker = copy.deepcopy(common)
        worker["environment"] = {
'''
    new = '''        webhook = copy.deepcopy(common)
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
'''
    compose = replace_once(compose, old, new, "webhook semantic fixture")
    compose = replace_once(
        compose,
        '"services": {"n8n-main": main, "n8n-worker": worker},',
        '"services": {"n8n-main": main, "n8n-webhook": webhook, "n8n-worker": worker},',
        "webhook fixture registration",
    )
    marker = '''    def test_telemetry_network_must_be_external(self) -> None:
'''
    addition = '''    def test_webhook_process_and_readiness_are_required(self) -> None:
        model = self.valid_model()
        model["services"]["n8n-webhook"]["command"] = ["worker"]
        model["services"]["n8n-webhook"]["healthcheck"] = {}
        errors = policy_compose.validate_rendered_compose(
            model, sorted(REQUIRED_DANGEROUS_NODES)
        )
        self.assertTrue(any("webhook process" in error for error in errors))
        self.assertTrue(any("n8n-webhook lacks" in error for error in errors))

    def test_telemetry_network_must_be_external(self) -> None:
'''
    compose = replace_once(compose, marker, addition, "webhook mutation test")
    compose_path.write_text(compose, encoding="utf-8")

    obs_path = ROOT / "tests/test_observability_authority.py"
    obs = obs_path.read_text(encoding="utf-8")
    marker = '''    def test_no_privileged_observability_collector(self):
'''
    addition = '''    def test_readiness_and_failure_event_contracts_are_complete(self):
        contract = json.loads(
            (ROOT / "observability/n8n-scrape-contract.v1.json").read_text()
        )
        self.assertEqual(
            {"main", "webhook", "worker"},
            {target["component"] for target in contract["targets"]},
        )
        self.assertTrue(
            all(target["readiness_endpoint"] == "/healthz/readiness" for target in contract["targets"])
        )
        self.assertEqual(
            {"main", "webhook", "worker"},
            {probe["component"] for probe in contract["readiness_probes"]},
        )
        self.assertTrue(
            all(probe["metric"] == "probe_success" for probe in contract["readiness_probes"])
        )
        self.assertEqual(
            "codestra_n8n_execution_failures_total",
            contract["structured_log_metrics"][0]["metric"],
        )
        self.assertEqual("counter", contract["structured_log_metrics"][0]["type"])
        self.assertFalse(contract["structured_log_metrics"][0]["payload_capture"])

    def test_alerts_use_readiness_and_a_monotonic_failure_counter(self):
        rules = (ROOT / "observability/n8n-readiness.rules.yml").read_text()
        self.assertIn("probe_success", rules)
        self.assertIn("codestra_n8n_execution_failures_total", rules)
        self.assertNotIn("increase(n8n_scaling_mode_queue_jobs_failed", rules)

    def test_no_privileged_observability_collector(self):
'''
    obs = replace_once(obs, marker, addition, "observability regressions")
    obs_path.write_text(obs, encoding="utf-8")


def update_readme() -> None:
    path = ROOT / "observability/README.md"
    source = path.read_text(encoding="utf-8")
    marker = "## "
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
    update_rules()
    update_contract()
    update_compose()
    update_compose_policy()
    update_tests()
    update_readme()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
