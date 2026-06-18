#!/usr/bin/env python3
"""RQ2 Tasks D/E/F — re-validate & re-score the SAME stored outputs with the
enum-completeness fix (no model re-inference). Emits BEFORE-vs-AFTER.

BEFORE = the saved rq2_schema_compliance.json / rq2_heterogeneity.json
         (computed with the pre-fix enum).
AFTER  = recomputed now; rq2_lib/score_rq1 import the (now fixed) veris_enums.
"""
import json
import numpy as np

import rq2_lib as L
import rq2_analyze as A
import score_rq1 as sc
from veris_fields import MULTI_FIELDS, ALL_FIELDS

H2A = 0.10


def verdict(lo, hi):
    if hi < H2A:
        return "SUPPORTED (Wilson upper < 10%)"
    if lo >= H2A:
        return "NOT SUPPORTED (Wilson CI entirely >= 10%)"
    return "INCONCLUSIVE (Wilson CI straddles 10%)"


def main():
    # ---------- AFTER: re-validate stored temp0 outputs ----------
    temp0 = A.load_tag("temp0")
    after = A.task4_schema(temp0)
    after["h2a_verdict_preregistered"] = verdict(*after["svr_wilson_ci95"])

    before = json.load(open("rq2/rq2_schema_compliance.json"))

    # ---------- Task D: BEFORE vs AFTER table ----------
    keymetrics = ["svr", "n_violation_records", "field_completeness_rate",
                  "vocabulary_conformance_rate"]
    dtable = {k: {"before": before.get(k), "after": after.get(k)} for k in keymetrics}
    dtable["svr_wilson_ci95"] = {"before": before["svr_wilson_ci95"],
                                 "after": after["svr_wilson_ci95"]}
    dtable["cause_breakdown_records"] = {"before": before["cause_breakdown_records"],
                                         "after": after["cause_breakdown_records"]}
    dtable["cause_sole_records"] = {"before": before["cause_sole_records"],
                                    "after": after["cause_sole_records"]}
    dtable["per_field_off_vocab_after"] = {
        f: d for f, d in after["per_field_off_vocab"].items() if d["off"] > 0}

    out_v2 = {
        "policy": ("controlled vocabulary = full official VERIS 1.3.x per field; "
                   "enum must be a superset of frozen gold. Off-vocab = violation, "
                   "never remapped."),
        "enum_changes": [
            {"value": "Defacement", "field": "action.hacking.variety (->action_variety)",
             "reason": "gold GS-080 uses action_variety=Defacement (Hacking, web defacement)"},
            {"value": "Destroy data", "field": "attribute.integrity.variety",
             "reason": "gold GS-020 uses attr_integrity_variety=Destroy data"},
            {"value": "Encryption", "field": "attribute.availability.variety",
             "reason": "gold GS-026 (ransomware) uses attr_avail_variety=Encryption"},
        ],
        "enum_NOT_changed": [
            {"value": "Obscuration", "field": "attribute.integrity.variety",
             "reason": ("official VERIS places Obscuration under availability (already "
                        "in enum), not integrity; gold never uses it -> genuine "
                        "off-vocab violation, kept")},
        ],
        "before": {k: before.get(k) for k in
                   ["svr", "svr_wilson_ci95", "n_violation_records", "n_outputs",
                    "field_completeness_rate", "vocabulary_conformance_rate",
                    "cause_breakdown_records", "cause_sole_records"]},
        "after": {k: after.get(k) for k in
                  ["svr", "svr_wilson_ci95", "n_violation_records", "n_outputs",
                   "field_completeness_rate", "vocabulary_conformance_rate",
                   "cause_breakdown_records", "cause_sole_records",
                   "test_proportions_ztest_two_sided", "test_proportions_ztest_smaller",
                   "test_binomtest_two_sided_p", "per_field_off_vocab"]},
        "before_vs_after": dtable,
        "h2a_verdict_before": before.get("h2a_verdict"),
        "h2a_verdict_after_preregistered": after["h2a_verdict_preregistered"],
    }
    json.dump(out_v2, open("rq2/rq2_schema_compliance_v2.json", "w"), indent=2, ensure_ascii=False)

    # ---------- Task F: heterogeneity v2 ----------
    hetero_after = A.task7_heterogeneity(temp0)
    json.dump(hetero_after, open("rq2/rq2_heterogeneity_v2.json", "w"), indent=2, ensure_ascii=False)

    # ---------- Task E: F1 deltas ----------
    # RQ2 subset (n=50), temp0 run 1 (deterministic) — enum does NOT enter F1
    # scoring (multi-label uses string set-match and never drops off-vocab preds),
    # so we verify the delta empirically.
    gold50, _ = L.load_gold_subset()
    _m, recs = temp0[0]
    f1_rq2 = L.run_macro_f1(recs, gold50)

    # RQ1 full set (n=72): re-score the saved v3 predictions with the new enum
    gold72 = sc.load_gold()
    preds72_all = json.load(open("rq1/predictions_v3_fewshot_seed42.json"))
    preds72 = {k: v for k, v in preds72_all.items() if not k.startswith("_")}
    f1_rq1 = L.run_macro_f1(preds72, gold72)
    # per-dim multi F1 for the two touched fields
    av = sc.multi_label_metrics("action_variety", preds72, gold72)["macro_f1"]
    iv = sc.multi_label_metrics("attr_integrity_variety", preds72, gold72)["macro_f1"]

    m_old = json.load(open("rq1/metrics_v3_seed42.json"))
    rq1_old_overall = m_old["overall"]["macro_f1_per_record_mean"]
    rq1_old_av = m_old["multi_label"]["action_variety"]["macro_f1"]
    rq1_old_iv = m_old["multi_label"]["attr_integrity_variety"]["macro_f1"]

    f1_report = {
        "note": ("Enum changes affect schema-compliance only. F1 scoring "
                 "(score_rq1.multi_label_metrics) matches predicted vs gold label "
                 "SETS by string and never filtered/remapped off-vocab predictions, "
                 "so a Defacement match was already credited. Deltas are expected "
                 "to be 0; verified empirically below."),
        "rq2_subset_n50": {
            "macro_f1_after": f1_rq2, "baseline": 0.676,
            "delta_vs_0.676": round(f1_rq2 - 0.676, 6),
        },
        "rq1_n72_v3": {
            "overall_macro_f1_old": rq1_old_overall,
            "overall_macro_f1_after": f1_rq1,
            "overall_delta": round(f1_rq1 - rq1_old_overall, 6),
            "action_variety_f1_old": rq1_old_av, "action_variety_f1_after": av,
            "action_variety_delta": round(av - rq1_old_av, 6),
            "attr_integrity_variety_f1_old": rq1_old_iv,
            "attr_integrity_variety_f1_after": iv,
            "attr_integrity_variety_delta": round(iv - rq1_old_iv, 6),
        },
        "rq1_chapter4_table_change_needed": bool(
            abs(f1_rq1 - rq1_old_overall) > 1e-9 or abs(av - rq1_old_av) > 1e-9
            or abs(iv - rq1_old_iv) > 1e-9),
    }
    json.dump(f1_report, open("rq2/rq2_f1_delta_enumfix.json", "w"), indent=2, ensure_ascii=False)

    # ---------- console summary ----------
    print("=== TASK D: schema compliance BEFORE vs AFTER (250 temp0 outputs) ===")
    print(f"  SVR            : {before['svr']*100:.2f}%  ->  {after['svr']*100:.2f}%")
    print(f"  Wilson 95% CI  : [{before['svr_wilson_ci95'][0]*100:.2f},"
          f"{before['svr_wilson_ci95'][1]*100:.2f}]  ->  "
          f"[{after['svr_wilson_ci95'][0]*100:.2f},{after['svr_wilson_ci95'][1]*100:.2f}]")
    print(f"  violation recs : {before['n_violation_records']}  ->  {after['n_violation_records']} / {after['n_outputs']}")
    print(f"  completeness   : {before['field_completeness_rate']*100:.2f}%  ->  {after['field_completeness_rate']*100:.2f}%")
    print(f"  vocab conform  : {before['vocabulary_conformance_rate']*100:.4f}%  ->  {after['vocabulary_conformance_rate']*100:.4f}%")
    print(f"  causes         : {before['cause_breakdown_records']}  ->  {after['cause_breakdown_records']}")
    print(f"  sole-cause     : {before['cause_sole_records']}  ->  {after['cause_sole_records']}")
    print(f"  remaining off-vocab fields: "
          f"{ {f:d['examples'] for f,d in after['per_field_off_vocab'].items() if d['off']>0} }")
    print(f"  H2a verdict (pre-registered): {after['h2a_verdict_preregistered']}")
    print()
    print("=== TASK E: F1 deltas ===")
    print(f"  RQ2 n=50 macro-F1 after enum fix: {f1_rq2:.4f}  (delta vs 0.676 = {f1_rq2-0.676:+.6f})")
    print(f"  RQ1 n=72 overall: {rq1_old_overall:.4f} -> {f1_rq1:.4f} (delta {f1_rq1-rq1_old_overall:+.6f})")
    print(f"  RQ1 action_variety F1: {rq1_old_av:.4f} -> {av:.4f} (delta {av-rq1_old_av:+.6f})")
    print(f"  RQ1 attr_integrity_variety F1: {rq1_old_iv:.4f} -> {iv:.4f} (delta {iv-rq1_old_iv:+.6f})")
    print(f"  RQ1 chapter_4 table change needed: {f1_report['rq1_chapter4_table_change_needed']}")
    print()
    print("[wrote] rq2_schema_compliance_v2.json, rq2_heterogeneity_v2.json, rq2_f1_delta_enumfix.json")


if __name__ == "__main__":
    main()
