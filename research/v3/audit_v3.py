"""PHOENIX-R V3: exact finite-law visibility checks and sequential synthetic audits."""
import itertools as it, math, csv
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.special import rel_entr
from scipy.stats import beta
ROOT=Path(__file__).parent

def kl(p,q):
    p,q=np.asarray(p,float),np.asarray(q,float)
    return float(np.sum(rel_entr(p,q)))
def binarykl(p,q): return kl([p,1-p],[q,1-q])
def states(m): return np.array(list(it.product([0,1],repeat=m)),dtype=np.int8)
def subsets(m,r): return list(it.combinations(range(m),r))
def law(x,S,e): return (1+e*(1-2*(x[:,S].sum(1)%2)))/len(x)
def aggregate(x,p,A,kind):
    if kind=='direct':
        f=(x[:,A].sum(1)==0); return np.array([p[f].sum(),p[~f].sum()])
    ind=x[:,A]@ (2**np.arange(len(A)))
    return np.bincount(ind,weights=p,minlength=2**len(A))

def check():
    rng=np.random.default_rng(20261126); nb=0; nf=0; nk=0; rows=[]
    # Sharp equivalence criterion for heterogeneous finite laws, prescribed coverage.
    for _ in range(160):
        n=int(rng.integers(2,12)); H=int(rng.integers(2,5)); p=rng.dirichlet(np.ones(n),size=H)
        l=float(rng.uniform(0,.35)); u=float(rng.uniform(l+.05,1)); rho=float(rng.uniform(0,1))
        L=l*p.max(0); U=u*p.min(0)
        predicted=bool(np.all(L<=U+1e-10) and L.sum()<=rho+1e-10 and rho<=U.sum()+1e-10)
        # Explicit independent inequalities, not using the compressed bounds.
        z=linprog(np.zeros(n),A_ub=np.vstack([np.eye(n) for _ in range(H)]+[-np.eye(n) for _ in range(H)]),b_ub=np.r_[u*p.ravel(),-l*p.ravel()],A_eq=np.ones((1,n)),b_eq=[rho],bounds=(0,None),method='highs')
        assert predicted==z.success; nb+=1
    # Include constructive feasible/boundary instances, not only random infeasible cases.
    for m in [3,4,5,6]:
      x=states(m); p0=np.ones(len(x))/len(x)
      for r in range(2,m+1):
       menu=subsets(m,r); M=len(menu); S=menu[0]
       for e in [.15,.35,.55]:
        ps=law(x,S,e)
        for frac in [.15,.65,.95]:
         rho=(1-e)*frac; a=1-rho; ep=e/a; q=rho*p0
         assert np.all(q<=ps) and np.allclose(q+ (ps-q),ps)
         assert np.allclose((ps-q)/a,law(x,S,ep)); assert np.isclose(q.sum(),rho)
         d=-.5*np.log1p(-ep**2); h=binarykl(2**(-r),(1+ep)*2**(-r))
         p1=(ps-q)/a
         for s in range(1,m+1):
          for A in subsets(m,s):
           div=kl(aggregate(x,p0,A,'vector'),aggregate(x,p1,A,'vector'))
           assert np.isclose(div,d if set(S)<=set(A) else 0,atol=1e-10); nk+=1
         for A in menu:
          assert np.isclose(kl(aggregate(x,p0,A,'direct'),aggregate(x,p1,A,'direct')),h if A==S else 0,atol=1e-10); nk+=1
         for gamma in [1,3]:
          for cd in [.1,2]:
           b=.2; acts=[('vector',A,len(A)**gamma) for s in range(r,m+1) for A in subsets(m,s)]+[('direct',A,cd) for A in menu]
           D=np.array([[ (d if set(T)<=set(A) else 0) if kind=='vector' else (h if T==A else 0) for kind,A,c in acts] for T in menu]); costs=np.array([c+b/a for _,_,c in acts]); Z=D/costs
           opt=linprog(np.r_[np.zeros(len(acts)),-1],A_ub=np.c_[-Z,np.ones(M)],b_ub=np.zeros(M),A_eq=[np.r_[np.ones(len(acts)),0]],b_eq=[1],bounds=[(0,None)]*len(acts)+[(None,None)],method='highs')
           rates=[(d*math.comb(s,r)/(M*(s**gamma+b/a)),f'vector_{s}') for s in range(r,m+1)]+[(h/(M*(cd+b/a)),'direct')]; eta,typ=max(rates)
           assert opt.success and np.isclose(opt.x[-1],eta,rtol=1e-8,atol=1e-10); nf+=1
           rows.append(dict(m=m,r=r,epsilon=e,rho=rho,gamma=gamma,direct_cost=cd,eta=eta,lp_eta=opt.x[-1],best=typ))
    print(f'PASS: {nb} visibility feasibility LPs; {nf} frontier LPs; {nk} KL identities')
    write('frontier_v3.csv',rows)

def write(name,rows):
    with open(ROOT/name,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def simulate():
    # Fresh iid scenes, common public law, valid conditional likelihoods.
    # Budget in abstract cost units, no claim of real human expenses.
    m,r,e,rho=5,3,.4,.5; a=1-rho; ep=e/a; menu=subsets(m,r); M=len(menu); x=states(m); p0=np.ones(len(x))/len(x); ps=law(x,menu[0],e); parity=np.array([1-2*(x[:,S].sum(1)%2) for S in menu]).T
    fail=np.array([x[:,S].sum(1)==0 for S in menu]).T; N=2000; delta=.05; b=.2; rows=[]
    # Strategies all observe the same public logs. Public-only cannot validly decide.
    # Randomized audit each scene regardless of missing (wastes paid readout on logged scenes);
    # targeted audit on missing; unconditional direct gold ignores public mask (strong direct baseline).
    for cd in [.15,1.0]:
      for budget in [100.,300.]:
       for w in ['safe','unsafe','offmodel_pair']:
        p=p0 if w=='safe' else ps if w=='unsafe' else law(x,(0,1),e); missing=(p-rho*p0)/a
        for strategy in ['public_only','vector_all','vector_missing','direct_missing','direct_gold']:
         rng=np.random.default_rng(3300+int(cd*100)+int(budget)+['safe','unsafe','offmodel_pair'].index(w)*10000+['public_only','vector_all','vector_missing','direct_missing','direct_gold'].index(strategy))
         L=np.zeros((N,M)); cost=np.zeros(N); decision=np.zeros(N,dtype=np.int8); steps=np.zeros(N,dtype=int)
         readcost=5 if strategy.startswith('vector') else cd
         if strategy!='public_only':
          while True:
           # Reserve maximum next-scene cost, no overspend or outcome-dependent stopping before record.
           ids=np.flatnonzero((decision==0)&(cost+b+readcost<=budget+1e-9))
           if not len(ids): break
           k=len(ids); miss=rng.random(k)<a; ix=np.empty(k,dtype=int); ix[miss]=rng.choice(len(x),size=miss.sum(),p=missing); ix[~miss]=rng.choice(len(x),size=(~miss).sum(),p=p0)
           cost[ids]+=b; steps[ids]+=1
           if strategy=='vector_all':
            cost[ids]+=readcost; j=ids[miss]; L[j]-=np.log1p(ep*parity[ix[miss]])
           elif strategy=='vector_missing':
            j=ids[miss]; cost[j]+=readcost; L[j]-=np.log1p(ep*parity[ix[miss]])
           else:
            audit=miss if strategy=='direct_missing' else np.ones(k,dtype=bool); j=ids[audit]; cost[j]+=readcost
            T=rng.integers(M,size=len(j)); f=fail[ix[audit],T]; pp=2**(-r); ee=ep if strategy=='direct_missing' else e
            L[j,T]+=np.where(f,-np.log1p(ee),np.log((1-pp)/(1-(1+ee)*pp)))
           reject=(L[ids]<=-math.log(M/delta)).any(1); cert=(L[ids]>=math.log(1/delta)).all(1)
           decision[ids[reject]]=-1; decision[ids[cert & ~reject]]=1
         rows.append(dict(world=w,direct_cost=cd,budget=budget,strategy=strategy,trials=N,certify=(decision==1).mean(),reject=(decision==-1).mean(),undecided=(decision==0).mean(),mean_cost=cost.mean(),mean_scenes=steps.mean()))
    write('sequential_results.csv',rows)
    print('Synthetic trials:',sum(v['trials'] for v in rows))
    for v in rows:
        if v['budget']==300 and v['direct_cost']==1: print(v)

def robust_check():
    m,r,e,rho=5,3,.4,.5; a=1-rho; menu=subsets(m,r); M=len(menu); x=states(m); p0=np.ones(len(x))/len(x); fail=np.array([x[:,S].sum(1)==0 for S in menu]).T; N=2000; rows=[]; threshold=.15; delta=.05; b=.2; cd=1.
    rng=np.random.default_rng(20261127)
    for w in ['safe','unsafe','offmodel_pair']:
     p=p0 if w=='safe' else law(x,menu[0] if w=='unsafe' else (0,1),e); missing=(p-rho*p0)/a; probs=missing@fail
     for budget in [300,3000,10000]:
      for strategy in ['robust_vector_missing','robust_direct_missing']:
       if strategy=='robust_vector_missing':
        n=int(budget/(5+b/a)); k=rng.multinomial(n,missing,size=N)@fail
        expected_cost=n*(5+b/a)
       else:
        n=int(budget/(M*(cd+b/a))); k=rng.binomial(n,probs,size=(N,M)); expected_cost=n*M*(cd+b/a)
       # Oracle known common public conditional law and coverage; only missing distribution unrestricted.
       # Simultaneous one-sided intervals in each direction, separate error guarantees.
       lo=np.where(k==0,0,beta.ppf(delta/M,k,n-k+1)); hi=np.where(k==n,1,beta.ppf(1-delta/M,k+1,n-k)); lo=rho*2**(-r)+a*lo; hi=rho*2**(-r)+a*hi
       cert=(hi<=threshold).all(1); rej=(lo>threshold).any(1); assert not np.any(cert&rej)
       rows.append(dict(world=w,expected_budget=budget,strategy=strategy,trials=N,certify=cert.mean(),reject=rej.mean(),undecided=(~(cert|rej)).mean(),expected_cost=expected_cost,n_per_portfolio=n,largest_true_failure=(p@fail).max()))
    write('robust_results.csv',rows)
    print('Robust fixed-audit trials:',sum(v['trials'] for v in rows))
    for v in rows:
     if v['expected_budget']==10000: print(v)

if __name__=='__main__': check(); simulate(); robust_check()
