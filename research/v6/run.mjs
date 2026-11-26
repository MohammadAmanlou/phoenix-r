// V6 Node.js 18+; local OpenAI-compatible endpoint. No dependencies.
import {mkdirSync,readFileSync,writeFileSync,appendFileSync,existsSync} from "node:fs";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {parseArgs} from "node:util";
import {performance} from "node:perf_hooks";
import {caseFor,room,scripted,summarize,selftest} from "./core.mjs";
const {values:v}=parseArgs({options:{backend:{type:"string",default:"scripted"},split:{type:"string",default:"smoke"},cases:{type:"string",default:"2"},model:{type:"string"},revision:{type:"string",default:"unverified"},endpoint:{type:"string",default:"http://127.0.0.1:11434/v1/chat/completions"},out:{type:"string",default:"local_runs/v6-smoke"},selftest:{type:"boolean",default:false}}});
if(v.selftest){console.log(JSON.stringify(await selftest(),null,2));process.exit(0)}
const n=Number(v.cases);if(!["scripted","llm"].includes(v.backend)||!["smoke","calibration","test"].includes(v.split)||!Number.isInteger(n)||n<2||n>10000||n%2)throw Error("Specify a valid backend, split and even case count between 2 and 10000.");
if(v.backend==="llm"&&!v.model)throw Error("--model required");
const ep=new URL(v.endpoint);if(ep.username||ep.password||ep.search||ep.hash)throw Error("Do not put credentials in the endpoint URL.");
mkdirSync(v.out,{recursive:true});
const manifest={backend:v.backend,split:v.split,cases:n,model:v.model??null,revision:v.revision,endpoint:v.backend==="llm"?v.endpoint:null,temperature:0,max_tokens:160,source_sha256:createHash("sha256").update(readFileSync(new URL("./core.mjs",import.meta.url))).update(readFileSync(new URL(import.meta.url))).digest("hex"),node:process.version};
const mp=join(v.out,"manifest.json"),jp=join(v.out,"rooms.jsonl");
if(existsSync(mp)&&JSON.stringify(JSON.parse(readFileSync(mp,"utf8")))!==JSON.stringify(manifest))throw Error("Manifest mismatch; choose a fresh --out directory.");
if(!existsSync(mp))writeFileSync(mp,JSON.stringify(manifest,null,2));
const rows=existsSync(jp)?readFileSync(jp,"utf8").split("\n").filter(Boolean).map(JSON.parse):[];
const key=r=>[r.id,r.assignment,r.relay].join("|"),done=new Set(rows.map(key));if(done.size!==rows.length)throw Error("Duplicate room keys.");
const llm=async req=>{const start=performance.now();const body={model:v.model,messages:[{role:"system",content:req.system},{role:"user",content:req.user}],temperature:0,max_tokens:160};
 const headers={"Content-Type":"application/json"};if(process.env.LOCAL_LLM_API_KEY)headers.Authorization="Bearer "+process.env.LOCAL_LLM_API_KEY;
 const res=await fetch(ep,{method:"POST",headers,body:JSON.stringify(body),signal:AbortSignal.timeout(180000)});
 if(!res.ok)throw Error("HTTP "+res.status);
 const x=await res.json(),raw=x?.choices?.[0]?.message?.content;
 return {raw:typeof raw==="string"?raw:"",usage:x.usage??null,latency_ms:performance.now()-start};
};
const arms=[["clustered","snapshot"],["clustered","persistent"],["dispersed","snapshot"],["dispersed","persistent"]];
for(let i=0;i<n;i++){const c=caseFor(v.split,i);const order=arms.slice(i%4).concat(arms.slice(0,i%4));for(const [assignment,relay] of order){const k=key({id:c.id,assignment,relay});if(done.has(k))continue;try{const r=await room(c,assignment,relay,v.backend==="llm"?llm:scripted);appendFileSync(jp,JSON.stringify(r)+"\n");rows.push(r);done.add(k);console.log(k,rows.length+"/"+(4*n));}catch(e){appendFileSync(join(v.out,"errors.jsonl"),JSON.stringify({key:k,error:String(e),time:new Date().toISOString()})+"\n");throw e}}}
const summary=summarize(rows);writeFileSync(join(v.out,"summary.json"),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
