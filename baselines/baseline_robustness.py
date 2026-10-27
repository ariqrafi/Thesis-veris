import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, statistics
from collections import Counter
B=ROOT
gold=json.load(open(f"{B}/data/gold_standard.json"))
clean=json.load(open(f"{B}/rq1/predictions_v3_fewshot_seed42.json"))
ids=sorted(k for k in clean if not k.startswith("_"))
SINGLE=["actor_category","action_category","asset_category","attr_conf_present",
        "attr_integrity_present","attr_avail_present","attr_conf_disclosure"]
MULTI=["actor_variety","actor_motive","action_variety","action_vector","asset_variety",
       "attr_conf_data_variety","attr_integrity_variety","attr_avail_variety"]

RECORD_TETAP={d:Counter(gold[i].get(d) or '' for i in ids).most_common(1)[0][0] for d in SINGLE}
RECORD_TETAP.update({d:list(Counter(tuple(sorted(gold[i].get(d) or [])) for i in ids).most_common(1)[0][0]) for d in MULTI})

def predictor_konstan(laporan):      # 'laporan' tidak pernah dipakai
    return RECORD_TETAP

def f1m(p,g):
    P,G=set(p or []),set(g or [])
    if not P and not G: return 1.0
    if not P or not G: return 0.0
    return 2*len(P&G)/(len(P)+len(G))
def skor(predfn, teks_per_id):
    v=[]
    for i in ids:
        p=predfn(teks_per_id[i]); g=gold[i]
        d=[1.0 if (p.get(x) or '')==(g.get(x) or '') else 0.0 for x in SINGLE]
        d+=[f1m(p.get(x),g.get(x)) for x in MULTI]
        v.append(statistics.mean(d))
    return statistics.mean(v)

SK=["A1_seed42","A2_seed42","A3_seed42","A4_seed42","C1_headline_seed42",
    "C1_25pct_seed42","C1_50pct_seed42","C2_actor_seed42","C2_action_seed42","C2_asset_seed42"]
NAMA=["A1 informal","A2 code-switch","A3 noise","A4 translasi","C1a judul saja",
      "C1b potong 25%","C1c potong 50%","C2a buang actor","C2b buang action","C2c buang asset"]

base_teks={i:"teks asli" for i in ids}
b_konst=skor(predictor_konstan, base_teks)
b_fw=skor(lambda t: t, {i:clean[i] for i in ids})
print(f"{'skenario':18s} {'konstan':>9s} {'delta':>8s} | {'framework':>10s} {'delta':>8s}")
print(f"{'(teks asli)':18s} {b_konst:9.4f} {0.0:8.4f} | {b_fw:10.4f} {0.0:8.4f}")
print("-"*62)
for s,n in zip(SK,NAMA):
    pr=json.load(open(f"{B}/rq3/predictions/{s}.json"))
    k=skor(predictor_konstan,{i:f"teks {n}" for i in ids})
    f=skor(lambda t:t,{i:pr[i] for i in ids})
    print(f"{n:18s} {k:9.4f} {b_konst-k:8.4f} | {f:10.4f} {b_fw-f:+8.4f}")
