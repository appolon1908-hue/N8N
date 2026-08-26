#!/usr/bin/env python3
import hashlib,hmac,json,os,urllib.error,urllib.request
base=os.environ.get('MOCK_URL','http://127.0.0.1:38096'); secret=open(os.environ['MOCK_SECRET_FILE']).read().strip(); root=os.path.dirname(os.path.dirname(__file__))
event=json.load(open(root+'/fixtures/completed-call.json')); raw=json.dumps(event,separators=(',',':')).encode(); now=str(int(__import__('time').time()))
def call(path,body=None,headers=None):
 data=None if body is None else json.dumps(body,separators=(',',':')).encode(); req=urllib.request.Request(base+path,data=data,headers=headers or {},method='POST' if body is not None else 'GET')
 try:
  with urllib.request.urlopen(req) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
sig=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest(); headers={'Content-Type':'application/json','X-Codestra-Timestamp':now,'X-Codestra-Signature':sig,'X-Codestra-Event-ID':event['event_id'],'X-Codestra-Workflow-ID':'CdstCallCompletedV1'}
req=urllib.request.Request(base+'/api/v1/automation/events/verify',data=raw,headers=headers,method='POST'); assert urllib.request.urlopen(req).status==200
bad={**headers,'X-Codestra-Signature':'0'*64}; req=urllib.request.Request(base+'/api/v1/automation/events/verify',data=raw,headers=bad,method='POST')
try: urllib.request.urlopen(req);raise AssertionError('invalid signature accepted')
except urllib.error.HTTPError as e: assert e.code==401
stale={**headers,'X-Codestra-Timestamp':'1','X-Codestra-Signature':hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()};req=urllib.request.Request(base+'/api/v1/automation/events/verify',data=raw,headers=stale,method='POST')
try: urllib.request.urlopen(req);raise AssertionError('stale timestamp accepted')
except urllib.error.HTTPError as e: assert e.code==401
for change,expected in [({'event_version':'2.0'},422),({'campaign_id':'CAMP1'},403)]:
 b={**event,**change}; rb=json.dumps(b,separators=(',',':')).encode(); h={**headers,'X-Codestra-Signature':hmac.new(secret.encode(),rb,hashlib.sha256).hexdigest()};req=urllib.request.Request(base+'/api/v1/automation/events/verify',data=rb,headers=h,method='POST')
 try: urllib.request.urlopen(req);raise AssertionError('invalid event accepted')
 except urllib.error.HTTPError as e: assert e.code==expected
ah={'Content-Type':'application/json','Idempotency-Key':event['idempotency_key']}; assert call('/api/v1/automation/actions/call-completed',event,ah)[0]==202; status,dup=call('/api/v1/automation/actions/call-completed',event,ah);assert status==200 and dup['duplicate']
conf={**event,'data':{**event['data'],'talk_seconds':999}};assert call('/api/v1/automation/actions/call-completed',conf,ah)[0]==409
assert len(call('/api/v1/automation/callbacks/due')[1]['items'])==2;assert call('/api/v1/reports/daily-operations')[1]['kpis']['total_calls']==100
evidence=call('/test/evidence')[1];assert evidence['external_messages']==evidence['telephony_actions']==evidence['production_writes']==0
print('mock functional tests passed: signature, freshness, scope, idempotency, fixtures, no side effects')
