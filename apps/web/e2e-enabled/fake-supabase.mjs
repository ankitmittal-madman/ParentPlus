import http from 'node:http';
import { randomUUID } from 'node:crypto';
if (process.env.PARENTPLUS_SYNTHETIC_BROWSER !== '1' || process.env.NEXT_PUBLIC_SUPABASE_URL !== 'http://localhost:3191' || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY !== 'synthetic-public-key') throw new Error('Synthetic provider configuration required');
const actor='11111111-1111-4111-8111-111111111111';
const other='22222222-2222-4222-8222-222222222222';
const enc=x=>Buffer.from(JSON.stringify(x)).toString('base64url');
const tokenFor=id=>enc({alg:'HS256',typ:'JWT'})+'.'+enc({sub:id,aud:'authenticated',role:'authenticated',exp:4102444800,iat:1700000000})+'.c3ludGhldGlj';
const user={id:actor,aud:'authenticated',role:'authenticated',email:'parent@example.test',app_metadata:{},user_metadata:{},created_at:'2026-01-01T00:00:00.000Z'};
let current=null,history=[],fenced=new Set(),lose=false,loseAck=false,failBefore=false,events=[];
function reset(){current=null;history=[];fenced=new Set();lose=false;loseAck=false;failBefore=false;events=[]}
const server=http.createServer(async(req,res)=>{
  res.setHeader('Access-Control-Allow-Origin','http://127.0.0.1:3190');res.setHeader('Access-Control-Allow-Headers','authorization, apikey, content-type, x-client-info, x-supabase-api-version');res.setHeader('Access-Control-Allow-Methods','GET, POST, OPTIONS');res.setHeader('Content-Type','application/json');
  if(req.method==='OPTIONS'){res.writeHead(204);return res.end();}
  let body='';for await(const chunk of req)body+=chunk;let args={};try{if(body)args=JSON.parse(body)}catch{res.writeHead(400);return res.end('{}');}
  if(req.url==='/__test/reset'&&req.method==='POST'){reset();return res.end('{}');}
  if(req.url==='/__test/lose'&&req.method==='POST'){lose=true;return res.end('{}');}
  if(req.url==='/__test/lose-ack'&&req.method==='POST'){loseAck=true;return res.end('{}');}
  if(req.url==='/__test/fail-before'&&req.method==='POST'){failBefore=true;return res.end('{}');}
  if(req.url==='/__test/events'&&req.method==='GET')return res.end(JSON.stringify(events));
  const identity=[actor,other].find(id=>req.headers.authorization==='Bearer '+tokenFor(id));
  if(!identity||req.headers.apikey!=='synthetic-public-key'){res.writeHead(401);return res.end('{}');}
  if(req.url==='/auth/v1/user'&&req.method==='GET'){events.push('user:'+identity);return res.end(JSON.stringify({...user,id:identity}));}
  if(identity!==actor){events.push('unexpected-other-rpc');res.writeHead(403);return res.end('{}');}
  if(req.method!=='POST'||!req.url?.startsWith('/rest/v1/rpc/')){events.push('unexpected-endpoint');res.writeHead(404);return res.end('{}');}
  const op=req.url.slice('/rest/v1/rpc/'.length);events.push(op);
  if(op==='app_current_child_creation')return res.end(JSON.stringify(current?[current]:[]));
  if(op==='app_list_created_children')return res.end(JSON.stringify([...history,...(current?[current]:[])].map(x=>({child_id:x.child_id,display_name:x.display_name}))));
  if(op==='app_begin_child_creation'){
    if(failBefore){failBefore=false;res.writeHead(503);return res.end(JSON.stringify({message:'synthetic request not committed'}));}
    if(fenced.has(args.p_request_id)){res.writeHead(409);return res.end('{}');}
    if(current&&current.request_id===args.p_request_id&&current.prior_intent_id===args.p_prior_intent_id&&current.display_name===args.p_display_name)return res.end(JSON.stringify([{...current,disposition:'existing'}]));
    if((!current&&args.p_prior_intent_id!==null)||(current&&(!current.acknowledged||args.p_prior_intent_id!==current.intent_id))){res.writeHead(409);return res.end('{}');}
    if(current)history.push({...current});
    current={intent_id:randomUUID(),child_id:randomUUID(),display_name:args.p_display_name,acknowledged:false,prior_intent_id:args.p_prior_intent_id,request_id:args.p_request_id};
    if(lose){lose=false;res.writeHead(503);return res.end(JSON.stringify({message:'synthetic response lost'}));}
    return res.end(JSON.stringify([{...current,disposition:'created'}]));
  }
  if(op==='app_ack_child_creation'){if(current&&current.intent_id===args.p_intent_id){current.acknowledged=true;if(loseAck){loseAck=false;res.writeHead(503);return res.end(JSON.stringify({message:'synthetic confirmation response lost'}));}return res.end('true');}res.writeHead(400);return res.end('{}');}
  if(op==='app_fence_child_creation'){
    if(current&&current.request_id===args.p_request_id&&current.prior_intent_id===args.p_prior_intent_id)return res.end('"created"');
    if((!current&&args.p_prior_intent_id===null)||(current&&current.acknowledged&&current.intent_id===args.p_prior_intent_id)){fenced.add(args.p_request_id);return res.end('"fenced"');}
    return res.end('"unknown"');
  }
  if(op==='app_historical_child_creation')return res.end(JSON.stringify(history.some(x=>x.request_id===args.p_request_id&&x.prior_intent_id===args.p_prior_intent_id)?'found':'unknown'));
  events.push('unexpected-endpoint');res.writeHead(404);res.end('{}');
});server.listen(3191,'127.0.0.1');
