#!/usr/bin/env python3
"""RQ3 Scenario B — Class imbalance analysis.

Uses ONLY the baseline predictions (no new inference needed).
Computes:
  B1: per-class P/R/F1 + support for every VERIS enum value; macro vs micro F1 gap.
  B2: rare-class stress subset (minority sectors + low-frequency enum values).
  B3: government-sector dominance and its effect on macro-F1.

Output: rq3/rq3_scenarioB.json
"""
import json, sys
from collections import defaultdict, Counter
sys.path.insert(0, ".")

import numpy as np
import score_rq1 as sc
import rq3_lib as L
from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS

PREDS_FILE = "rq1/predictions_v3_fewshot_seed42.json"
OUT_FILE   = "rq3/rq3_scenarioB.json"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def per_class_metrics(f, preds, gold):
    """Return per-class {label: {tp,fp,fn,precision,recall,f1,support}} for field f."""
    res = sc.single_label_metrics(f, preds, gold)
    return res["per_class"], res["macro_f1_incl_unknown"], res["macro_f1_excl_unknown"], \
           res["correct"], res["n"]

def multi_class_stats(f, preds, gold):
    """Multi-label: per-value TP/FP/FN across all records."""
    from veris_fields import allowed_values
    labels = list(allowed_values(f))
    tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
    for rid, g_ann in gold.items():
        g_set = set(g_ann.get(f, []) or [])
        p_set = set((preds.get(rid) or {}).get(f, []) or [])
        for v in g_set & p_set:  tp[v] += 1
        for v in p_set - g_set:  fp[v] += 1
        for v in g_set - p_set:  fn[v] += 1
    out = {}
    for v in labels:
        t, p, n = tp[v], fp[v], fn[v]
        prec = t/(t+p) if t+p else 0.0
        rec  = t/(t+n) if t+n else 0.0
        f1   = 2*prec*rec/(prec+rec) if prec+rec else 0.0
        sup  = t + n
        out[v] = {"tp":t,"fp":p,"fn":n,"precision":round(prec,4),
                  "recall":round(rec,4),"f1":round(f1,4),"support":sup}
    return out


def macro_micro_f1_gap(per_class_dict):
    """Compute macro-F1 (mean over classes with support>0) and micro-F1."""
    classes_with_support = {k:v for k,v in per_class_dict.items() if v["support"]>0}
    if not classes_with_support:
        return 0.0, 0.0, 0.0
    macro = np.mean([v["f1"] for v in classes_with_support.values()])
    tp = sum(v["tp"] for v in classes_with_support.values())
    fp = sum(v["fp"] for v in classes_with_support.values())
    fn = sum(v["fn"] for v in classes_with_support.values())
    micro_p = tp/(tp+fp) if tp+fp else 0.0
    micro_r = tp/(tp+fn) if tp+fn else 0.0
    micro   = 2*micro_p*micro_r/(micro_p+micro_r) if micro_p+micro_r else 0.0
    return float(macro), float(micro), float(macro - micro)


# --------------------------------------------------------------------------- #
def main():
    preds_all = json.load(open(PREDS_FILE))
    preds = {k:v for k,v in preds_all.items() if not k.startswith("_")}
    gold  = L.load_gold()
    eval72 = L.load_72_records()
    baseline = L.load_baseline()
    per_rec_f1 = baseline["per_record_f1"]
    rids = list(gold.keys())

    # ------------------------------------------------------------------ #
    # B1 — Per-class P/R/F1 + support + macro vs micro gap
    # ------------------------------------------------------------------ #
    print("[B1] Computing per-class metrics ...")
    b1_single = {}
    for f in SINGLE_FIELDS:
        pc, macro_incl, macro_excl, correct, n = per_class_metrics(f, preds, gold)
        b1_single[f] = {
            "per_class": {k: {kk:vv for kk,vv in v.items()} for k,v in pc.items()},
            "macro_f1_incl_unknown": round(macro_incl, 4),
            "macro_f1_excl_unknown": round(macro_excl, 4),
            "accuracy": round(correct/n, 4) if n else 0,
            "n": n,
        }
        # Macro vs micro (treating Unknown as a class)
        # per_class from score_rq1 has {p, r, f1, support} (no tp/fp/fn)
        pc_stats = {k: {"tp": int(v["support"]*v["r"]),
                        "fp": max(0, int(v["support"]/max(v["r"],1e-9)*v["p"]) - int(v["support"]*v["r"])) if v["p"] else 0,
                        "fn": int(v["support"]*(1-v["r"])),
                        "f1": v["f1"], "support": v["support"]}
                    for k, v in pc.items()}
        mac, mic, gap = macro_micro_f1_gap(pc_stats)
        b1_single[f]["macro_f1_unweighted"] = round(mac, 4)
        b1_single[f]["micro_f1"]            = round(mic, 4)
        b1_single[f]["macro_micro_gap"]      = round(gap, 4)

    b1_multi = {}
    for f in MULTI_FIELDS:
        pc = multi_class_stats(f, preds, gold)
        mac, mic, gap = macro_micro_f1_gap(pc)
        res = sc.multi_label_metrics(f, preds, gold)
        b1_multi[f] = {
            "per_value": pc,
            "macro_f1_by_record": round(res["macro_f1"], 4),
            "micro_f1": round(res["micro_f1"], 4),
            "macro_micro_gap": round(mac - mic, 4),
            "macro_f1_by_value": round(mac, 4),
        }

    # Summary: rank dims by macro-micro gap (highest gap = most imbalance impact)
    gap_summary = {}
    for f, d in b1_single.items():
        gap_summary[f] = d["macro_micro_gap"]
    for f, d in b1_multi.items():
        gap_summary[f] = d["macro_micro_gap"]
    top_gaps = sorted(gap_summary.items(), key=lambda x: -abs(x[1]))

    print(f"  Top macro-micro gaps: {top_gaps[:5]}")

    # ------------------------------------------------------------------ #
    # B2 — Rare-class stress subset
    # ------------------------------------------------------------------ #
    print("[B2] Building rare-class stress subset ...")
    # Identify minority sector records (telco, education_healthcare; n<5 in gold)
    sector_groups = defaultdict(list)
    for rid, ann in gold.items():
        sec = ann.get("_meta", {}).get("sector", "unknown")
        sector_groups[sec].append(rid)
    minority_sectors = {s for s, ids in sector_groups.items() if len(ids) < 5}
    minority_sector_ids = {rid for s, ids in sector_groups.items()
                           if s in minority_sectors for rid in ids}

    # Identify records where gold has at least one low-frequency action_variety value
    # (frequency < 3 in the 72-record gold)
    av_counts = Counter()
    for ann in gold.values():
        for v in ann.get("action_variety", []) or []:
            av_counts[v] += 1
    rare_av_values = {v for v, c in av_counts.items() if c < 3}
    rare_av_ids = {rid for rid, ann in gold.items()
                   if any(v in rare_av_values for v in (ann.get("action_variety") or []))}

    # Union of minority-sector and rare-action_variety records
    stress_ids = minority_sector_ids | rare_av_ids
    if len(stress_ids) < 5:
        # expand: add financial sector and unknown sector
        for s in ["financial", "unknown"]:
            stress_ids |= set(sector_groups.get(s, []))

    stress_f1 = {rid: per_rec_f1[rid] for rid in stress_ids if rid in per_rec_f1}
    majority_ids = set(rids) - stress_ids
    majority_f1  = {rid: per_rec_f1[rid] for rid in majority_ids if rid in per_rec_f1}

    stress_mean   = float(np.mean(list(stress_f1.values()))) if stress_f1 else 0
    majority_mean = float(np.mean(list(majority_f1.values()))) if majority_f1 else 0
    delta_stress  = majority_mean - stress_mean  # positive = majority outperforms

    print(f"  stress subset: n={len(stress_ids)} mean F1={stress_mean:.4f}")
    print(f"  majority: n={len(majority_ids)} mean F1={majority_mean:.4f}")
    print(f"  delta (majority-stress): {delta_stress:.4f}")

    b2 = {
        "minority_sectors": sorted(minority_sectors),
        "minority_sector_ids": sorted(minority_sector_ids),
        "rare_action_variety_values": sorted(rare_av_values),
        "rare_av_ids": sorted(rare_av_ids),
        "stress_subset_ids": sorted(stress_ids),
        "n_stress": len(stress_ids),
        "n_majority": len(majority_ids),
        "stress_mean_f1": round(stress_mean, 4),
        "majority_mean_f1": round(majority_mean, 4),
        "delta_majority_minus_stress": round(delta_stress, 4),
        "h3_note": ("B2 does not directly test H3 degradation as it compares "
                    "subgroups within baseline, not baseline vs perturbed scenario."),
    }

    # ------------------------------------------------------------------ #
    # B3 — Government sector dominance
    # ------------------------------------------------------------------ #
    print("[B3] Sector breakdown ...")
    sector_f1 = defaultdict(list)
    for rid in rids:
        sec = gold[rid].get("_meta", {}).get("sector", "unknown")
        sector_f1[sec].append(per_rec_f1.get(rid, 0))
    b3 = {
        sec: {"n": len(v), "mean_f1": round(float(np.mean(v)), 4) if v else 0}
        for sec, v in sector_f1.items()
    }
    gov_n  = b3.get("government", {}).get("n", 0)
    all_n  = len(rids)
    b3["_gov_dominance_note"] = (
        f"government sector = {gov_n}/{all_n} records "
        f"({100*gov_n/all_n:.1f}%); macro-F1 is heavily weighted toward government "
        f"incidents (KPU, PDNS, BSSN, PDN). Other sectors are too small for "
        f"reliable per-sector inference (n<8)."
    )

    # ------------------------------------------------------------------ #
    # Overall summary — support table (B1 key insight)
    # ------------------------------------------------------------------ #
    support_table = {}
    for f in SINGLE_FIELDS:
        for cls, d in b1_single[f]["per_class"].items():
            support_table[f"{f}::{cls}"] = {
                "support": d.get("support",0),
                "f1": d.get("f1",0),
            }

    # ------------------------------------------------------------------ #
    out = {
        "scenario": "B",
        "n_records": len(rids),
        "b1_single_label": b1_single,
        "b1_multi_label": b1_multi,
        "b1_macro_micro_gap_ranking": [
            {"dim": d, "gap": round(g, 4)} for d, g in top_gaps
        ],
        "b2_rare_class_subset": b2,
        "b3_sector_breakdown": b3,
    }
    json.dump(out, open(OUT_FILE, "w"), indent=2, ensure_ascii=False)
    print(f"\n[B] -> {OUT_FILE}")


if __name__ == "__main__":
    main()
