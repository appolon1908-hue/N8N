.PHONY: validate repository policy-tests workflows secrets compose runtime-status ruleset-contract platform-control-plane

validate: repository policy-tests workflows secrets compose runtime-status ruleset-contract platform-control-plane

repository:
	python3 scripts/validate_repository.py

policy-tests:
	python3 -m unittest tests.test_attest_n8n_policy tests.test_community_runtime_policy tests.test_compose_semantics tests.test_integration_contracts tests.test_middleware_surface tests.test_n8n_recovery_source tests.test_policy_guards tests.test_ruleset_contract tests.test_runtime_path_audit tests.test_runtime_path_privileged_stat tests.test_shared_templates
	python3 scripts/validate_workflow_completeness.py
	./tests/test_n8n_recovery_contract.sh

workflows:
	python3 scripts/validate_workflows.py workflows

secrets:
	python3 scripts/scan_secrets.py .

compose:
	docker compose --env-file deploy/env/ci.env -f deploy/compose/compose.staging.yml config --quiet

runtime-status:
	python3 scripts/verify_runtime_paths.py --allow-unverified

ruleset-contract:
	python3 scripts/validate_ruleset_contract.py

platform-control-plane:
	python3 scripts/validate_platform_control_plane.py
