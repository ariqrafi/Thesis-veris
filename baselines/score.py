import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, statistics
GS=os.path.join(ROOT, "data", "gold_standard.json")
PR=os.path.join(ROOT, "rq3", "predictions", "A1_seed42.json")
SC=os.path.join(ROOT, "rq3", "scenario_scores.json")

SINGLE=["actor_category","action_category","asset_category","attr_conf_present",
        "attr_integrity_present","attr_avail_present","attr_conf_disclosure"]
MULTI=["actor_variety","actor_motive","action_variety","action_vector","asset_variety",
       "attr_conf_data_variety","attr_integrity_variety","attr_avail_variety"]
DIMS=SINGLE+MULTI

gold=json.load(open(GS)); pred=json.load(open(PR)); sc=json.load(open(SC))
ids=[k for k in pred if not k.startswith("_")]
print("n pred ids",len(ids))
ins=[k for k,v in gold.items() if v.get("in_scope")=="Yes"]
print("in_scope gold:",len(ins))
print("pred ids subset of in_scope:", set(ids)<=set(ins))

def f1_multi(p,g,empty_is_one=True):
    P,G=set(p or []),set(g or [])
    if not P and not G: return 1.0 if empty_is_one else None
    if not P or not G: return 0.0
    i=len(P&G)
    return 2*i/(len(P)+len(G))

def rec_f1(p,g,empty_is_one=True):
    vals=[]
    for d in SINGLE:
        vals.append(1.0 if (p.get(d) or "")==(g.get(d) or "") else 0.0)
    for d in MULTI:
        v=f1_multi(p.get(d),g.get(d),empty_is_one)
        if v is not None: vals.append(v)
    return statistics.mean(vals) if vals else None

per=[rec_f1(pred[i],gold[i]) for i in ids]
print("mean over records (empty=1):", round(statistics.mean(per),4))
print("target A1 overall_macro_f1  :", sc["A1"]["overall_macro_f1"])
