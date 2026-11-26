"""Synthetic stress: evidence requires independent repeated measurements; popular-query feedback.
No claim that these parameters characterize human behavior. Every query is a paid new measurement.
"""
from pathlib import Path
import numpy as np, csv
from dynamic import POLICIES
ROOT=Path(__file__).parent

def run(n,mode,seed,p,sensitivity,false_positive,threshold,truth,reinforcement=3.):
    m,k,T=12,3,8
    base=np.random.default_rng(seed); valid=base.random((n,m))<p if truth=='false_claim' else np.zeros((n,m),bool)
    u=base.random((n,T,k)); relay=base.random((n,T)); adopt=base.random((n,T))
    rng=np.random.default_rng(seed+100); perms=np.argsort(rng.random((n,m)),axis=1); ids=np.arange(n)
    counts=np.zeros((n,m),int); visits=np.zeros((n,m),int); private=np.zeros(n,bool); public=np.zeros(n,bool); accepted=np.zeros(n,bool); first=np.full(n,-1,int)
    for t in range(T):
        if mode=='shared': q=np.repeat(rng.integers(m,size=(n,1)),k,axis=1)
        elif mode=='iid': q=rng.integers(m,size=(n,k))
        elif mode=='distinct': q=np.argsort(rng.random((n,m)),axis=1)[:,:k]
        elif mode=='rotate': q=perms[:,(np.arange(k)+t*k)%m]
        elif mode=='popular':
            w=1+reinforcement*visits; cum=np.cumsum(w,axis=1); z=rng.random((n,k))*cum[:,-1,None]; q=(z[:,:,None]>=cum[:,None,:]).sum(2)
        else: raise ValueError(mode)
        hit=u[:,t]<np.where(valid[ids[:,None],q],sensitivity,false_positive)
        # Independent measurement conditional on latent root; not copies of a previous result.
        np.add.at(visits,(ids[:,None],q),1); np.add.at(counts,(ids[:,None],q),hit.astype(int))
        eligible=counts>=threshold; new=(~private)&eligible.any(1); first[new]=eligible[new].argmax(1); private|=eligible.any(1)
        public|=private&(relay[:,t]<.85); accepted|=public&(adopt[:,t]<.65)
    return dict(accepted=accepted.mean(),published=public.mean(),private=private.mean(),roots=(visits>0).sum(1).mean(),verified_root_true=(valid[ids[private],first[private]].mean() if private.any() else 0.),queries=k*T)

def main():
    n=20000; rows=[]
    for threshold in [1,2,3]:
     for truth in ['false_claim','true_claim']:
      for mode in (*POLICIES,'popular'):
       rows.append(dict(threshold=threshold,truth=truth,policy=mode,n=n,**run(n,mode,20261128,.10,.65,.025,threshold,truth)))
    with open(ROOT/'stress.csv','w',newline='') as f:
      w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    print('Stress trajectories:',len(rows)*n)
    for row in rows:
      if row['threshold'] in (1,3): print(row)
if __name__=='__main__': main()
