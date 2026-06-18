#!/usr/bin/env python3
"""RQ3 Task Final — Generate rq3/rq3_summary.md.

Consumes rq3_baseline.json, scenario_scores.json, rq3_stats.json, rq3_scenarioB.json.
Produces rq3/rq3_summary.md.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
import rq3_lib as L
from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS

OUT_MD = Path("rq3/rq3_summary.md")

SCENARIO_LABELS = {
    "A1": "A1 — Informal register (LLM)",
    "A2": "A2 — Code-switching (LLM)",
    "A3": "A3 — Noise injection (rule-based, 7%)",
    "A4": "A4 — Cross-lingual translation (LLM)",
    "C1_headline": "C1a — Truncation: headline-only",
    "C1_25pct":    "C1b — Truncation: 25% of text",
    "C1_50pct":    "C1c — Truncation: 50% of text",
    "C2_actor":    "C2a — Sentence dropout: actor keywords",
    "C2_action":   "C2b — Sentence dropout: action keywords",
    "C2_asset":    "C2c — Sentence dropout: asset keywords",
}


def pct(x):
    if x is None: return "—"
    return f"{100*x:.2f}%"

def f3(x):
    if x is None: return "—"
    return f"{x:.3f}"

def f4(x):
    if x is None: return "—"
    return f"{x:.4f}"


def main():
    baseline = json.load(open("rq3/rq3_baseline.json"))
    stats    = json.load(open("rq3/rq3_stats.json"))
    b_data   = json.load(open("rq3/rq3_scenarioB.json"))
    scores   = json.load(open("rq3/scenario_scores.json")) if Path("rq3/scenario_scores.json").exists() else {}

    L_lines = []
    def w(s=""): L_lines.append(s)

    w("# RQ3 — Robustness Evaluation Report")
    w()
    w("**Research Question 3:** How robust is the schema-constrained LLM framework "
      "against (A) linguistic variation, (B) class imbalance, and (C) incomplete "
      "information typical of Indonesian data breach incident reports?")
    w()
    w("**Hypothesis H3:** Performance degradation (ΔF1 = F1_baseline − F1_scenario) "
      "≤ 0.15 across all stress-test scenarios. "
      "*SUPPORTED* iff the upper bound of the 95% bootstrap CI for ΔF1 < 0.15 "
      "for every scenario.")
    w()

    # --- Baseline ---
    w("## 1. Baseline (Task 0 — Clean v3 Predictions)")
    w()
    w("| Metric | Value |")
    w("|---|---:|")
    w(f"| Overall macro-F1 (15 dim, per-record) | **{f4(baseline['overall_macro_f1'])}** |")
    w(f"| — 95% bootstrap CI | [{f4(baseline['overall_macro_f1_ci95'][0])}, "
      f"{f4(baseline['overall_macro_f1_ci95'][1])}] |")
    w(f"| Core-A4 macro-F1 excl-Unknown | **{f4(baseline['core_a4_f1_excl_unknown'])}** |")
    w(f"| Schema-violation rate (SVR) | {pct(baseline['svr'])} |")
    w(f"| n_records | {baseline['n_records']} |")
    w()

    # --- Scenarios A + C: ΔF1 table ---
    w("## 2. Scenario Results — F1, ΔF1, and H3 Verdict")
    w()
    w("ΔF1 = F1_baseline − F1_scenario (paired, same 72 documents). "
      "H3 SUPPORTED iff CI upper < 0.15.")
    w()
    w("| Scenario | F1 | ΔF1 | 95% CI ΔF1 | SVR | H3 |")
    w("|---|---:|---:|---|---:|---|")

    all_sc = list(SCENARIO_LABELS.keys())
    for sc in all_sc:
        if sc not in scores:
            label = SCENARIO_LABELS.get(sc, sc)
            w(f"| {label} | — | — | — | — | pending |")
            continue
        entry  = scores[sc]
        st     = stats["per_scenario"].get(sc, {})
        od     = st.get("overall_delta", {})
        label  = SCENARIO_LABELS.get(sc, sc)
        f1     = entry.get("overall_macro_f1")
        delta  = od.get("delta_mean")
        ci_lo  = od.get("ci95_lo")
        ci_hi  = od.get("ci95_hi")
        svr    = entry.get("svr")
        h3     = od.get("h3_supported")
        h3_str = "**SUPPORTED**" if h3 else "NOT SUP." if h3 is not None else "—"
        ci_str = f"[{f4(ci_lo)}, {f4(ci_hi)}]" if ci_lo is not None else "—"
        w(f"| {label} | {f4(f1)} | {f4(delta)} | {ci_str} | {pct(svr)} | {h3_str} |")
    w()

    # --- C3 natural ---
    c3 = stats.get("c3_natural_short_report", {})
    if c3:
        w("### C3 — Short-Report Natural Cross-Check (no perturbation)")
        w()
        w(f"Bottom quartile (n={c3.get('n_short','?')}, "
          f"len≤{c3.get('q25_length_threshold','?')} chars) vs top 3/4 "
          f"(n={c3.get('n_long','?')}):")
        w()
        w("| Subset | n | Mean F1 |")
        w("|---|---:|---:|")
        w(f"| Short reports (C3) | {c3.get('n_short','?')} | {f4(c3.get('short_mean_f1'))} |")
        w(f"| Longer reports     | {c3.get('n_long','?')} | {f4(c3.get('long_mean_f1'))} |")
        w()
        w(f"Δ(long−short) = {f4(c3.get('delta_long_minus_short'))}  "
          f"95% CI = [{f4(c3.get('bootstrap_ci95_delta',[None,None])[0])}, "
          f"{f4(c3.get('bootstrap_ci95_delta',[None,None])[1])}]")
        w(f"> {c3.get('note','')}")
        w()

    # --- Scenario B: imbalance ---
    w("## 3. Scenario B — Class Imbalance")
    w()
    w("### B1 — Per-Dimension Macro vs Micro F1 Gap")
    w()
    w("Positive gap = macro > micro (model performs better on balanced per-class "
      "metric than on overall token counts; driven by small-class recall).")
    w()
    w("| Dimension | Type | Macro-F1 | Micro-F1 | Gap |")
    w("|---|---|---:|---:|---:|")
    gap_rank = b_data.get("b1_macro_micro_gap_ranking", [])
    for entry in gap_rank:
        dim = entry["dim"]
        gap = entry["gap"]
        if dim in b_data["b1_single_label"]:
            d = b_data["b1_single_label"][dim]
            w(f"| {dim} | single | {f4(d.get('macro_f1_unweighted'))} | "
              f"{f4(d.get('micro_f1'))} | {f4(gap)} |")
        elif dim in b_data["b1_multi_label"]:
            d = b_data["b1_multi_label"][dim]
            w(f"| {dim} | multi | {f4(d.get('macro_f1_by_value'))} | "
              f"{f4(d.get('micro_f1'))} | {f4(gap)} |")
    w()

    # Per-class F1 for key single-label dims
    w("### B1 — Per-Class F1 + Support (single-label dimensions)")
    w()
    for dim, d in b_data["b1_single_label"].items():
        w(f"**{dim}** (macro-F1 incl-Unk={f4(d['macro_f1_incl_unknown'])}, "
          f"excl-Unk={f4(d['macro_f1_excl_unknown'])}, acc={pct(d['accuracy'])})")
        w()
        w("| Class | F1 | Precision | Recall | Support |")
        w("|---|---:|---:|---:|---:|")
        for cls, pc in sorted(d["per_class"].items(), key=lambda x: -x[1]["support"]):
            w(f"| {cls} | {f4(pc['f1'])} | {f4(pc['p'])} | {f4(pc['r'])} | {pc['support']} |")
        w()

    # B2
    w("### B2 — Rare-Class Stress Subset")
    w()
    b2 = b_data["b2_rare_class_subset"]
    w(f"Minority sectors: {b2['minority_sectors']}  ")
    w(f"Rare action_variety values (count < 3): {b2['rare_action_variety_values']}")
    w()
    w("| Subset | n | Mean F1 |")
    w("|---|---:|---:|")
    w(f"| Stress (minority sector + rare action) | {b2['n_stress']} | "
      f"{f4(b2['stress_mean_f1'])} |")
    w(f"| Majority | {b2['n_majority']} | {f4(b2['majority_mean_f1'])} |")
    w()
    w(f"Δ(majority−stress) = {f4(b2['delta_majority_minus_stress'])}  ")
    w(f"> {b2['h3_note']}")
    w()

    # B3
    w("### B3 — Sector Breakdown")
    w()
    w("| Sector | n | Mean F1 |")
    w("|---|---:|---:|")
    b3 = b_data["b3_sector_breakdown"]
    for sec, d in sorted(b3.items(), key=lambda x: -x[1].get("n",0) if isinstance(x[1],dict) else 0):
        if isinstance(d, dict) and "n" in d:
            w(f"| {sec} | {d['n']} | {f4(d['mean_f1'])} |")
    w()
    w(f"> {b3.get('_gov_dominance_note','')}")
    w()

    # --- McNemar + Bonferroni ---
    w("## 4. Statistical Tests")
    w()
    bonf = stats.get("bonferroni", {})
    w(f"**Bonferroni correction:** {bonf.get('n_mcnemar_comparisons','?')} McNemar comparisons, "
      f"α_adj = {bonf.get('alpha_adjusted','?'):.5f}, "
      f"reject raw (α=0.05): {bonf.get('n_reject_raw_alpha05','?')}, "
      f"reject Bonferroni: {bonf.get('n_reject_bonferroni','?')}.")
    w()

    # McNemar table (select available scenarios)
    avail_sc = [sc for sc in all_sc if sc in stats.get("per_scenario",{})]
    if avail_sc:
        w("### McNemar Test per Dimension (selected scenarios)")
        w()
        w("Rows = VERIS dimensions (binarised: F1≥0.5 = correct). "
          "b = baseline-correct/scenario-wrong, c = baseline-wrong/scenario-correct. "
          "Significant at Bonferroni-corrected α indicates a dimension significantly "
          "changed between baseline and scenario.")
        w()
        header = "| Dimension |" + "".join(f" {sc} p |" for sc in avail_sc)
        sep    = "|---|" + "---|" * len(avail_sc)
        w(header); w(sep)
        for dim in list(SINGLE_FIELDS.keys()) + list(MULTI_FIELDS):
            row = f"| {dim} |"
            for sc in avail_sc:
                mc = stats["per_scenario"][sc].get("mcnemar_per_dim", {}).get(dim, {})
                p  = mc.get("p_value")
                bk = stats["bonferroni"]["per_comparison"].get(f"{sc}__{dim}", {})
                sig = "*" if bk.get("reject") else ""
                row += f" {f4(p)}{sig} |" if p is not None else " — |"
            w(row)
        w()
        w("\\* = significant after Bonferroni correction.")
        w()

    # --- H3 Verdicts ---
    w("## 5. H3 Verdicts")
    w()
    w(f"**Aggregate:** {stats.get('h3_aggregate','?')}")
    w()
    w("| Scenario | ΔF1 CI upper | H3 |")
    w("|---|---:|---|")
    for sc, h3_ok in stats.get("h3_per_scenario", {}).items():
        od   = stats["per_scenario"].get(sc, {}).get("overall_delta", {})
        ci_h = od.get("ci95_hi")
        w(f"| {SCENARIO_LABELS.get(sc,sc)} | {f4(ci_h)} | "
          f"{'**SUPPORTED**' if h3_ok else 'NOT SUPPORTED'} |")
    w()
    w("*H3 SUPPORTED iff CI upper < 0.15.*")
    w()

    OUT_MD.write_text("\n".join(L_lines) + "\n", encoding="utf-8")
    print(f"[Final] wrote {OUT_MD}")


if __name__ == "__main__":
    main()
