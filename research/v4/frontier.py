"""Exact nonadaptive repeated-measurement frontier. Exhaustive small-instance oracle."""
from pathlib import Path
import math,csv,itertools
import numpy as np
ROOT=Path(__file__).parent

def tail(n,p,h):return sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(h,n+1))
def score(counts,p,s,f,h):
    good=[tail(n,s,h) for n in counts]; bad=[tail(n,f,h) for n in counts]
    return (1-math.prod(1-p*a-(1-p)*b for a,b in zip(good,bad)),1-math.prod(1-b for b in bad))
def partitions(total,m,minimum=0):
    if m==1:
        if total>=minimum:yield (total,)
        return
    for a in range(minimum,total//m+1):
        for b in partitions(total-a,m-1,a):yield (a,*b)
def main():
    rows=[]; checks=0
    for m in [4,6,12]:
     for B in [6,12,24]:
      for h in [1,2,3]:
       for cap in [.001,.01,.05,.5]:
        allrows=[(score(c,.1,.65,.025,h),c) for c in partitions(B,m)]
        good=[(x,c) for x,c in allrows if x[1]<=cap+1e-12]
        if good:
         (hit,fp),c=max(good);rows.append(dict(m=m,budget=B,threshold=h,false_cap=cap,discovery=hit,false_discovery=fp,counts=' '.join(map(str,c)),feasible=True))
        else: rows.append(dict(m=m,budget=B,threshold=h,false_cap=cap,discovery='',false_discovery='',counts='',feasible=False))
        checks+=len(allrows)
    with open(ROOT/'allocation_frontier.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    print(f'{checks} allocation evaluations, {len(rows)} settings')
    for r in rows:
        if r['m']==12 and r['budget']==24 and r['false_cap']==.01:print(r)
if __name__=='__main__':main()
