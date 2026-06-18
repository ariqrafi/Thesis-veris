#!/usr/bin/env python3
"""RQ3 Task STAT — Full statistical analysis across all scenarios.

Consumes:
  rq3/rq3_baseline.json
  rq3/scenario_scores.json   (built by rq3_score_scenario.py --all)
  rq1/predictions_v3_fewshot_seed42.json
  rq3/predictions/<scenario>_seed42.json  (for per-record per-dim McNemar)

Produces:
  rq3/rq3_stats.json   (all tests, Bonferroni, verdicts)
  rq3/rq3_scenarioA.json
  rq3/rq3_scenarioC.json
"""
import json, sys
from pathlib import Path
sys.path.insert(0, ".")

import numpy as np
import rq3_lib as L

PREDS_DIR   = Path("rq3/predictions")
SCORES_FILE = Path("rq3/scenario_scores.json")
OUT_STATS   = Path("rq3/rq3_stats.json")
OUT_A       = Path("rq3/rq3_scenarioA.json")
OUT_C       = Path("rq3/rq3_scenarioC.json")

SCENARIO_GROUPS = {
    "A": ["A1","A2","A3","A4"],
    "C": ["C1_headline","C1_25pct","C1_50pct","C2_actor","C2_action","C2_asset"],
}


def load_scenario_result(scenario):
    """Return (scored_result, preds_all) for a scenario if predictions exist."""
    path = PREDS_DIR / f"{scenario}_seed42.json"
    if not path.exists():
        return None, None
    preds_all = json.load(open(path))
    res = L.score_predictions(preds_all)
    return res, preds_all


def main():
    baseline = L.load_baseline()
    scores   = json.load(open(SCORES_FILE)) if SCORES_FILE.exists() else {}
    gold     = L.load_gold()
    rids     = list(gold.keys())

    # Load baseline predictions for McNemar
    base_preds_all = json.load(open("rq1/predictions_v3_fewshot_seed42.json"))
    base_result    = L.score_predictions(base_preds_all)

    all_scenarios = [s for group in SCENARIO_GROUPS.values() for s in group]
    available     = [s for s in all_scenarios if s in scores]
    print(f"Scoring {len(available)}/{len(all_scenarios)} scenarios available: {available}")

    # ------------------------------------------------------------------ #
    # Per-scenario: ΔF1 + McNemar + SVR Wilson
    # ------------------------------------------------------------------ #
    scenario_stats = {}
    all_pvals = {}  # for Bonferroni: keyed by "<scenario>_overall", "<scenario>_<dim>"

    for sc in available:
        scen_result, preds_all = load_scenario_result(sc)
        if scen_result is None:
            continue
        entry = scores[sc]

        # Paired bootstrap ΔF1 (already in scores but recompute for consistency)
        bv = np.array([base_result["per_record_f1"][r]  for r in rids])
        sv = np.array([scen_result["per_record_f1"][r]  for r in rids])
        delta_mean, ci_lo, ci_hi = L.paired_bootstrap_delta(bv, sv)
        h3_overall = ci_hi < 0.15

        # McNemar per dimension
        mcnemar_res = L.mcnemar_per_dim(base_result, scen_result)
        for dim, d in mcnemar_res.items():
            all_pvals[f"{sc}__{dim}"] = d["p_value"]
        all_pvals[f"{sc}__OVERALL"] = None  # placeholder; bootstrap CI not a p-value

        scenario_stats[sc] = {
            "overall_delta": {
                "delta_mean": round(delta_mean, 4),
                "ci95_lo": round(ci_lo, 4),
                "ci95_hi": round(ci_hi, 4),
                "h3_supported": h3_overall,
                "h3_note": "SUPPORTED iff CI upper < 0.15",
            },
            "core_a4_delta": entry.get("delta_core_a4", {}),
            "svr": entry.get("svr"),
            "svr_wilson_ci95": entry.get("svr_wilson_ci95"),
            "mcnemar_per_dim": mcnemar_res,
        }
        print(f"  [{sc}] ΔF1={delta_mean:.4f} CI=[{ci_lo:.4f},{ci_hi:.4f}] H3={h3_overall}")

    # ------------------------------------------------------------------ #
    # Bonferroni correction across all McNemar p-values
    # ------------------------------------------------------------------ #
    mc_pvals = {k: v for k, v in all_pvals.items() if v is not None}
    bonferroni_res = L.bonferroni(mc_pvals, alpha=0.05)
    n_comparisons  = len(mc_pvals)
    threshold_adj  = 0.05 / n_comparisons if n_comparisons else 0.05
    n_reject_raw   = sum(1 for v in mc_pvals.values() if v < 0.05)
    n_reject_bonf  = sum(1 for d in bonferroni_res.values() if d["reject"])
    print(f"\nBonferroni: {n_comparisons} comparisons, α_adj={threshold_adj:.5f}, "
          f"reject_raw={n_reject_raw}, reject_bonferroni={n_reject_bonf}")

    # ------------------------------------------------------------------ #
    # C3 — Short-report subset analysis (no new inference, from baseline)
    # ------------------------------------------------------------------ #
    short_ids = set(baseline.get("c3_short_record_ids", []))
    long_ids  = set(rids) - short_ids
    c3_short_f1 = {r: base_result["per_record_f1"][r] for r in short_ids if r in base_result["per_record_f1"]}
    c3_long_f1  = {r: base_result["per_record_f1"][r] for r in long_ids  if r in base_result["per_record_f1"]}
    c3_short_mean = float(np.mean(list(c3_short_f1.values()))) if c3_short_f1 else 0.0
    c3_long_mean  = float(np.mean(list(c3_long_f1.values())))  if c3_long_f1  else 0.0
    c3_delta      = c3_long_mean - c3_short_mean  # positive = long docs score higher

    # Paired bootstrap for C3 (NOT paired by document, just group comparison)
    sv_arr = np.array(list(c3_short_f1.values()))
    lv_arr = np.array(list(c3_long_f1.values()))
    rng = np.random.default_rng(42)
    c3_boot_deltas = [
        rng.choice(lv_arr, len(lv_arr)).mean() - rng.choice(sv_arr, len(sv_arr)).mean()
        for _ in range(1000)
    ]
    c3_ci_lo = float(np.percentile(c3_boot_deltas, 2.5))
    c3_ci_hi = float(np.percentile(c3_boot_deltas, 97.5))

    c3_natural = {
        "q25_length_threshold": baseline.get("q25_length_threshold"),
        "n_short": len(short_ids),
        "n_long":  len(long_ids),
        "short_mean_f1": round(c3_short_mean, 4),
        "long_mean_f1":  round(c3_long_mean,  4),
        "delta_long_minus_short": round(c3_delta, 4),
        "bootstrap_ci95_delta": [round(c3_ci_lo, 4), round(c3_ci_hi, 4)],
        "note": ("C3 is a natural cross-check (not a perturbed scenario); "
                 "delta is long-doc F1 minus short-doc F1 (positive = long docs score better). "
                 "Not directly used for H3 verdict (no paired baseline-scenario comparison)."),
    }
    print(f"\nC3 short vs long: short={c3_short_mean:.4f} long={c3_long_mean:.4f} "
          f"delta={c3_delta:.4f} CI=[{c3_ci_lo:.4f},{c3_ci_hi:.4f}]")

    # ------------------------------------------------------------------ #
    # Aggregate H3 verdict
    # ------------------------------------------------------------------ #
    h3_per_scenario = {sc: stats["overall_delta"]["h3_supported"]
                       for sc, stats in scenario_stats.items()}
    n_supported = sum(1 for v in h3_per_scenario.values() if v)
    n_total_sc  = len(h3_per_scenario)
    h3_aggregate = (
        f"SUPPORTED ({n_supported}/{n_total_sc} scenarios: CI upper < 0.15)"
        if n_supported == n_total_sc and n_total_sc > 0
        else f"NOT SUPPORTED or PARTIAL ({n_supported}/{n_total_sc} scenarios supported)"
        if n_total_sc > 0 else "INSUFFICIENT DATA"
    )

    # ------------------------------------------------------------------ #
    # Assemble final stats output
    # ------------------------------------------------------------------ #
    stats_out = {
        "h3_hypothesis": "Degradation F1 <= 0.15 across all stress-test scenarios",
        "h3_rule": "SUPPORTED iff upper bound of 95% CI(ΔF1) < 0.15 for each scenario",
        "h3_per_scenario": h3_per_scenario,
        "h3_aggregate": h3_aggregate,
        "n_scenarios_evaluated": n_total_sc,
        "n_scenarios_h3_supported": n_supported,
        "bonferroni": {
            "n_mcnemar_comparisons": n_comparisons,
            "alpha_adjusted": round(threshold_adj, 6),
            "n_reject_raw_alpha05": n_reject_raw,
            "n_reject_bonferroni": n_reject_bonf,
            "per_comparison": bonferroni_res,
        },
        "c3_natural_short_report": c3_natural,
        "per_scenario": scenario_stats,
    }
    json.dump(stats_out, open(OUT_STATS, "w"), indent=2, ensure_ascii=False)
    print(f"\n-> {OUT_STATS}")
    print(f"H3 aggregate verdict: {h3_aggregate}")

    # ------------------------------------------------------------------ #
    # Scenario group JSONs
    # ------------------------------------------------------------------ #
    def build_group_json(group_name, group_scenarios):
        return {
            "scenario_group": group_name,
            "scenarios": {
                sc: {**scores.get(sc, {}), "stats": scenario_stats.get(sc, {})}
                for sc in group_scenarios if sc in scenario_stats
            },
            "c3_natural_short_report": c3_natural if group_name == "C" else None,
        }

    json.dump(build_group_json("A", SCENARIO_GROUPS["A"]),
              open(OUT_A, "w"), indent=2, ensure_ascii=False)
    json.dump(build_group_json("C", SCENARIO_GROUPS["C"]),
              open(OUT_C, "w"), indent=2, ensure_ascii=False)
    print(f"-> {OUT_A}, {OUT_C}")


if __name__ == "__main__":
    main()
