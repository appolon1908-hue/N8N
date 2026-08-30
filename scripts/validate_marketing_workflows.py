import json
from pathlib import Path


def main() -> None:
    design_files = list(Path('docs/marketing').rglob('*.design.json'))
    assert design_files, 'no_marketing_design_contracts_found'
    for path in design_files:
        data = json.loads(path.read_text(encoding='utf-8'))
        text = json.dumps(data).lower()
        assert data.get('executable') is False, f'design_must_not_be_executable:{path}'
        assert data.get('activationState') == 'DISABLED', f'design_must_be_disabled:{path}'
        assert data.get('networkPolicy') == 'MIDDLEWARE_ONLY', f'middleware_only_required:{path}'
        assert data.get('endpointBinding') == 'UNVERIFIED', f'unverified_endpoint_must_remain_explicit:{path}'
        assert data.get('credentialBinding') == 'UNVERIFIED', f'unverified_credentials_must_remain_explicit:{path}'
        assert 'graph.facebook.com' not in text, f'n8n_must_not_call_meta_directly:{path}'
        assert 'googleads.googleapis.com' not in text, f'n8n_must_not_call_google_ads_directly:{path}'
        assert '/jsonrpc' not in text and '/web/dataset/call_kw' not in text, f'n8n_must_not_call_odoo_directly:{path}'
        assert 'middleware' in text, f'design_must_route_effects_through_middleware:{path}'
        assert 'idempot' in text, f'design_missing_idempotency_contract:{path}'
    executable_marketing = list(Path('workflows/marketing').rglob('*.json')) if Path('workflows/marketing').exists() else []
    assert not executable_marketing, 'executable_marketing_workflows_forbidden_until_runtime_bindings_verified'
    print('MARKETING_WORKFLOW_STAGE5_CERTIFICATION=PASS')
    print('MARKETING_WORKFLOW_RUNTIME_BINDINGS=UNVERIFIED')


if __name__ == '__main__':
    main()
