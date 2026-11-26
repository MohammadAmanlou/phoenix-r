// PHOENIX-R V5: separate acquisition from robust certification. Node.js 18+.
import {writeFileSync} from 'node:fs';
function robustExperiment(){
 const alpha=.05,m=12,B=24,n=5000,p=.1,s=.65,f=.025;
 const cfgs=[{name:"matched",actualF:.025,hot:0},{name:"shift",actualF:.12,hot:0},{name:"correlated",actualF:.025,hot:.15}];
 const methods=[["nominal",.025,.025],["gate_12",.025,.12],["gate_30",.025,.30],["policy_and_gate_12",.12,.12],["policy_and_gate_30",.30,.30]];
 function rng(seed){let x=seed>>>0;return ()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return (x>>>0)/4294967296}}
 const rows=[];
 for(const c of cfgs)for(const [policy,searchF,gateF] of methods){
  const rs=[];
  for(let truth=0;truth<=1;truth++){let correct=0,wrong=0;
   for(let i=0;i<n;i++){
    const r=rng(123457+Math.imul(i+1,2654435761)+truth*91919);
    const valid=Array.from({length:m},()=>truth===1&&r()<p),hot=Array.from({length:m},()=>r()<c.hot);
    const tape=Array.from({length:m},(_,j)=>Array.from({length:B},()=>r()<(valid[j]?s:hot[j]?.30:c.actualF)));
    const a=Array(m).fill(0),b=Array(m).fill(0);
    const pl=Math.log(s/searchF),nl=Math.log((1-s)/(1-searchF));
    const pg=Math.log(s/gateF),ng=Math.log((1-s)/(1-gateF));
    for(let t=0;t<B;t++){let j=0,best=-Infinity;for(let i=0;i<m;i++){let z=a[i]*pl+b[i]*nl;if(z>best+1e-14){best=z;j=i}}if(tape[j][a[j]+b[j]])a[j]++;else b[j]++}
    const z=a.map((v,j)=>v*pl+b[j]*nl),w=z.map(v=>Math.log(1-p+p*Math.exp(v))),alt=1/(1+Math.exp(-w.reduce((x,y)=>x+y,0)));
    const q=z.map((v,j)=>alt*p*Math.exp(v-w[j]));
    let j=-1,best=0;
    for(let i=0;i<m;i++){const value=2*q[i]-1;if(a[i]*pg+b[i]*ng>=Math.log(m/alpha)&&value>best){best=value;j=i}}
    correct+=+(j>=0&&valid[j]);wrong+=+(j>=0&&!valid[j]);
   }
   rs.push({correct:correct/n,wrong:wrong/n});
  }
  rows.push({config:c.name,policy,searchF,gateF,n_per_truth:n,correct_false_claim:rs[1].correct,wrong_root_false_claim:rs[1].wrong,false_correction_true_claim:rs[0].wrong,mean_utility:(rs[1].correct-rs[1].wrong-rs[0].wrong)/2,conditional_null_bound_valid:Math.max(c.actualF,c.hot>0?.30:0)<=gateF});
 }
 return {rows,trajectories:rows.length*2*n,alpha};
}
const out=robustExperiment();const keys=Object.keys(out.rows[0]);writeFileSync(new URL('robust_gate.csv',import.meta.url),[keys.join(','),...out.rows.map(r=>keys.map(k=>r[k]).join(','))].join('\n')+'\n');console.log(JSON.stringify(out,null,2));
