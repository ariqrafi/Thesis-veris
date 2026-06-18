#!/usr/bin/env python3
"""RQ3 shared utilities: data loading, scoring, statistics."""
import json, math, itertools
from collections import defaultdict

import numpy as np
from scipy import stats as sp_stats
from statsmodels.stats.proportion import proportion_confint

import score_rq1 as sc
from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS

GOLD_FILE  = "data/gold_standard.json"
EVAL_FILE  = "data/eval_set_100.jsonl"
EXEMPLAR_FILE = "data/fewshot_exemplars.json"
BASELINE_FILE = "rq3/rq3_baseline.json"

CORE_DIMS = [
    "actor_category", "action_category", "asset_category",
    "attr_conf_present", "attr_integrity_present", "attr_avail_present",
]

# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_gold():
    return sc.load_gold()

def load_eval_records():
    recs = {}
    with open(EVAL_FILE) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                r = json.loads(ln)
                recs[r["record_id"]] = r
    return recs

def load_72_records():
    """Return dict {record_id: record} for the 72 in-scope records."""
    gold = load_gold()
    all_recs = load_eval_records()
    return {rid: all_recs[rid] for rid in gold if rid in all_recs}

def exemplar_hashes():
    doc = json.load(open(EXEMPLAR_FILE))
    return {e.get("content_hash") for e in doc["exemplars"] if e.get("use")}

def load_baseline():
    return json.load(open(BASELINE_FILE))

# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def score_predictions(preds_all):
    """Score predictions against 72-record gold.

    Returns dict with:
      overall_macro_f1, core_a4_f1_excl_unknown, svr,
      per_record_f1 {rid: float},
      per_dim_correct {dim: {rid: float}},  # 0/1 single-label, set-F1 multi-label
      dim_headline_f1 {dim: float},
      schema {full schema compliance dict}
    """
    gold = load_gold()
    preds = {k: v for k, v in preds_all.items() if not k.startswith("_")}
    rids  = list(gold.keys())

    schema    = sc.schema_compliance(preds, gold)
    single_res = {f: sc.single_label_metrics(f, preds, gold) for f in SINGLE_FIELDS}
    multi_res  = {f: sc.multi_label_metrics(f, preds, gold)  for f in MULTI_FIELDS}

    per_dim_correct = {}
    for f in SINGLE_FIELDS:
        per_dim_correct[f] = {}
        for i, rid in enumerate(rids):
            g, p, _ = single_res[f]["pairs"][i]
            per_dim_correct[f][rid] = 1.0 if g == p else 0.0

    for f in MULTI_FIELDS:
        per_dim_correct[f] = {rid: multi_res[f]["per_record"][rid] for rid in rids}

    per_record_f1 = {}
    for rid in rids:
        dims  = [per_dim_correct[f][rid] for f in SINGLE_FIELDS]
        dims += [per_dim_correct[f][rid] for f in MULTI_FIELDS]
        per_record_f1[rid] = float(np.mean(dims))

    dim_headline = {}
    for f in SINGLE_FIELDS:
        dim_headline[f] = single_res[f]["macro_f1_incl_unknown"]
    for f in MULTI_FIELDS:
        dim_headline[f] = multi_res[f]["macro_f1"]

    # Core-A4 excl Unknown
    core_f1s_excl = [single_res[f]["macro_f1_excl_unknown"] for f in CORE_DIMS]
    core_a4_excl  = float(np.mean(core_f1s_excl))

    svr = schema.get("svr", schema.get("violation_rate", 0.0))
    return {
        "overall_macro_f1":        float(np.mean([per_record_f1[r] for r in rids])),
        "core_a4_f1_excl_unknown": core_a4_excl,
        "svr":                     svr,
        "per_record_f1":           per_record_f1,
        "per_dim_correct":         per_dim_correct,
        "dim_headline_f1":         dim_headline,
        "schema":                  schema,
        "n_records":               len(rids),
    }

# --------------------------------------------------------------------------- #
# Paired bootstrap ΔF1
# --------------------------------------------------------------------------- #
def paired_bootstrap_delta(base_vec, scen_vec, n_boot=1000, seed=42):
    """
    base_vec, scen_vec: aligned np.array of per-record F1 values.
    Returns (delta_mean, ci_lo, ci_hi)  where delta = baseline - scenario.
    """
    delta_obs = base_vec - scen_vec
    delta_mean = float(delta_obs.mean())
    rng = np.random.default_rng(seed)
    n   = len(delta_obs)
    boots = np.array([
        delta_obs[rng.integers(0, n, n)].mean() for _ in range(n_boot)
    ])
    ci_lo = float(np.percentile(boots, 2.5))
    ci_hi = float(np.percentile(boots, 97.5))
    return delta_mean, ci_lo, ci_hi

def delta_stats(base_result, scen_result, n_boot=1000, seed=42):
    """Compute paired ΔF1 stats for overall and Core-A4."""
    gold = load_gold()
    rids = list(gold.keys())
    bv = np.array([base_result["per_record_f1"][r] for r in rids])
    sv = np.array([scen_result["per_record_f1"][r] for r in rids])
    overall_d, overall_lo, overall_hi = paired_bootstrap_delta(bv, sv, n_boot, seed)
    h3_supported_overall = overall_hi < 0.15

    # Core-A4 per-record delta
    bc = np.array([
        np.mean([base_result["per_dim_correct"][f][r] for f in CORE_DIMS]) for r in rids
    ])
    sc2 = np.array([
        np.mean([scen_result["per_dim_correct"][f][r] for f in CORE_DIMS]) for r in rids
    ])
    core_d, core_lo, core_hi = paired_bootstrap_delta(bc, sc2, n_boot, seed)
    h3_supported_core = core_hi < 0.15

    return {
        "overall": {
            "delta_mean": overall_d,
            "ci95_lo": overall_lo, "ci95_hi": overall_hi,
            "h3_supported": h3_supported_overall,
        },
        "core_a4_excl_unknown": {
            "delta_mean": core_d,
            "ci95_lo": core_lo, "ci95_hi": core_hi,
            "h3_supported": h3_supported_core,
        },
    }

# --------------------------------------------------------------------------- #
# McNemar test (per-dimension, single-label only; binarise multi-label at 0.5)
# --------------------------------------------------------------------------- #
def mcnemar_per_dim(base_result, scen_result):
    """Return {dim: {b, c, chi2, p_value}} for each dimension."""
    gold = load_gold()
    rids = list(gold.keys())
    results = {}
    for f in ALL_FIELDS:
        b_correct = np.array([base_result["per_dim_correct"][f][r] for r in rids])
        s_correct = np.array([scen_result["per_dim_correct"][f][r] for r in rids])
        # binarise for multi-label
        b_bin = (b_correct >= 0.5).astype(int)
        s_bin = (s_correct >= 0.5).astype(int)
        # McNemar counts
        b_cnt = int(((b_bin == 1) & (s_bin == 0)).sum())  # correct base, wrong scen
        c_cnt = int(((b_bin == 0) & (s_bin == 1)).sum())  # wrong base, correct scen
        n_disc = b_cnt + c_cnt
        if n_disc == 0:
            chi2, p = 0.0, 1.0
        else:
            # Edwards correction
            chi2 = float(max(abs(b_cnt - c_cnt) - 1, 0)**2 / n_disc)
            p    = float(sp_stats.chi2.sf(chi2, 1))
        results[f] = {"b": b_cnt, "c": c_cnt, "chi2": chi2, "p_value": p}
    return results

# --------------------------------------------------------------------------- #
# Bonferroni
# --------------------------------------------------------------------------- #
def bonferroni(p_values_dict, alpha=0.05):
    """p_values_dict: {label: p}. Returns {label: {p, reject_bonferroni}}."""
    n = len(p_values_dict)
    threshold = alpha / n if n else alpha
    out = {}
    for k, p in p_values_dict.items():
        out[k] = {"p": p, "bonferroni_threshold": threshold, "reject": p < threshold}
    return out

# --------------------------------------------------------------------------- #
# Wilson CI for SVR
# --------------------------------------------------------------------------- #
def wilson_svr(n_violations, n_total):
    if n_total == 0:
        return 0.0, (0.0, 0.0)
    svr = n_violations / n_total
    lo, hi = proportion_confint(n_violations, n_total, method="wilson")
    return svr, (float(lo), float(hi))
