"""Text-based closed-world verification pilot; optional OpenAI-compatible local server.
Default scripted backend is executable without model weights; LLM backend is untested here.
All claims and records are fictional. No live web or human data.
"""
import argparse,json,os,urllib.request,random
from pathlib import Path
ROOT=Path(__file__).parent

def scripted(claim,records):
    for r in records:
        if r['text'].startswith('Audited record:'):
            val=int(r['text'].split('value = ')[1].split('.')[0]); expected=int(claim.split('value = ')[1].split('.')[0]);return {'verdict':'refute' if val!=expected else 'support','source_id':r['id']}
    return {'verdict':'insufficient','source_id':None}

def local_model(claim,records,endpoint,model):
    prompt={'claim':claim,'records':records,'task':'These are fictional closed-world records. Classify using only the supplied records. Return JSON with verdict support, refute, or insufficient and source_id (null if insufficient).'}
    data={'model':model,'messages':[{'role':'user','content':json.dumps(prompt)}],'temperature':0,'max_tokens':180}
    headers={'Content-Type':'application/json'}
    if os.getenv('LOCAL_LLM_API_KEY'):headers['Authorization']='Bearer '+os.environ['LOCAL_LLM_API_KEY']
    with urllib.request.urlopen(urllib.request.Request(endpoint,data=json.dumps(data).encode(),headers=headers),timeout=120) as r: raw=json.load(r)['choices'][0]['message']['content']
    try:
        z=json.loads(raw); assert z['verdict'] in ['support','refute','insufficient']; assert z.get('source_id') is None or isinstance(z['source_id'],str);return z
    except (ValueError,TypeError,KeyError,AssertionError): return {'verdict':'invalid','source_id':None,'raw':raw}

def scene(idx,mode,backend,T=8):
    rng=random.Random(5000+idx); actual=rng.randrange(10,100); false=idx%2==0; stated=actual+1 if false else actual
    claim=f'Fictional registry R{idx}: value = {stated}.'; roots=[]; informative=set(rng.sample(range(12),2))
    for j in range(12):roots.append({'id':f'R{idx}-S{j}','text':f'Audited record: registry R{idx}, value = {actual}.' if j in informative else f'Registry R{idx}: record {j} contains only unrelated administrative metadata.'})
    sched=random.Random(9000+idx); perm=list(range(12));sched.shuffle(perm); archive=[]; trace=[]; ever=False; false_correction=False
    for t in range(T):
        if mode=='shared': q=[sched.randrange(12)]*3
        elif mode=='iid':q=[sched.randrange(12) for _ in range(3)]
        elif mode=='distinct':q=sched.sample(range(12),3)
        else:q=[perm[(t*3+j)%12] for j in range(3)]
        prior=list(archive); pending=[]; round_calls=[]
        for root in q:
            visible=[roots[root]]+prior; out=backend(claim,visible); round_calls.append({'source':roots[root]['id'],'output':out})
            # Gold gate: only a cited refuting audited record that was actually visible may enter archive.
            if false and out.get('verdict')=='refute' and any(v['id']==out.get('source_id') and v['text'].startswith('Audited record:') for v in visible):
                pending.extend(v for v in visible if v['id']==out['source_id'])
        archive=list({v['id']:v for v in prior+pending}.values()); downstream=backend(claim,archive)
        refute=downstream.get('verdict')=='refute'; grounded=refute and any(v['id']==downstream.get('source_id') and v['text'].startswith('Audited record:') for v in archive); ever|=false and grounded; false_correction|=(not false) and refute
        trace.append({'round':t+1,'calls':round_calls,'archive_ids':[v['id'] for v in archive],'downstream':downstream})
    return {'case':idx,'policy':mode,'initial_claim_false':false,'ever_recovered':bool(ever),'false_correction':bool(false_correction),'queries':3*T,'trace':trace}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--backend',choices=['scripted','llm'],default='scripted');ap.add_argument('--endpoint',default='http://localhost:8000/v1/chat/completions');ap.add_argument('--model');ap.add_argument('--cases',type=int,default=40);args=ap.parse_args()
    if args.backend=='llm' and not args.model:ap.error('--model required for llm backend')
    backend=scripted if args.backend=='scripted' else lambda c,r:local_model(c,r,args.endpoint,args.model)
    results=[scene(i,m,backend) for i in range(args.cases) for m in ['shared','iid','distinct','rotate']]
    path=ROOT/f'text_{args.backend}.jsonl';path.write_text(''.join(json.dumps(r)+'\n' for r in results));
    for mode in ['shared','iid','distinct','rotate']:
        rr=[r for r in results if r['policy']==mode]; pos=[r for r in rr if r['initial_claim_false']]; neg=[r for r in rr if not r['initial_claim_false']]; print(mode,sum(r['ever_recovered'] for r in pos),len(pos),'false corrections',sum(r['false_correction'] for r in neg),len(neg))
    if args.backend=='scripted': assert not any(r['false_correction'] for r in results); assert all(r['ever_recovered'] for r in results if r['policy']=='rotate' and r['initial_claim_false'])
if __name__=='__main__':main()
