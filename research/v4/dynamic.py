"""PHOENIX-R V4: finite persistent source bank, controlled repair coupling.
Synthetic agents, not human or LLM participants. All policy arms use k*T queries.
"""
from pathlib import Path
import argparse, csv, math
import numpy as np
ROOT=Path(__file__).parent
POLICIES=('shared','iid','distinct','rotate')

def coverage_step(m,k,mode):
    # Transition for number of distinct queried roots. Shared: k repeated queries.
    P=np.zeros((m+1,m+1))
    if mode=='iid':
        Q=coverage_step(m,1,'shared'); return np.linalg.matrix_power(Q,k)
    if mode=='shared': k=1
    for u in range(m+1):
        if mode=='rotate': P[u,min(m,u+k)]=1; continue
        for j in range(max(0,k-u),min(k,m-u)+1):
            P[u,u+j]=math.comb(m-u,j)*math.comb(u,k-j)/math.comb(m,k)
    assert np.allclose(P.sum(1),1)
    return P

def exact(m,k,T,p,relay,uptake,mode):
    P=coverage_step(m,k,mode); z=np.zeros(m+1); z[0]=1
    S=[1.]; mean_roots=[]
    for _ in range(T):
        z=z@P; S.append(float(z@((1-p)**np.arange(m+1)))); mean_roots.append(float(z@np.arange(m+1)))
    # First discovery time d, then geometric waiting for relay, then geometric uptake.
    D=np.array(S[:-1])-np.array(S[1:]); public=np.zeros(T); recovery=np.zeros(T)
    for t in range(1,T+1):
        public[t-1]=sum(D[d-1]*(1-(1-relay)**(t-d+1)) for d in range(1,t+1))
        recovery[t-1]=sum(D[d-1]*sum((1-relay)**(j-d)*relay*(1-(1-uptake)**(t-j+1)) for j in range(d,t+1)) for d in range(1,t+1))
    return np.array(1-np.array(S[1:])), public,recovery,np.array(mean_roots)

def run(m,k,T,p,relay,uptake,mode,n,seed,feedback=False,visibility=(.8,.8)):
    # Preassigned persistent evidence roots; a repeated query cannot generate a new root.
    # Independent random streams: identical ground truth and relay/uptake draws across arms.
    base=np.random.default_rng(seed); informative=base.random((n,m))<p
    relay_u=base.random((n,T)); uptake_u=base.random((n,T)); log_u=base.random((n,T))
    rng=np.random.default_rng(seed+100); perms=np.argsort(rng.random((n,m)),axis=1)
    checked=np.zeros((n,m),bool); private=np.zeros(n,bool); public=np.zeros(n,bool); adopted=np.zeros(n,bool); source=np.full(n,-1,int)
    rows=[]; ids=np.arange(n)
    for t in range(T):
        if mode=='shared': q=np.repeat(rng.integers(m,size=(n,1)),k,axis=1)
        elif mode=='iid': q=rng.integers(m,size=(n,k))
        elif mode=='distinct': q=np.argsort(rng.random((n,m)),axis=1)[:,:k]
        else: q=perms[:,(np.arange(k)+t*k)%m]
        if feedback: q[public]=source[public,None] # archive-first subsequent retrieval, not independent evidence
        checked[ids[:,None],q]=True
        hit=informative[ids[:,None],q]; new=(~private)&hit.any(1)
        source[new]=q[new,hit[new].argmax(1)]; private|=hit.any(1)
        public|=private&(relay_u[:,t]<relay)
        adopted|=public&(uptake_u[:,t]<uptake)
        # Logging does NOT change archive; outcomes may be selectively observed.
        log=log_u[:,t]<np.where(adopted,visibility[1],visibility[0])
        rows.append(dict(round=t+1,discovered=private.mean(),published=public.mean(),recovered=adopted.mean(),roots=checked.sum(1).mean(),route_hit=hit.mean(),logged=log.mean(),logged_recovery=adopted[log].mean() if log.any() else float('nan'),queries=k*(t+1)))
    return rows,adopted

def save(name,rows):
    with open(ROOT/name,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main(n=20000):
    # 3 evidence prevalences, 2 relay regimes, 4 policies, 2 feedback regimes;
    # p=.02 can also represent spurious proof acceptance on true-claim controls.
    rows=[]; contrasts=[]; checks=0
    for p in [.02,.10,.25]:
      for relay in [.25,.85]:
       for feedback in [False,True]:
        endpoints={}
        for mode in POLICIES:
         sim,end=run(12,3,8,p,relay,.65,mode,n,20261126,feedback,(.8,.4)); endpoints[mode]=end
         ex=exact(12,3,8,p,relay,.65,mode)
         for i,a in enumerate(sim):
          for j,key in enumerate(['discovered','published','recovered']):
           val=ex[j][i]; se=math.sqrt(max(val*(1-val),1/n)/n)
           assert abs(a[key]-val)<6*se+.001,(p,relay,mode,feedback,key,i,a[key],val)
           checks+=1
          if not feedback: assert abs(a['roots']-ex[3][i])<.15; checks+=1
          rows.append(dict(p=p,relay=relay,feedback=feedback,policy=mode,n=n,**a,exact_discovery=ex[0][i],exact_publication=ex[1][i],exact_recovery=ex[2][i]))
        for mode in POLICIES[1:]:
         diff=endpoints[mode].astype(int)-endpoints['shared'].astype(int); mu=diff.mean(); se=diff.std(ddof=1)/math.sqrt(n)
         contrasts.append(dict(p=p,relay=relay,feedback=feedback,contrast=mode+'-shared',n=n,difference=mu,ci_low=mu-1.96*se,ci_high=mu+1.96*se))
    save('trajectory.csv',rows);save('paired_contrasts.csv',contrasts)
    # Analytical marginal equality for each route: uniform root id; permutation/rotation preserves it.
    for m in range(3,14):
      for k in range(1,m+1):
       a=[exact(m,k,6,.1,.4,.7,s)[2][-1] for s in POLICIES]
       assert all(x<=y+1e-12 for x,y in zip(a,a[1:])),(m,k,a);checks+=1
    print(f'PASS {checks} exact/Monte Carlo/order checks; {3*2*2*4*n:,} synthetic room-policy trajectories; {len(rows)} aggregate trajectory rows')
    for a in rows:
     if a['p']==.1 and a['relay']==.85 and a['feedback'] and a['round']==8: print(a)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=20000);main(p.parse_args().n)
