// PHOENIX-R V5: fixed-budget synthetic acquisition. Node.js 18+; no dependencies.
import {writeFileSync} from 'node:fs';
function experiment(){
  const cfgs=[
    {name:"small_matched",m:3,B:8,p:.15,s:.7,f:.05,actualS:.7,actualF:.05,n:3000},
    {name:"large_matched",m:12,B:24,p:.10,s:.65,f:.025,actualS:.65,actualF:.025,n:3000},
    {name:"large_noisy",m:12,B:24,p:.10,s:.55,f:.10,actualS:.55,actualF:.10,n:3000},
    {name:"null_shift",m:12,B:24,p:.10,s:.65,f:.025,actualS:.65,actualF:.12,n:3000},
    {name:"root_correlated",m:12,B:24,p:.10,s:.65,f:.025,actualS:.65,actualF:.025,hot:.15,n:3000}
  ];
  const alpha=.05;
  function rng(seed){let x=seed>>>0;return ()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return (x>>>0)/4294967296}}
  const rows=[],tests=[];
  for(const c of cfgs){
    const {m,B,p,s,f,n}=c, cut=Math.log(m/alpha), lp=Math.log(s/f), ln=Math.log((1-s)/(1-f));
    const actions=["rotate","shared","iid","sprt","posterior_greedy","phoenix_lookahead",...(m===3?["exact_dp"]:[])];
    const memo=new Map();
    function stats(a,b){
      const z=a.map((v,j)=>v*lp+b[j]*ln);
      const w=z.map(v=>Math.log((1-p)+p*Math.exp(v)));
      const l=w.reduce((x,y)=>x+y,0);
      const alt=1/(1+Math.exp(-l));
      const q=z.map((v,j)=>alt*p*Math.exp(v-w[j]));
      return {z,q};
    }
    function terminal(a,b){const {z,q}=stats(a,b);let j=-1,v=0;for(let i=0;i<m;i++)if(z[i]>=cut&&2*q[i]-1>v){v=2*q[i]-1;j=i}return {j,v}}
    function expect(a,b,j,next){
      const pr=f+(s-f)*stats(a,b).q[j];a[j]++;const x=next(a,b);a[j]--;b[j]++;const y=next(a,b);b[j]--;return pr*x+(1-pr)*y
    }
    function key(a,b,t){return t+"|"+a.map((v,j)=>v+":"+b[j]).sort().join(",")}
    function exact(a,b,t){
      if(t===0)return terminal(a,b).v;
      const k=key(a,b,t);if(memo.has(k))return memo.get(k);
      let best=-Infinity,seen=new Set();for(let j=0;j<m;j++){let k2=a[j]+":"+b[j];if(seen.has(k2))continue;seen.add(k2);best=Math.max(best,expect(a,b,j,(aa,bb)=>exact(aa,bb,t-1)))}
      memo.set(k,best);return best;
    }
    // A one-step value-of-information rule with bounded local confirmation fallback.
    // Fallback scores consecutive positives needed to cross the gate, given current posterior.
    function pick(a,b,t,mode,rr,state){
      const {z,q}=stats(a,b);let best=-Infinity,jj=0;
      if(mode==="rotate")return (B-t)%m;
      if(mode==="shared")return 0;
      if(mode==="iid")return Math.floor(rr()*m);
      if(mode==="sprt"){
        while(state.j<m-1&&z[state.j]<Math.log(.2))state.j++;
        if(z[state.j]>=cut&&state.j<m-1)state.j++;
        return state.j;
      }
      for(let j=0;j<m;j++){
        let score;
        if(mode==="posterior_greedy")score=q[j];
        else if(mode==="exact_dp")score=expect(a,b,j,(aa,bb)=>exact(aa,bb,t-1));
        else {
          const vo=expect(a,b,j,(aa,bb)=>terminal(aa,bb).v);
          const need=Math.max(1,Math.ceil((cut-z[j])/lp));
          const fallback=need<=t ? (q[j]*s**need+(1-q[j])*f**need)/need : 0;
          // prefer one-step expected utility, break exact ties by potential confirmation.
          score=vo+1e-6*fallback+1e-9*q[j];
        }
        if(score>best+1e-14){best=score;jj=j}
      }return jj;
    }
    const zero=Array(m).fill(0);
    if(m===3){const v=exact([...zero],[...zero],B);tests.push({config:c.name,exact_initial_value:v,states:memo.size});if(!(v>=0&&v<=1))throw Error("DP range")}
    const aggregates=Object.fromEntries(actions.map(x=>[x,[{correct:0,wrong:0,declared:0,coverage:0},{correct:0,wrong:0,declared:0,coverage:0}]]));
    const pair=Object.fromEntries(actions.map(x=>[x,{d:0,ss:0}]));
    for(let truth=0;truth<=1;truth++)for(let i=0;i<n;i++){
      const r=rng(123457+Math.imul(i+1,2654435761)+(truth*91919));
      const valid=Array.from({length:m},()=>truth===1&&r()<p);
      const hot=Array.from({length:m},()=>r()<(c.hot||0));
      const tape=Array.from({length:m},(_,j)=>Array.from({length:B},()=>r()<(valid[j]?c.actualS:hot[j]?.30:c.actualF)));
      const outcomes={};
      for(const mode of actions){
        const a=[...zero],b=[...zero],rr=rng(9187+i*19+truth*17),state={j:0};
        for(let t=B;t>0;t--){const j=pick(a,b,t,mode,rr,state);if(!(j>=0&&j<m))throw Error("action");const x=tape[j][a[j]+b[j]];if(x)a[j]++;else b[j]++}
        if(a.reduce((x,v,j)=>x+v+b[j],0)!==B)throw Error("budget");
        const out=terminal(a,b), correct=+(out.j>=0&&valid[out.j]),wrong=+(out.j>=0&&!valid[out.j]),z=aggregates[mode][truth];z.correct+=correct;z.wrong+=wrong;z.declared+=correct+wrong;z.coverage+=a.filter((v,j)=>v+b[j]>0).length;outcomes[mode]=correct-wrong;
      }
      for(const mode of actions){const d=outcomes[mode]-outcomes.rotate;pair[mode].d+=d;pair[mode].ss+=d*d}
    }
    for(const mode of actions){const a=aggregates[mode][0],b=aggregates[mode][1],dd=pair[mode],N=2*n,delta=dd.d/N,se=Math.sqrt(Math.max(0,(dd.ss-N*delta*delta)/(N-1)/N));rows.push({config:c.name,policy:mode,m,B,n_per_truth:n,correct_false_claim:b.correct/n,wrong_root_false_claim:b.wrong/n,false_correction_true_claim:a.wrong/n,mean_utility:(b.correct-b.wrong-a.wrong)/N,coverage:(a.coverage+b.coverage)/N,paired_utility_delta_vs_rotate:delta,ci_lo:delta-1.96*se,ci_hi:delta+1.96*se})}
    if(m===3){const dp=rows.find(x=>x.config===c.name&&x.policy==="exact_dp");const v=tests.at(-1).exact_initial_value;if(Math.abs(dp.mean_utility-v)>.05)throw Error("DP simulation discrepancy");tests.at(-1).mc_value=dp.mean_utility;}
  }
  return {rows,tests,alpha,configs:cfgs,trajectories:rows.reduce((n,x)=>n+2*x.n_per_truth,0)};
}
const out=experiment();
const keys=Object.keys(out.rows[0]);
writeFileSync(new URL('results.csv',import.meta.url),[keys.join(','),...out.rows.map(r=>keys.map(k=>r[k]).join(','))].join('\n')+'\n');
writeFileSync(new URL('checks.json',import.meta.url),JSON.stringify({tests:out.tests,configs:out.configs,alpha:out.alpha,trajectories:out.trajectories},null,2)+'\n');
console.log(JSON.stringify(out,null,2));
