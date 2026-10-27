import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, statistics, random
from collections import Counter
GS=os.path.join(ROOT, "data", "gold_standard.json")
PR=os.path.join(ROOT, "rq1", "predictions_v3_fewshot_seed42.json")

SINGLE=["actor_category","action_category","asset_category","attr_conf_present",
        "attr_integrity_present","attr_avail_present","attr_conf_disclosure"]
MULTI=["actor_variety","actor_motive","action_variety","action_vector","asset_variety",
       "attr_conf_data_variety","attr_integrity_variety","attr_avail_variety"]

gold_all=json.load(open(GS)); pred=json.load(open(PR))
ids=sorted([k for k in pred if not k.startswith("_")])
gold={i:gold_all[i] for i in ids}

def f1_multi(p,g,empty_one=True):
    P,G=set(p or []),set(g or [])
    if not P and not G: return 1.0 if empty_one else None
    if not P or not G: return 0.0
    return 2*len(P&G)/(len(P)+len(G))

def rec_f1(p,g,empty_one=True):
    v=[]
    for d in SINGLE: v.append(1.0 if (p.get(d) or "")==(g.get(d) or "") else 0.0)
    for d in MULTI:
        x=f1_multi(p.get(d),g.get(d),empty_one)
        if x is not None: v.append(x)
    return statistics.mean(v) if v else None

def overall(predfn, empty_one=True):
    vals=[]
    for i in ids:
        p=predfn(i)
        r=rec_f1(p,gold[i],empty_one)
        if r is not None: vals.append(r)
    return statistics.mean(vals), vals

def boot(vals,n=10000,seed=42):
    rnd=random.Random(seed); N=len(vals)
    ms=sorted(statistics.mean(rnd.choices(vals,k=N)) for _ in range(n))
    return ms[int(.025*n)], ms[int(.975*n)]

# ---------- priors ----------
def fit_priors(train_ids):
    pri={}
    for d in SINGLE:
        pri[d]=Counter(gold[i].get(d) or "" for i in train_ids)
    for d in MULTI:
        pri[d]=Counter(tuple(sorted(gold[i].get(d) or [])) for i in train_ids)
    return pri

def majority_from(pri):
    m={}
    for d in SINGLE: m[d]=pri[d].most_common(1)[0][0]
    for d in MULTI: m[d]=list(pri[d].most_common(1)[0][0])
    return m

# B0a: oracle majority (fitted on all 72 -- upper bound for a prior predictor)
pri_all=fit_priors(ids); maj_all=majority_from(pri_all)
m,v=overall(lambda i: maj_all)
lo,hi=boot(v)
print(f"B0a oracle majority-class      : {m:.4f}  95% CI [{lo:.4f}, {hi:.4f}]")
print("    predicted constant record  :", {k:maj_all[k] for k in SINGLE})
print("    multi:", {k:maj_all[k] for k in MULTI})

# B0b: leave-one-out majority (honest, no fitting on the test record)
def loo_major(i):
    tr=[j for j in ids if j!=i]
    return majority_from(fit_priors(tr))
m2,v2=overall(loo_major)
lo2,hi2=boot(v2)
print(f"B0b LOO majority-class         : {m2:.4f}  95% CI [{lo2:.4f}, {hi2:.4f}]")

# B1: stratified random from gold marginals (LOO priors), 200 trials
trials=[]
for t in range(200):
    rnd=random.Random(1000+t)
    def sr(i,rnd=rnd):
        tr=[j for j in ids if j!=i]; pri=fit_priors(tr); out={}
        for d in SINGLE:
            ks,ws=zip(*pri[d].items()); out[d]=rnd.choices(ks,weights=ws)[0]
        for d in MULTI:
            ks,ws=zip(*pri[d].items()); out[d]=list(rnd.choices(ks,weights=ws)[0])
        return out
    trials.append(overall(sr)[0])
print(f"B1  stratified-random (200x)   : {statistics.mean(trials):.4f}  sd {statistics.pstdev(trials):.4f}  range [{min(trials):.4f}, {max(trials):.4f}]")

# framework, same scorer
mf,vf=overall(lambda i: pred[i])
lof,hif=boot(vf)
print(f"v3 few-shot framework (CLEAN)   : {mf:.4f}  95% CI [{lof:.4f}, {hif:.4f}]")

print()
print("="*78)
print("CORRECTED METRIC: empty-vs-empty pairs EXCLUDED (reviewer B point 4)")
print("="*78)
me,ve=overall(lambda i: maj_all, empty_one=False); loe,hie=boot(ve)
mfe,vfe=overall(lambda i: pred[i], empty_one=False); lofe,hife=boot(vfe)
print(f"  majority-class : {me:.4f}  CI [{loe:.4f}, {hie:.4f}]")
print(f"  framework (v3) : {mfe:.4f}  CI [{lofe:.4f}, {hife:.4f}]")

print()
print("="*78)
print("PER-DIMENSION: framework vs majority (per-record mean, empty=1)")
print("="*78)
print(f"{'dimension':28s} {'framework':>10s} {'majority':>10s} {'delta':>8s}")
wins=0
for d in SINGLE+MULTI:
    if d in SINGLE:
        fv=[1.0 if (pred[i].get(d) or '')==(gold[i].get(d) or '') else 0.0 for i in ids]
        mv=[1.0 if maj_all[d]==(gold[i].get(d) or '') else 0.0 for i in ids]
    else:
        fv=[f1_multi(pred[i].get(d),gold[i].get(d)) for i in ids]
        mv=[f1_multi(maj_all[d],gold[i].get(d)) for i in ids]
    f,m_=statistics.mean(fv),statistics.mean(mv)
    if f>m_: wins+=1
    print(f"{d:28s} {f:10.4f} {m_:10.4f} {f-m_:+8.4f}")
print(f"\nframework beats majority on {wins}/15 dimensions")

print()
print("="*78)
print("GOLD LABEL SKEW (why majority is strong)")
print("="*78)
for d in SINGLE:
    c=Counter(gold[i].get(d) or '' for i in ids)
    top,n=c.most_common(1)[0]
    print(f"{d:28s} top='{top}' {n}/72 = {n/72:.1%}   classes={len(c)}")
for d in MULTI:
    c=Counter(tuple(sorted(gold[i].get(d) or [])) for i in ids)
    top,n=c.most_common(1)[0]
    print(f"{d:28s} top={list(top)} {n}/72 = {n/72:.1%}")
