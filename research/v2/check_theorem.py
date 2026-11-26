"""PHOENIX-R V2: exact finite-model checks, not human or LLM evidence."""
from itertools import combinations,product
from math import comb,log
import numpy as np
from scipy.optimize import linprog
from scipy.special import rel_entr
from pathlib import Path
import csv

OUT=Path(__file__).parent

def kl(p,q):
    return float(sum(rel_entr([p,1-p],[q,1-q])))

def check(m,r,e,gamma,cD):
    S=list(combinations(range(m),r)); M=len(S); sets=[a for s in range(r,m+1) for a in combinations(range(m),s)]
    d=-.5*np.log1p(-e*e); h=kl(2.**(-r),2.**(-r)*(1+e))
    costs=np.array([len(a)**gamma for a in sets]+[cD]*M)
    D=np.array([[d*(set(s)<=set(a)) for a in sets]+[h*(s==t) for t in S] for s in S])
    # one unit of total cost, maximize smallest KL over alternatives
    R=linprog(np.r_[np.zeros(len(costs)),-1],A_ub=np.c_[-D,np.ones(M)],b_ub=np.zeros(M),A_eq=np.array([np.r_[costs,0]]),b_eq=[1],bounds=(0,None),method='highs')
    assert R.success
    options=[(d*comb(s,r)/M/s**gamma, f'vector_{s}') for s in range(r,m+1)]+[(h/M/cD,'direct')]
    eta,mode=max(options)
    assert np.isclose(R.x[-1],eta,rtol=1e-7,atol=1e-10)
    # exact distribution marginals and KL for all actions against one representative alternative
    x=np.array(list(product([0,1],repeat=m))); p=np.ones(len(x))/len(x); chi=(-1.)**x[:,S[0]].sum(axis=1); q=p*(1+e*chi)
    assert np.isclose(q.sum(),1)
    for a in sets:
        idx=x[:,a]@2**np.arange(len(a)); u=np.bincount(idx,weights=p,minlength=2**len(a)); v=np.bincount(idx,weights=q,minlength=2**len(a))
        assert np.isclose(sum(rel_entr(u,v)),d*(set(S[0])<=set(a)))
    for s in S:
        failure=(x[:,s]==0).all(axis=1); assert np.isclose(kl(p@failure,q@failure),h*(s==S[0]))
    return dict(m=m,r=r,epsilon=e,gamma=gamma,direct_cost=cD,alternatives=M,eta=eta,lp_eta=R.x[-1],best=mode,lower_bound_95pct=kl(.95,.05)/eta,full_vector_eta=d/m**gamma,direct_eta=h/M/cD)

if __name__=='__main__':
    rows=[check(m,r,e,g,c) for m,r in [(5,2),(6,3),(8,3),(8,4)] for e in [.2,.6,.85] for g in [1,2,4,8] for c in [.01,1,100]]
    with (OUT/'frontier.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    print('Exact checks passed:',len(rows),'LP instances; all vector/direct channel KL identities checked by enumeration.')
    for row in rows:
        if row['m']==8 and row['r']==3 and row['epsilon']==.6 and row['direct_cost']==1: print(row)
