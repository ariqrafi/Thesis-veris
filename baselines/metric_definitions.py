"""Table 4 (five aggregate definitions x B0/v3/v2/v1) and the oracle-abstention
counterfactual (0.6841 -> 0.8726) reported in the ARTMAN 2026 paper.

Oracle abstention: substitute the gold value only where the gold is Unknown
(single-valued) or empty / contains Unknown (multi-valued); every other
prediction is left untouched.
"""
import json, os, statistics, random
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = ROOT
gold=json.load(open(f"{B}/data/gold_standard.json"))
P={ "v1 zero-shot": f"{B}/rq1/predictions_seed42.json",
    "v2 structural": f"{B}/rq1/predictions_v2_seed42.json",
    "v3 few-shot":  f"{B}/rq1/predictions_v3_fewshot_seed42.json"}
preds={k:json.load(open(v)) for k,v in P.items()}
ids=sorted(k for k in preds["v3 few-shot"] if not k.startswith("_"))
SINGLE=["actor_category","action_category","asset_category","attr_conf_present","attr_integrity_present","attr_avail_present","attr_conf_disclosure"]
MULTI=["actor_variety","actor_motive","action_variety","action_vector","asset_variety","attr_conf_data_variety","attr_integrity_variety","attr_avail_variety"]
CORE=["actor_category","action_category","asset_category","attr_conf_present","attr_integrity_present","attr_avail_present"]

maj={d:Counter(gold[i].get(d) or '' for i in ids).most_common(1)[0][0] for d in SINGLE}
maj.update({d:list(Counter(tuple(sorted(gold[i].get(d) or [])) for i in ids).most_common(1)[0][0]) for d in MULTI})

def f1m(p,g,e1=True):
    P_,G=set(p or []),set(g or [])
    if not P_ and not G: return 1.0 if e1 else None
    if not P_ or not G: return 0.0
    return 2*len(P_&G)/(len(P_)+len(G))

def M_perrecord(get,e1=True,dims=None):
    dims=dims or (SINGLE+MULTI); v=[]
    for i in ids:
        p=get(i); d=[]
        for x in dims:
            if x in SINGLE: d.append(1.0 if (p.get(x) or '')==(gold[i].get(x) or '') else 0.0)
            else:
                z=f1m(p.get(x),gold[i].get(x),e1)
                if z is not None: d.append(z)
        if d: v.append(statistics.mean(d))
    return statistics.mean(v)

def M_perdim(get,e1=True,dims=None):
    dims=dims or (SINGLE+MULTI); out=[]
    for x in dims:
        if x in SINGLE: out.append(statistics.mean(1.0 if (get(i).get(x) or '')==(gold[i].get(x) or '') else 0.0 for i in ids))
        else:
            vals=[f1m(get(i).get(x),gold[i].get(x),e1) for i in ids]
            vals=[z for z in vals if z is not None]
            if vals: out.append(statistics.mean(vals))
    return statistics.mean(out)

MET=[("per-record mean, empty=1  (paper)", lambda g: M_perrecord(g,True)),
     ("per-record mean, empty excl.",      lambda g: M_perrecord(g,False)),
     ("mean over dimensions, empty=1",     lambda g: M_perdim(g,True)),
     ("mean over dimensions, empty excl.", lambda g: M_perdim(g,False)),
     ("Core-A4 only (6 category dims)",    lambda g: M_perrecord(g,True,CORE))]

print("=== 1. Is the finding specific to one metric definition? ===")
print(f"{'metric':38s} {'majority':>9s} {'v3':>8s} {'v2':>8s} {'v1':>8s}  baseline wins?")
for name,fn in MET:
    m=fn(lambda i: maj); v3=fn(lambda i: preds['v3 few-shot'][i])
    v2=fn(lambda i: preds['v2 structural'][i]); v1=fn(lambda i: preds['v1 zero-shot'][i])
    print(f"{name:38s} {m:9.4f} {v3:8.4f} {v2:8.4f} {v1:8.4f}   {'YES' if m>max(v1,v2,v3) else 'no'}")

print()
print("=== 2. Cost of under-abstention (oracle-abstention counterfactual) ===")
def oracle_abst(i):
    p=dict(preds['v3 few-shot'][i]); g=gold[i]
    for x in SINGLE:
        if (g.get(x) or '')=='Unknown': p[x]='Unknown'
    for x in MULTI:
        gv=g.get(x) or []
        if (not gv) or ('Unknown' in gv): p[x]=list(gv)
    return p
base=M_perrecord(lambda i: preds['v3 few-shot'][i])
orc =M_perrecord(oracle_abst)
print(f"  v3 as-is                      : {base:.4f}")
print(f"  v3 + perfect abstention       : {orc:.4f}   (+{orc-base:.4f})")
print(f"  majority baseline             : {M_perrecord(lambda i: maj):.4f}")
print(f"  -> under-abstention accounts for {orc-base:.4f} F1, i.e. {100*(orc-base)/base:.1f}% of current score")
