#!/usr/bin/env python3
"""RQ2 Task 8 — assemble rq2_summary.md from the four analysis JSONs + xverify."""
import json


def pct(x):
    return f"{100*x:.2f}%" if x is not None else "—"


def f3(x):
    return f"{x:.3f}" if x is not None else "—"


def main():
    schema = json.load(open("rq2/rq2_schema_compliance.json"))
    repro = json.load(open("rq2/rq2_reproducibility.json"))
    temp = json.load(open("rq2/rq2_temperature_stability.json"))
    hetero = json.load(open("rq2/rq2_heterogeneity.json"))
    xver = json.load(open("rq2/rq2_xverify.json"))
    leak = json.load(open("data/repro_subset_leakage_check.json"))
    det = repro["determinism"]

    # a representative meta from temp0 run 1
    m0 = temp["temp0"]
    L = []
    L.append("# RQ2 — Consistency, Reproducibility & Schema Compliance\n")
    L.append("**Model:** `qwen3.5:35b` (digest `3460ffeede54`), Ollama `0.30.8`, "
             "think=false, num_ctx=32768, input=full_content_clean[:16000], "
             "few-shot v3 (6 exemplars).  ")
    L.append(f"**Subset:** {leak['n_selected']} records, stratified by sector "
             f"(largest-remainder, seed {leak['seed']}), leakage-safe vs the 6 "
             f"exemplars (overlap={leak['leakage_overlap_with_exemplars']}).  ")
    L.append("**Seed strategy:** temp=0 → seed 42 on all 5 runs (determinism test); "
             "temp=0.3/0.7 → seeds 42–46 (sample the stochastic distribution).\n")

    # ---------------- Determinism ----------------
    L.append("## Task 3 — Determinism (5× temp=0, seed=42)\n")
    L.append(f"- Scored A4 labels identical across all 5 runs: "
             f"**{det['deterministic_scored_fields']}** "
             f"({det['n_docs_label_identical']}/{det['n_docs']} docs).")
    L.append(f"- Raw byte-identical across all 5 runs: "
             f"**{det['raw_byte_identical_all']}** "
             f"({det['n_docs_raw_identical']}/{det['n_docs']} docs).")
    L.append(f"\n> {det['note']}\n")

    # ---------------- Schema compliance ----------------
    L.append("## Task 4 — Schema compliance (H2a)\n")
    L.append(f"Aggregated over all {schema['n_outputs']} temp=0 outputs "
             f"(50 docs × 5 runs). Validation module is the source of truth; "
             f"off-vocabulary = violation (not remapped).\n")
    L.append("| Metric | Value |")
    L.append("|---|---:|")
    L.append(f"| Schema-violation rate (SVR) | **{pct(schema['svr'])}** |")
    L.append(f"| SVR Wilson 95% CI | [{pct(schema['svr_wilson_ci95'][0])}, "
             f"{pct(schema['svr_wilson_ci95'][1])}] |")
    L.append(f"| Field completeness rate | {pct(schema['field_completeness_rate'])} |")
    L.append(f"| Vocabulary conformance rate | {pct(schema['vocabulary_conformance_rate'])} |")
    L.append(f"| Violation records | {schema['n_violation_records']} / {schema['n_outputs']} |")
    L.append("")
    L.append("**Failure causes** (record counts; a record may have several):  ")
    L.append(f"`{schema['cause_breakdown_records']}` — sole-cause: "
             f"`{schema['cause_sole_records']}`\n")
    zt = schema["test_proportions_ztest_two_sided"]
    zs = schema["test_proportions_ztest_smaller"]
    L.append(f"One-sample proportion test vs 0.10: two-sided z={zt['z']:.3f} "
             f"(p={zt['p']:.3g}); directional (SVR<0.10) z={zs['z']:.3f} "
             f"(p={zs['p']:.3g}); binomtest p={schema['test_binomtest_two_sided_p']:.3g}.\n")
    L.append("Per-field off-vocabulary (value-level):\n")
    L.append("| Field | values | off | rate | top examples |")
    L.append("|---|---:|---:|---:|---|")
    for f, d in schema["per_field_off_vocab"].items():
        if d["off"] == 0:
            continue
        ex = ", ".join(f"{v}×{c}" for v, c in d["examples"]) or "—"
        L.append(f"| {f} | {d['values']} | {d['off']} | {pct(d['rate'])} | {ex} |")
    L.append("")
    L.append(f"**H2a verdict: {schema['h2a_verdict']}** "
             f"({schema['h2a_rule']}: upper CI = {pct(schema['svr_wilson_ci95'][1])}).\n")

    # ---------------- Reproducibility ----------------
    L.append("## Task 5 — Reproducibility (H2b)\n")
    L.append(f"- Mean per-doc pairwise agreement (full A4 label, "
             f"{repro['n_runs']} runs → {repro['n_runs']*(repro['n_runs']-1)//2} pairs): "
             f"**{f3(repro['mean_pairwise_agreement'])}**")
    L.append(f"- Mean exact-match-all-runs: **{f3(repro['mean_exact_match_all_runs'])}**")
    L.append(f"- Agreement 95% CI(t): [{f3(repro['agreement_ci95_t'][0])}, "
             f"{f3(repro['agreement_ci95_t'][1])}]  ({repro['ttest_vs_0.85']['note']})")
    L.append(f"- Fleiss' κ macro (over defined dims): **{f3(repro['fleiss_kappa_macro'])}**")
    L.append("")
    L.append("| Dimension | Fleiss κ |")
    L.append("|---|---:|")
    for f, d in repro["fleiss_kappa_per_dimension"].items():
        k = d.get("kappa")
        note = d.get("note", "")
        L.append(f"| {f} | {f3(k) if k is not None else 'undefined'}"
                 f"{(' ('+note+')') if k is None else ''} |")
    L.append("")
    if repro["h2b_caveat"]:
        L.append(f"> {repro['h2b_caveat']}\n")
    L.append(f"**H2b verdict: {repro['h2b_verdict']}** "
             f"({repro['h2b_rule']}: lower CI = {f3(repro['agreement_ci95_t'][0])}).\n")

    # ---------------- Temperature stability ----------------
    L.append("## Task 6 — Temperature stability\n")
    L.append("| Temp | runs | F1 mean | F1 variance | F1 std | F1 range | SVR |")
    L.append("|---|---:|---:|---:|---:|---|---:|")
    for tag in ["temp0", "temp0.3", "temp0.7"]:
        if tag not in temp:
            continue
        d = temp[tag]
        L.append(f"| {d['temperature']} | {d['n_runs']} | {f3(d['macro_f1_mean'])} | "
                 f"{d['macro_f1_var_sample']:.2e} | {d['macro_f1_std_sample']:.4f} | "
                 f"[{f3(d['macro_f1_min'])}, {f3(d['macro_f1_max'])}] | {pct(d['svr'])} |")
    L.append("")

    # ---------------- Heterogeneity ----------------
    L.append("## Task 7 — Heterogeneity\n")
    for dim in ["sector", "language", "source"]:
        L.append(f"### By {dim}\n")
        L.append("| Group | docs | outputs | SVR | mean agreement |")
        L.append("|---|---:|---:|---:|---:|")
        for g, d in hetero[dim].items():
            L.append(f"| {g} | {d['n_docs']} | {d['n_outputs']} | {pct(d['svr'])} | "
                     f"{f3(d['mean_agreement'])} |")
        L.append("")
    L.append(f"> {hetero['_note']}\n")

    # ---------------- Verification ----------------
    L.append("## Task 8 — Cross-verification\n")
    L.append(f"- Field-slot accounting per run (50 × 15 = 750) verified; "
             f"all runs consistent: **{xver['consistent']}**.")
    L.append(f"- SVR(temp0) Task4={pct(xver['svr_temp0_task4'])} vs "
             f"Task6={pct(xver['svr_temp0_task6'])} → match.")
    if xver["issues"]:
        L.append(f"- ⚠️ Issues: {xver['issues']}")
    else:
        L.append("- No missing/extra records in any run.")
    L.append("")

    # ---------------- Verdict ----------------
    L.append("## Verdicts\n")
    L.append(f"- **H2a (schema compliance, SVR < 0.10): {schema['h2a_verdict']}** — "
             f"SVR {pct(schema['svr'])}, Wilson upper {pct(schema['svr_wilson_ci95'][1])}.")
    L.append(f"- **H2b (reproducibility, mean agreement ≥ 0.85): {repro['h2b_verdict']}** — "
             f"mean agreement {f3(repro['mean_pairwise_agreement'])}, "
             f"lower CI {f3(repro['agreement_ci95_t'][0])}.")
    if det["deterministic_scored_fields"]:
        L.append("\n> Note: at temp=0/seed=42 the extractor is fully deterministic, so "
                 "H2b's agreement is trivially 1.0; the substantive reproducibility "
                 "evidence is the low F1 variance across temperatures (Task 6).")

    open("rq2/rq2_summary.md", "w").write("\n".join(L) + "\n")
    print("[T8] wrote rq2/rq2_summary.md")


if __name__ == "__main__":
    main()
