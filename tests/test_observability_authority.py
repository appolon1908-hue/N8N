import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ObservabilityAuthorityTests(unittest.TestCase):
    def test_contract_is_private_and_least_privilege(self):
        contract = json.loads(
            (ROOT / "observability/n8n-scrape-contract.v1.json").read_text()
        )
        privacy = contract["privacy"]
        self.assertFalse(privacy["public_metrics"])
        for key in (
            "docker_socket_required",
            "container_exec_required",
            "database_superuser_required",
            "secret_read_required",
        ):
            self.assertFalse(privacy[key], key)
        self.assertTrue(contract["targets"])
        self.assertTrue(all(t["network_scope"] == "private" for t in contract["targets"]))
        self.assertTrue(all(t["metrics_source"] == "n8n-native" for t in contract["targets"]))

    def test_readiness_and_failure_event_contracts_are_complete(self):
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
        forbidden = (
            "docker exec",
            "docker inspect",
            "/var/run/docker.sock",
            "psql -u postgres",
            "/run/secrets/",
            "/opt/codestra/backups",
        )
        sources = []
        for path in (ROOT / "observability").rglob("*"):
            if path.is_file() and path.suffix in {".sh", ".py"}:
                sources.append(path.read_text().lower())
        combined = "\n".join(sources)
        for token in forbidden:
            self.assertNotIn(token, combined)

    def test_compose_enables_native_private_telemetry(self):
        compose = (ROOT / "deploy/compose/compose.staging.yml").read_text()
        for setting in (
            'N8N_METRICS: "true"',
            'N8N_METRICS_INCLUDE_QUEUE_METRICS: "true"',
            "N8N_LOG_FORMAT: json",
            "N8N_LOG_OUTPUT: console",
            'N8N_OTEL_ENABLED: "true"',
            "N8N_OTEL_EXPORTER_OTLP_ENDPOINT: http://alloy:4318",
            'N8N_AGENTS_TRACING_ENABLED: "false"',
            'N8N_AGENTS_TRACING_RECORD_INPUTS: "false"',
            'N8N_AGENTS_TRACING_RECORD_OUTPUTS: "false"',
        ):
            self.assertIn(setting, compose)
        self.assertNotRegex(compose, r"(?m)^\s*ports:\s*$")

    def test_trace_contract_is_private_and_not_certified_from_source(self):
        contract = json.loads(
            (ROOT / "observability/n8n-scrape-contract.v1.json").read_text()
        )
        tracing = contract["tracing"]
        runtime = json.loads(
            (ROOT / "config/n8n-community-runtime.v1.json").read_text()
        )
        version = lambda value: tuple(int(part) for part in value.split("."))
        self.assertGreaterEqual(
            version(runtime["minimum_runtime_version"]),
            version(tracing["minimum_n8n_version"]),
        )
        self.assertEqual(
            runtime["minimum_runtime_version"],
            tracing["reviewed_candidate_minimum_version"],
        )
        self.assertEqual(tracing["endpoint"], "http://alloy:4318")
        self.assertEqual(tracing["network_scope"], "private_external_telemetry_network")
        self.assertFalse(tracing["agent_tracing"])
        self.assertFalse(tracing["agent_inputs_recorded"])
        self.assertFalse(tracing["agent_outputs_recorded"])
        self.assertTrue(tracing["w3c_inbound_context"])
        self.assertTrue(tracing["w3c_outbound_context"])
        self.assertIn("pending", tracing["production_certification"])


if __name__ == "__main__":
    unittest.main()
