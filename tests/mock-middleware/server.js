'use strict';
const http=require('http'),crypto=require('crypto'),fs=require('fs'),path=require('path');
const port=8096, secret=fs.readFileSync(process.env.TEST_SECRET_FILE||'/run/secrets/mock_hmac','utf8').trim();
const fixtures=path.join('/workflows','fixtures'), actions=new Map();
const send=(res,status,obj)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(obj));};
const read=req=>new Promise((ok,no)=>{let chunks=[],size=0;req.on('data',c=>{size+=c.length;if(size>262144)no(new Error('too_large'));else chunks.push(c)});req.on('end',()=>ok(Buffer.concat(chunks)));req.on('error',no)});
const clean=o=>Object.fromEntries(Object.entries(o||{}).map(([k,v])=>[/password|secret|token|authorization|phone/i.test(k)?k:k,/password|secret|token|authorization|phone/i.test(k)?'[REDACTED]':v]));
const fixture=n=>JSON.parse(fs.readFileSync(path.join(fixtures,n),'utf8'));
function verify(req,raw,obj){
  const ts=Number(req.headers['x-codestra-timestamp']); if(!Number.isFinite(ts)||Math.abs(Date.now()/1000-ts)>300)return [401,'stale timestamp'];
  const expected=crypto.createHmac('sha256',secret).update(raw).digest('hex'); const got=String(req.headers['x-codestra-signature']||'').replace(/^sha256=/,'');
  if(!crypto.timingSafeEqual(Buffer.from(expected),Buffer.from(got.padEnd(expected.length,'0').slice(0,expected.length))))return [401,'invalid signature'];
  if(obj.event_version!=='1.0')return [422,'unsupported event version']; if(obj.environment!=='test')return [403,'invalid environment']; if(obj.campaign_id!=='TEST_SYN')return [403,'campaign not permitted']; return [200,'ok'];
}
const server=http.createServer(async(req,res)=>{try{
  const url=new URL(req.url,'http://middleware:8095'), raw=await read(req), body=raw.length?JSON.parse(raw):{};
  if(req.method==='GET'&&url.pathname.startsWith('/api/v1/automation/context/calls/'))return send(res,200,{uniqueid:url.pathname.split('/').pop(),lead_id:'37',campaign_id:'TEST_SYN',talk_seconds:90,wait_seconds:12});
  if(req.method==='GET'&&url.pathname.startsWith('/api/v1/automation/context/leads/'))return send(res,200,{lead_id:url.pathname.split('/').pop(),campaign_id:'TEST_SYN',score:82,contact:'[REDACTED]'});
  if(req.method==='GET'&&url.pathname.startsWith('/api/v1/automation/context/timeline/'))return send(res,200,{lead_id:url.pathname.split('/').pop(),events:[{type:'call.completed'}]});
  if(req.method==='GET'&&url.pathname.startsWith('/api/v1/automation/context/campaigns/'))return send(res,200,{campaign_id:'TEST_SYN',hot_lead_threshold:80});
  if(req.method==='GET'&&url.pathname==='/api/v1/automation/callbacks/due')return send(res,200,{items:fixture('callbacks.json')});
  if(req.method==='GET'&&url.pathname==='/api/v1/reports/daily-operations')return send(res,200,fixture('daily-report.json'));
  if(req.method==='POST'&&url.pathname==='/api/v1/automation/events/verify'){const [s,m]=verify(req,raw,body);return send(res,s,s===200?{verified:true,event_id:body.event_id}:{verified:false,error:m});}
  if(req.method==='POST'&&/^\/api\/v1\/automation\/executions\/(start|complete|fail)$/.test(url.pathname))return send(res,202,{accepted:true,execution_reference:'exec_test_001',payload:clean(body)});
  if(req.method==='POST'&&url.pathname==='/api/v1/automation/events/dead-letter')return send(res,202,{accepted:true,status:'dead_lettered',payload:clean(body)});
  if(req.method==='POST'&&url.pathname.startsWith('/api/v1/automation/actions/')){
    if(body.campaign_id&&body.campaign_id!=='TEST_SYN')return send(res,403,{error:'campaign not permitted'});
    const key=req.headers['idempotency-key']||body.idempotency_key||body.event_id; if(!key)return send(res,400,{error:'idempotency key required'});
    const digest=crypto.createHash('sha256').update(raw).digest('hex'), previous=actions.get(key);
    if(previous&&previous.digest!==digest)return send(res,409,{error:'idempotency conflict'}); if(previous)return send(res,200,{...previous.result,duplicate:true});
    const result={accepted:true,action_id:'act_'+crypto.createHash('sha256').update(key).digest('hex').slice(0,12),preview_only:url.pathname.endsWith('/preview')};actions.set(key,{digest,result});return send(res,202,result);
  }
  if(req.method==='GET'&&url.pathname==='/test/evidence')return send(res,200,{action_count:actions.size,outbound_network:false,external_messages:0,telephony_actions:0,production_writes:0});
  return send(res,404,{error:'not found'});
}catch(e){send(res,e.message==='too_large'?413:400,{error:String(e.message).replace(/secret|token|password/ig,'[REDACTED]')});}});
server.listen(port,'0.0.0.0',()=>process.stdout.write('mock middleware ready\n'));
