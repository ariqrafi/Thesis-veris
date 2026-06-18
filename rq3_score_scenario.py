#!/usr/bin/env python3
"""RQ3 — Score a single scenario's predictions and compute ΔF1 vs baseline.

Usage:
  python3 rq3_score_scenario.py --scenario A3
  python3 rq3_score_scenario.py --scenario C1_25pct
  python3 rq3_score_scenario.py --all          # score all available predictions

Outputs (appended to rq3/scenario_scores.json — one entry per scenario).
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, ".")

import numpy as np
import rq3_lib as L

PREDS_DIR    = Path("rq3/predictions")
SCORES_FILE  = Path("rq3/scenario_scores.json")
BASE_PREDS   = "rq1/predictions_v3_fewshot_seed42.json"

ALL_SCENARIOS = [
    "A1","A2","A3","A4",
    "C1_headline","C1_25pct","C1_50pct",
    "C2_actor","C2_action","C2_asset",
]


def score_one(scenario):
    preds_path = PREDS_DIR / f"{scenario}_seed42.json"
    if not preds_path.exists():
        print(f"[{scenario}] predictions not found: {preds_path} — skip")
        return None

    preds_all = json.load(open(preds_path))
    run_meta  = preds_all.get("_run_meta", {})
    print(f"[{scenario}] scoring {len([k for k in preds_all if not k.startswith('_')])} records ...")

    import json as _json
    base_preds_all = _json.load(open(BASE_PREDS))
    base_result    = L.score_predictions(base_preds_all)
    res            = L.score_predictions(preds_all)
    baseline       = L.load_baseline()
    deltas         = L.delta_stats(base_result, res, n_boot=1000, seed=42)

    # SVR Wilson CI
    schema  = res["schema"]
    n_vio   = schema.get("n_violation_records", schema.get("off_vocab", 0))
    n_total = res["n_records"]
    svr, svr_ci = L.wilson_svr(n_vio, n_total)

    entry = {
        "scenario":               scenario,
        "run_meta":               run_meta,
        "n_records":              res["n_records"],
        "overall_macro_f1":       round(res["overall_macro_f1"], 4),
        "core_a4_f1_excl_unknown":round(res["core_a4_f1_excl_unknown"], 4),
        "svr":                    round(svr, 4),
        "svr_wilson_ci95":        [round(svr_ci[0], 4), round(svr_ci[1], 4)],
        "baseline_overall_f1":    round(baseline["overall_macro_f1"], 4),
        "baseline_core_a4_f1":    round(baseline["core_a4_f1_excl_unknown"], 4),
        "delta_overall":          deltas["overall"],
        "delta_core_a4":          deltas["core_a4_excl_unknown"],
        "dim_headline_f1":        {k: round(v, 4) for k,v in res["dim_headline_f1"].items()},
        "per_record_f1":          {k: round(v, 4) for k,v in res["per_record_f1"].items()},
    }

    print(f"  F1={res['overall_macro_f1']:.4f}  "
          f"ΔF1={deltas['overall']['delta_mean']:.4f}  "
          f"CI=[{deltas['overall']['ci95_lo']:.4f},{deltas['overall']['ci95_hi']:.4f}]  "
          f"H3={deltas['overall']['h3_supported']}")
    return entry


def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--scenario", choices=ALL_SCENARIOS)
    grp.add_argument("--all", action="store_true")
    args = ap.parse_args()

    scenarios = ALL_SCENARIOS if args.all else [args.scenario]

    # Load existing scores
    scores = {}
    if SCORES_FILE.exists():
        scores = json.load(open(SCORES_FILE))

    for sc in scenarios:
        entry = score_one(sc)
        if entry:
            scores[sc] = entry

    json.dump(scores, open(SCORES_FILE, "w"), indent=2, ensure_ascii=False)
    print(f"\n-> {SCORES_FILE} ({len(scores)} scenarios)")


if __name__ == "__main__":
    main()
