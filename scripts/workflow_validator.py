#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
root=Path(__file__).parents[1]; mode=sys.argv[1] if len(sys.argv)>1 else 'integration'; errors=[]
manifest=json.loads((root/'manifests/workflow-manifest.json').read_text())
manifest_paths=[root / item['path'] for item in manifest['workflows']]
files=[p for p in manifest_paths if p.exists()]
missing=[str(p.relative_to(root)) for p in manifest_paths if not p.exists()]
all_files=sorted((root/'workflows').glob('*.json'))+sorted((root/'workflows').glob('*/*.json'))
extras=sorted(str(p.relative_to(root)) for p in all_files if p not in manifest_paths)
if missing: errors.append('manifest files missing: '+', '.join(missing))
if len(files)!=manifest['expected_workflow_count']: errors.append('workflow count differs from manifest')
allowed_types={'n8n-nodes-base.executeWorkflowTrigger','n8n-nodes-base.code','n8n-nodes-base.httpRequest','n8n-nodes-base.if','n8n-nodes-base.executeWorkflow','n8n-nodes-base.webhook','n8n-nodes-base.respondToWebhook','n8n-nodes-base.switch','n8n-nodes-base.manualTrigger','n8n-nodes-base.scheduleTrigger','n8n-nodes-base.errorTrigger'}
ids=set()
for f in files:
 w=json.loads(f.read_text()); raw=f.read_text().lower(); wid=w.get('id')
 if wid in ids: errors.append(f'{f}: duplicate ID {wid}')
 ids.add(wid)
 if w.get('active') is not False: errors.append(f'{f}: active must be false')
 if w.get('meta',{}).get('environment')!='test' or w.get('meta',{}).get('campaign_allowlist')!=['TEST_SYN']: errors.append(f'{f}: test scope missing')
 if w.get('settings',{}).get('errorWorkflow')!='CdstErrorDeadLetterV1': errors.append(f'{f}: error workflow missing')
 if re.search(r'65\.21\.67\.207|crm\.codestra\.agency|external_dial|password\s*[=:]|api[_-]?key\s*[=:]|bearer\s+[a-z0-9]',raw,re.I): errors.append(f'{f}: forbidden target or secret')
 for n in w.get('nodes',[]):
  if n.get('type') not in allowed_types: errors.append(f'{f}: forbidden/community node {n.get("type")}')
  if n.get('type')=='n8n-nodes-base.httpRequest':
   url=str(n.get('parameters',{}).get('url',''))
   dynamic_context = url == '={{$json.context_url}}'
   env_middleware = url.startswith('={{$env.MIDDLEWARE_INTERNAL_URL}}')
   if not (url.startswith('http://middleware:8095/') or dynamic_context or env_middleware): errors.append(f'{f}: host not allowed: {url}')
   if n.get('parameters',{}).get('options',{}).get('timeout',0)<1000: errors.append(f'{f}: timeout missing')
 if mode=='production-candidate' and w['id']=='CdstAutomationRouterV1' and not w.get('meta',{}).get('signature_verification'): errors.append(f'{f}: verification path absent')
if extras:
 print(f'legacy/unmanifested workflow files preserved: {len(extras)}', file=sys.stderr)
if errors: print('\n'.join(errors));sys.exit(1)
print(f'{mode}: verified {len(files)} manifest-listed inactive TEST_SYN middleware-only workflows')
