import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json,statistics,random
from collections import Counter
BASE=ROOT
gold=json.load(open(f"{BASE}/data/gold_standard.json"))
pred=json.load(open(f"{BASE}/rq1/predictions_v3_fewshot_seed42.json"))
ids=sorted(k for k in pred if not k.startswith("_"))
SINGLE=["actor_category","action_category","asset_category","attr_conf_present","attr_integrity_present","attr_avail_present","attr_conf_disclosure"]
MULTI=["actor_variety","actor_motive","action_variety","action_vector","asset_variety","attr_conf_data_variety","attr_integrity_variety","attr_avail_variety"]
# entropy of gold label distribution per dimension
import math
print(f"{'dimension':28s} {'H(gold)':>8s} {'top%':>6s} {'fw-maj':>8s}")
maj={}
for d in SINGLE: maj[d]=Counter(gold[i].get(d) or '' for i in ids).most_common(1)[0][0]
for d in MULTI: maj[d]=list(Counter(tuple(sorted(gold[i].get(d) or [])) for i in ids).most_common(1)[0][0])
def f1m(p,g):
    P,G=set(p or []),set(g or [])
    if not P and not G: return 1.0
    if not P or not G: return 0.0
    return 2*len(P&G)/(len(P)+len(G))
rows=[]
for d in SINGLE+MULTI:
    if d in SINGLE:
        c=Counter(gold[i].get(d) or '' for i in ids)
        fv=statistics.mean(1.0 if (pred[i].get(d) or '')==(gold[i].get(d) or '') else 0.0 for i in ids)
        mv=statistics.mean(1.0 if maj[d]==(gold[i].get(d) or '') else 0.0 for i in ids)
    else:
        c=Counter(tuple(sorted(gold[i].get(d) or [])) for i in ids)
        fv=statistics.mean(f1m(pred[i].get(d),gold[i].get(d)) for i in ids)
        mv=statistics.mean(f1m(maj[d],gold[i].get(d)) for i in ids)
    n=sum(c.values()); H=-sum((v/n)*math.log2(v/n) for v in c.values())
    top=c.most_common(1)[0][1]/n
    rows.append((d,H,top,fv,mv))
    print(f"{d:28s} {H:8.3f} {top:6.1%} {fv-mv:+8.4f}")
# correlation between entropy and framework advantage
xs=[r[1] for r in rows]; ys=[r[3]-r[4] for r in rows]
mx,my=statistics.mean(xs),statistics.mean(ys)
num=sum((a-mx)*(b-my) for a,b in zip(xs,ys)); den=(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**.5
print(f"\nPearson r (gold entropy vs framework advantage over majority) = {num/den:.3f}")
json.dump([{"dim":r[0],"entropy":round(r[1],4),"top_share":round(r[2],4),"framework":round(r[3],4),"majority":round(r[4],4)} for r in rows], open("perdim.json","w"), indent=1)
