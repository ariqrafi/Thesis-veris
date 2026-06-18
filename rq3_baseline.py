#!/usr/bin/env python3
"""RQ3 Task 0 — Baseline robustness score from existing v3 predictions.

Reuses rq1/predictions_v3_fewshot_seed42.json (already generated).
Verifies leakage-safe: none of the 72 eval records share a content_hash
with the 6 few-shot exemplars.

Outputs:
  rq3/rq3_baseline.json   per-record F1 + aggregate metrics (reference for ΔF1)
"""
import json, sys, time
sys.path.insert(0, ".")
import numpy as np
import rq3_lib as L

PREDS_FILE = "rq1/predictions_v3_fewshot_seed42.json"
OUT_FILE   = "rq3/rq3_baseline.json"


def main():
    print("[Task 0] Loading v3 predictions ...")
    preds_all = json.load(open(PREDS_FILE))
    run_meta  = preds_all.get("_run_meta", {})
    preds     = {k: v for k, v in preds_all.items() if not k.startswith("_")}
    print(f"  {len(preds)} prediction records  |  model={run_meta.get('model')}  "
          f"digest={str(run_meta.get('model_digest',''))[:16]}")

    # -------- leakage check --------
    eval72    = L.load_72_records()
    ex_hashes = L.exemplar_hashes()
    eval_hashes = {r.get("content_hash") for r in eval72.values()}
    overlap   = eval_hashes & ex_hashes
    leakage_safe = len(overlap) == 0
    print(f"[Leakage check] exemplar hashes={len(ex_hashes)}, "
          f"eval72 hashes={len(eval_hashes)}, overlap={overlap} "
          f"-> leakage_safe={leakage_safe}")
    assert leakage_safe, f"LEAKAGE: {overlap}"

    # -------- score --------
    print("[Task 0] Scoring ...")
    res = L.score_predictions(preds_all)

    # -------- bootstrap CI for overall macro-F1 --------
    gold  = L.load_gold()
    rids  = list(gold.keys())
    f1vec = np.array([res["per_record_f1"][r] for r in rids])
    rng   = np.random.default_rng(42)
    n     = len(f1vec)
    boots = np.array([f1vec[rng.integers(0, n, n)].mean() for _ in range(1000)])
    ci_lo, ci_hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))

    # -------- text length stats (needed for C3 short-report subset) --------
    text_lengths = {}
    for rid, rec in eval72.items():
        txt = rec.get("full_content_clean") or rec.get("full_content") or ""
        text_lengths[rid] = len(txt)
    sorted_lens = sorted(text_lengths.items(), key=lambda x: x[1])
    q25_threshold = sorted_lens[len(sorted_lens) // 4][1]  # 25th percentile length

    # -------- assemble output --------
    out = {
        "scenario": "baseline",
        "source_preds": PREDS_FILE,
        "run_meta": run_meta,
        "leakage_check": {
            "exemplar_hashes": sorted(ex_hashes),
            "eval72_hashes": sorted(eval_hashes),
            "overlap": sorted(overlap),
            "leakage_safe": leakage_safe,
        },
        "n_records": res["n_records"],
        "overall_macro_f1": res["overall_macro_f1"],
        "overall_macro_f1_ci95": [ci_lo, ci_hi],
        "core_a4_f1_excl_unknown": res["core_a4_f1_excl_unknown"],
        "svr": res["svr"],
        "dim_headline_f1": res["dim_headline_f1"],
        "per_record_f1": res["per_record_f1"],
        "text_lengths": text_lengths,
        "q25_length_threshold": q25_threshold,
        "c3_short_record_ids": [rid for rid, l in sorted_lens[:len(sorted_lens)//4]],
        "schema_compliance_summary": {
            "svr":   res["svr"],
            "n_vio": res["schema"].get("n_violation_records",
                                       res["schema"].get("off_vocab", 0)),
            "n_out": res["schema"].get("n_outputs", res["n_records"]),
        },
    }
    json.dump(out, open(OUT_FILE, "w"), indent=2, ensure_ascii=False)

    print(f"\n[Task 0] Results:")
    print(f"  overall macro-F1 = {res['overall_macro_f1']:.4f}  CI=[{ci_lo:.4f},{ci_hi:.4f}]")
    print(f"  Core-A4 excl-Unk = {res['core_a4_f1_excl_unknown']:.4f}")
    print(f"  SVR              = {res['svr']:.4f}")
    print(f"  C3 short subset  = {len(out['c3_short_record_ids'])} records (len<={q25_threshold})")
    print(f"  -> {OUT_FILE}")


if __name__ == "__main__":
    main()
