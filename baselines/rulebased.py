# -*- coding: utf-8 -*-
"""B2: rule-based lexicon baseline (no LLM). Indonesian/English keyword matching
over full_content_clean, mapped onto the VERIS A4 controlled vocabulary.
Falls back to the training-set prior when no cue fires."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, re, statistics, random
from collections import Counter

BASE=ROOT
gold_all=json.load(open(f"{BASE}/data/gold_standard.json"))
pred=json.load(open(f"{BASE}/rq1/predictions_v3_fewshot_seed42.json"))
rows={r["record_id"]:r for r in
      (json.loads(l) for l in open(f"{BASE}/data/eval_set_100.jsonl",encoding="utf-8"))}
ids=sorted(k for k in pred if not k.startswith("_"))

SINGLE=["actor_category","action_category","asset_category","attr_conf_present",
        "attr_integrity_present","attr_avail_present","attr_conf_disclosure"]
MULTI=["actor_variety","actor_motive","action_variety","action_vector","asset_variety",
       "attr_conf_data_variety","attr_integrity_variety","attr_avail_variety"]

def txt(i):
    r=rows[i]; return ((r.get("title") or "")+" "+(r.get("full_content_clean") or r.get("full_content") or "")).lower()

def has(t,*kw): return any(k in t for k in kw)

# ---- cue lexicons (Indonesian + English) -------------------------------
def rule_predict(t, prior):
    o=dict(prior)  # start from training prior, override where a cue fires

    # actor
    if has(t,"orang dalam","oknum pegawai","karyawan","pegawai internal","insider","mantan karyawan"):
        o["actor_category"]="Internal"; o["actor_variety"]=["Other"]
    elif has(t,"vendor","pihak ketiga","mitra","supplier","third party","rekanan"):
        o["actor_category"]="Partner"; o["actor_variety"]=["Other"]
    elif has(t,"peretas","hacker","kelompok ransomware","penyerang","attacker","geng siber",
             "threat actor","lockbit","bjorka","brain cipher"):
        o["actor_category"]="External"; o["actor_variety"]=["Organized crime"]

    # motive
    if has(t,"tebusan","ransom","dijual","diperjualbelikan","uang","bitcoin","jual data","monetisasi"):
        o["actor_motive"]=["Financial"]
    elif has(t,"ideologi","protes","hacktivis","hacktivist","politik"):
        o["actor_motive"]=["Ideology"]

    # action
    if has(t,"ransomware","terenkripsi","dienkripsi","encrypt","malware","trojan","virus","brain cipher","lockbit"):
        o["action_category"]="Malware"; o["action_variety"]=["Ransomware"]; o["action_vector"]=["Unknown"]
    elif has(t,"phishing","rekayasa sosial","social engineering","email palsu","situs palsu"):
        o["action_category"]="Social"; o["action_variety"]=["Phishing"]; o["action_vector"]=["Email"]
    elif has(t,"sql injection","sqli","injeksi sql"):
        o["action_category"]="Hacking"; o["action_variety"]=["SQLi"]; o["action_vector"]=["Web application"]
    elif has(t,"deface","defacement","diretas tampilan","ubah tampilan"):
        o["action_category"]="Hacking"; o["action_variety"]=["Other"]; o["action_vector"]=["Web application"]
    elif has(t,"kredensial","password bocor","kata sandi","stolen credential","akun dicuri","login"):
        o["action_category"]="Hacking"; o["action_variety"]=["Use of stolen creds"]; o["action_vector"]=["Web application"]
    elif has(t,"diretas","peretasan","dibobol","hack","breach","serangan siber","cyberattack","dijebol"):
        o["action_category"]="Hacking"; o["action_variety"]=["Exploit vuln"]; o["action_vector"]=["Web application"]
    elif has(t,"salah konfigurasi","misconfig","tidak sengaja","kelalaian","human error","salah kirim"):
        o["action_category"]="Error"; o["action_variety"]=["Misconfiguration"]; o["action_vector"]=["Unknown"]
    elif has(t,"penyalahgunaan","disalahgunakan","misuse","wewenang"):
        o["action_category"]="Misuse"; o["action_variety"]=["Privilege abuse"]; o["action_vector"]=["Unknown"]

    # asset
    if has(t,"basis data","database","server","pusat data","data center","sistem","situs","website","aplikasi"):
        o["asset_category"]="Server"
        v=[]
        if has(t,"basis data","database"): v.append("Database")
        if has(t,"situs","website","web","aplikasi web"): v.append("Web application")
        o["asset_variety"]=v or ["Database"]
    elif has(t,"laptop","ponsel","handphone","komputer pegawai","user device"):
        o["asset_category"]="User Device"; o["asset_variety"]=["Desktop or laptop"]

    # attributes
    if has(t,"data bocor","kebocoran data","dibocorkan","terekspos","leaked","dijual","data breach","bocor"):
        o["attr_conf_present"]="Yes"; o["attr_conf_disclosure"]="Yes"
    if has(t,"nik","ktp","nama lengkap","alamat","nomor telepon","data pribadi","personal data","email"):
        o["attr_conf_data_variety"]=["Personal"]
    if has(t,"diubah","dimodifikasi","dienkripsi","terenkripsi","deface","modified","tampered"):
        o["attr_integrity_present"]="Yes"; o["attr_integrity_variety"]=["Software installation"]
    if has(t,"lumpuh","down","tidak dapat diakses","gangguan","mati","terganggu","outage","layanan terhenti"):
        o["attr_avail_present"]="Yes"; o["attr_avail_variety"]=["Interruption"]
    return o

# ---- scoring (identical to the validated scorer) -----------------------
def f1_multi(p,g,e1=True):
    P,G=set(p or []),set(g or [])
    if not P and not G: return 1.0 if e1 else None
    if not P or not G: return 0.0
    return 2*len(P&G)/(len(P)+len(G))

def rec_f1(p,g,e1=True):
    v=[1.0 if (p.get(d) or "")==(g.get(d) or "") else 0.0 for d in SINGLE]
    for d in MULTI:
        x=f1_multi(p.get(d),g.get(d),e1)
        if x is not None: v.append(x)
    return statistics.mean(v)

def prior_of(train):
    pr={}
    for d in SINGLE:
        pr[d]=Counter(gold_all[i].get(d) or "" for i in train).most_common(1)[0][0]
    for d in MULTI:
        pr[d]=list(Counter(tuple(sorted(gold_all[i].get(d) or [])) for i in train).most_common(1)[0][0])
    return pr

def boot(vals,n=10000,seed=42):
    rnd=random.Random(seed); N=len(vals)
    ms=sorted(statistics.mean(rnd.choices(vals,k=N)) for _ in range(n))
    return ms[int(.025*n)], ms[int(.975*n)]

# leave-one-out so the prior fallback never sees the test record
vals=[rec_f1(rule_predict(txt(i), prior_of([j for j in ids if j!=i])), gold_all[i]) for i in ids]
m=statistics.mean(vals); lo,hi=boot(vals)
print(f"B2 rule-based lexicon (LOO)    : {m:.4f}  95% CI [{lo:.4f}, {hi:.4f}]")

print(f"\n{'dimension':28s} {'rule':>8s} {'framework':>10s} {'majority':>9s}")
prior_all=prior_of(ids)
for d in SINGLE+MULTI:
    rv,fv,mv=[],[],[]
    for i in ids:
        rp=rule_predict(txt(i), prior_of([j for j in ids if j!=i])); g=gold_all[i]
        if d in SINGLE:
            rv.append(1.0 if (rp.get(d) or "")==(g.get(d) or "") else 0.0)
            fv.append(1.0 if (pred[i].get(d) or "")==(g.get(d) or "") else 0.0)
            mv.append(1.0 if prior_all[d]==(g.get(d) or "") else 0.0)
        else:
            rv.append(f1_multi(rp.get(d),g.get(d))); fv.append(f1_multi(pred[i].get(d),g.get(d)))
            mv.append(f1_multi(prior_all[d],g.get(d)))
    print(f"{d:28s} {statistics.mean(rv):8.4f} {statistics.mean(fv):10.4f} {statistics.mean(mv):9.4f}")
