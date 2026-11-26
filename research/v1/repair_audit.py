"""Synthetic, deliberately constructed repair-route audit. Not human/LLM evidence.
Python 3, numpy, scipy. Run: python repair_audit.py
"""
from itertools import product, combinations
from pathlib import Path
import csv
import numpy as np
from scipy.optimize import linprog
from scipy.stats import beta

STATES=np.array(list(product([0,1],repeat=3)))
PARITY=STATES.sum(1)%2
UNION=STATES.any(1).astype(int)
M=np.vstack([np.ones(8), *[np.prod(STATES[:,list(s)],axis=1) for k in (1,2) for s in combinations(range(3),k)]])
TARGET=np.array([1,.5,.5,.5,.25,.25,.25])
ALT=.875

def parity_world(theta):
    return np.where(PARITY==1,theta/4,(1-theta)/4)

def bounds(order):
    n={1:4,2:7}[order]
    lo=linprog(UNION,A_eq=M[:n],b_eq=TARGET[:n],bounds=(0,None),method='highs')
    hi=linprog(-UNION,A_eq=M[:n],b_eq=TARGET[:n],bounds=(0,None),method='highs')
    assert lo.success and hi.success
    return lo.fun,-hi.fun

def cp(k,n):
    k=np.asarray(k); lo=np.zeros_like(k,dtype=float); hi=np.ones_like(k,dtype=float)
    a=k>0; b=k<n
    lo[a]=beta.ppf(.025,k[a],n-k[a]+1)
    hi[b]=beta.ppf(.975,k[b]+1,n-k[b]); return lo,hi

def run():
    rng=np.random.default_rng(20261126)
    worlds={f'parity_theta_{t}':parity_world(t) for t in (0,.1,.45,.5,.55,.9,1)}
    drift=np.zeros(8);drift[0]=.2;drift[-1]=.8;worlds['structural_violation']=drift
    assert np.allclose(bounds(1),(.5,1)) and np.allclose(bounds(2),(.75,1))
    for t in (0,.1,.45,.5,.55,.9,1):
        p=parity_world(t); assert np.allclose(M@p,TARGET)
        assert np.isclose(p@UNION,.75+.25*t)
    print('Exact bounds: marginal',bounds(1),'pairwise',bounds(2))
    print('All parity worlds share all marginal and pairwise distributions.')
    rows=[]; R=4000
    for name,p in worlds.items():
        true=float(p@UNION)
        for n in (25,100,400,1600):
            c=rng.multinomial(n,p,size=R)
            for method in ('direct_union_CP','parity_structural_CP'):
                if method=='direct_union_CP': lo,hi=cp(c@UNION,n)
                else:
                    lo,hi=cp(c@PARITY,n);lo=.75+.25*lo;hi=.75+.25*hi
                adopt=lo>ALT; reject=hi<ALT
                row=dict(world=name,n=n,trials=R,method=method,true_success=true,coverage=float(((lo<=true)&(true<=hi)).mean()),adopt=float(adopt.mean()),reject=float(reject.mean()),undecided=float((~(adopt|reject)).mean()),mean_width=float((hi-lo).mean()),mean_regret=float((np.maximum(true,ALT)-np.where(adopt,true,ALT)).mean()))
                rows.append(row)
    out=Path(__file__).with_name('results.csv')
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    for row in rows:
        if row['n'] in (100,400) and row['world'] in ('parity_theta_0.1','parity_theta_0.9','parity_theta_0.5','structural_violation'):
            print(row['world'],row['n'],row['method'],'true',round(row['true_success'],3),'adopt',round(row['adopt'],4),'reject',round(row['reject'],4),'coverage',round(row['coverage'],4),'width',round(row['mean_width'],4))
    print('Wrote',len(rows),'rows;',len(worlds)*4*R,'simulated trials (two paired methods per trial).')
if __name__=='__main__': run()
