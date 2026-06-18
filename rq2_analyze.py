#!/usr/bin/env python3
"""RQ2 Tasks 3-8 analysis. Consumes runs/<tag>/run_*.jsonl produced by rq2_run.py
and emits the four JSON deliverables + cross-verification stats. rq2_summary.md is
written by rq2_summary.py from these JSONs.

All schema-compliance numbers come from rq2_lib.validate_record (single source of
truth). Off-vocabulary == violation; never remapped.
"""
import json, itertools
from collections import defaultdict, Counter

import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
from statsmodels.stats.inter_rater import fleiss_kappa

import rq2_lib as L
from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS

TEMP_TAGS = {"temp0": 0.0, "temp0.3": 0.3, "temp0.7": 0.7}
N_FIELDS = len(ALL_FIELDS)  # 15
H2A = 0.10   # SVR threshold
H2B = 0.85   # agreement threshold


# --------------------------------------------------------------------------- #
def load_tag(tag):
    """Return [(meta, recs), ...] for each run file under rq2/runs/<tag>."""
    out = []
    for path in L.list_runs(f"rq2/runs/{tag}"):
        out.append(L.load_run(path))
    return out


def classify_source(url):
    """Source-type bucket from the URL domain. The corpus is news-dominated; the
    thesis taxonomy is BSSN / media / vendor / OSINT-regulatory. No BSSN domains
    are present, so this maps what exists: .go.id -> regulatory, known security/IT
    vendor domains -> vendor, everything else -> media."""
    d = (url or "").lower()
    if ".go.id" in d or "bawaslu" in d or "komdigi" in d or "ksp.go.id" in d:
        return "regulatory"
    vendor_markers = ("dtrust", "lintasarta", "netmarks", "cyberhub", "dspace",
                      "cloudcomputing", "mitraberdaya")
    if any(m in d for m in vendor_markers):
        return "vendor"
    if ".ac.id" in d or "univ" in d:
        return "academic"
    return "media"


# --------------------------------------------------------------------------- #
# Task 3 — determinism across the 5 temp0 runs
# --------------------------------------------------------------------------- #
def task3_determinism(temp0_runs):
    runs = [recs for _m, recs in temp0_runs]
    ids = list(runs[0].keys())
    per_doc = {}
    raw_identical = {}
    n_label_id = 0
    n_raw_id = 0
    for rid in ids:
        labels = [L.label_key(L.record_label(r[rid])) for r in runs]
        raws = [r[rid].get("_raw", "") for r in runs]
        lab_same = len(set(labels)) == 1
        raw_same = len(set(raws)) == 1
        per_doc[rid] = lab_same
        raw_identical[rid] = raw_same
        n_label_id += lab_same
        n_raw_id += raw_same
    deterministic = (n_label_id == len(ids))
    return {
        "n_runs": len(runs),
        "n_docs": len(ids),
        "deterministic_scored_fields": deterministic,
        "n_docs_label_identical": n_label_id,
        "n_docs_raw_identical": n_raw_id,
        "raw_byte_identical_all": (n_raw_id == len(ids)),
        "per_doc_label_identical": per_doc,
        "note": ("All scored A4 labels identical across the 5 temp=0/seed=42 runs: "
                 "agreement=1.0 is trivial and Fleiss is undefined for constant "
                 "dimensions; reproducibility evidence rests on the temperature "
                 "stability analysis (Task 6).") if deterministic else
                ("Scored A4 labels are NOT identical across all temp=0 runs; "
                 "agreement/Fleiss below are non-trivial."),
    }


# --------------------------------------------------------------------------- #
# Task 4 — schema compliance (H2a), aggregated over all temp0 runs
# --------------------------------------------------------------------------- #
def task4_schema(temp0_runs):
    n_outputs = 0
    n_violation = 0
    cause_counts = Counter()        # per-cause record counts (a record may hit several)
    cause_only = Counter()          # records whose ONLY cause is X (for clean attribution)
    tot_vals = tot_invocab = 0
    tot_present_fields = tot_required_fields = 0
    per_field_off = Counter(); per_field_tot = Counter()
    off_examples = defaultdict(Counter)

    for _m, recs in temp0_runs:
        for rid, entry in recs.items():
            n_outputs += 1
            v = L.validate_record(entry)
            if v["violation"]:
                n_violation += 1
            for c in v["causes"]:
                cause_counts[c] += 1
            if len(v["causes"]) == 1:
                cause_only[next(iter(v["causes"]))] += 1
            for (f, val) in v["detail"]["off_vocab"]:
                off_examples[f][val] += 1
            # completeness / conformance cells
            nv, niv, pf = L.value_cells(entry)
            tot_vals += nv; tot_invocab += niv
            tot_present_fields += pf
            tot_required_fields += N_FIELDS
            # per-field off-vocab rate (value-level)
            p = L.parsed_fields(entry)
            for f in ALL_FIELDS:
                if f in SINGLE_FIELDS:
                    val = L.canon_single(p.get(f))
                    if val == "":
                        continue
                    per_field_tot[f] += 1
                    if val not in L.ALLOWED[f]:
                        per_field_off[f] += 1
                else:
                    for x in (p.get(f) or []):
                        per_field_tot[f] += 1
                        if str(x) not in L.ALLOWED[f]:
                            per_field_off[f] += 1

    svr = n_violation / n_outputs if n_outputs else 0.0
    # one-sample proportion test vs 0.10
    z_two, p_two = proportions_ztest(n_violation, n_outputs, value=H2A,
                                     alternative="two-sided", prop_var=H2A)
    z_sm, p_sm = proportions_ztest(n_violation, n_outputs, value=H2A,
                                   alternative="smaller", prop_var=H2A)
    lo, hi = proportion_confint(n_violation, n_outputs, alpha=0.05, method="wilson")
    binom = stats.binomtest(n_violation, n_outputs, p=H2A, alternative="two-sided")

    return {
        "n_outputs": n_outputs,
        "n_violation_records": n_violation,
        "svr": svr,
        "svr_wilson_ci95": [lo, hi],
        "h2a_threshold": H2A,
        "test_proportions_ztest_two_sided": {"z": float(z_two), "p": float(p_two)},
        "test_proportions_ztest_smaller": {"z": float(z_sm), "p": float(p_sm),
                                           "alt": "SVR < 0.10"},
        "test_binomtest_two_sided_p": float(binom.pvalue),
        "h2a_verdict": ("SUPPORTED" if hi < H2A else "NOT SUPPORTED"),
        "h2a_rule": "SUPPORTED iff Wilson upper bound < 0.10",
        "cause_breakdown_records": dict(cause_counts),
        "cause_sole_records": dict(cause_only),
        "field_completeness_rate": (tot_present_fields / tot_required_fields
                                    if tot_required_fields else 0.0),
        "n_present_fields": tot_present_fields,
        "n_required_fields": tot_required_fields,
        "vocabulary_conformance_rate": (tot_invocab / tot_vals if tot_vals else 0.0),
        "n_value_cells": tot_vals,
        "n_invocab_cells": tot_invocab,
        "per_field_off_vocab": {
            f: {"values": per_field_tot[f], "off": per_field_off[f],
                "rate": (per_field_off[f] / per_field_tot[f]) if per_field_tot[f] else 0.0,
                "examples": off_examples[f].most_common(5)}
            for f in ALL_FIELDS
        },
    }


# --------------------------------------------------------------------------- #
# Task 5 — reproducibility (H2b)
# --------------------------------------------------------------------------- #
def pairwise_agreement(labels):
    """labels: list of full-label keys (one per run). Mean over all run-pairs of
    exact full-A4-label equality."""
    pairs = list(itertools.combinations(range(len(labels)), 2))
    same = sum(1 for a, b in pairs if labels[a] == labels[b])
    return same / len(pairs) if pairs else 1.0


def task5_reproducibility(temp0_runs, det):
    runs = [recs for _m, recs in temp0_runs]
    ids = list(runs[0].keys())
    R = len(runs)

    doc_pair_agree = {}
    doc_exact_all = {}
    for rid in ids:
        labels = [L.label_key(L.record_label(r[rid])) for r in runs]
        doc_pair_agree[rid] = pairwise_agreement(labels)
        doc_exact_all[rid] = 1.0 if len(set(labels)) == 1 else 0.0

    pair_vals = np.array([doc_pair_agree[r] for r in ids])
    exact_vals = np.array([doc_exact_all[r] for r in ids])
    mean_pair = float(pair_vals.mean())
    mean_exact = float(exact_vals.mean())

    # Fleiss kappa per dimension (raters = runs)
    fleiss = {}
    for f in ALL_FIELDS:
        # build item x category count table
        cats = sorted({L.dim_category(L.record_label(r[rid]), f)
                       for r in runs for rid in ids})
        cat_idx = {c: i for i, c in enumerate(cats)}
        table = np.zeros((len(ids), len(cats)), dtype=int)
        for di, rid in enumerate(ids):
            for r in runs:
                c = L.dim_category(L.record_label(r[rid]), f)
                table[di, cat_idx[c]] += 1
        if len(cats) <= 1:
            fleiss[f] = {"kappa": None, "note": "undefined: single category"}
        else:
            try:
                k = fleiss_kappa(table, method="fleiss")
                fleiss[f] = {"kappa": (None if np.isnan(k) else float(k)),
                             "n_categories": len(cats)}
                if np.isnan(k):
                    fleiss[f]["note"] = "undefined (nan)"
            except Exception as e:
                fleiss[f] = {"kappa": None, "note": f"error: {e}"}
    defined = [d["kappa"] for d in fleiss.values() if d.get("kappa") is not None]
    macro_kappa = float(np.mean(defined)) if defined else None

    # one-sample t-test of per-doc pairwise agreement vs 0.85
    if np.allclose(pair_vals.std(ddof=1) if len(pair_vals) > 1 else 0.0, 0.0):
        t_stat = float("nan"); p_val = float("nan")
        ci = [mean_pair, mean_pair]
        ttest_note = ("zero variance across documents (degenerate) — all per-doc "
                      "agreements identical; t-test undefined, CI collapses to the mean")
    else:
        t_stat, p_val = stats.ttest_1samp(pair_vals, H2B)
        sem = pair_vals.std(ddof=1) / np.sqrt(len(pair_vals))
        h = sem * stats.t.ppf(0.975, len(pair_vals) - 1)
        ci = [mean_pair - h, mean_pair + h]
        ttest_note = "one-sample t-test vs 0.85"
        t_stat = float(t_stat); p_val = float(p_val)

    return {
        "n_runs": R,
        "n_docs": len(ids),
        "mean_pairwise_agreement": mean_pair,
        "mean_exact_match_all_runs": mean_exact,
        "agreement_ci95_t": ci,
        "ttest_vs_0.85": {"t": t_stat, "p": p_val, "note": ttest_note},
        "h2b_threshold": H2B,
        "h2b_verdict": ("SUPPORTED" if ci[0] >= H2B else "NOT SUPPORTED"),
        "h2b_rule": "SUPPORTED iff lower bound of mean-agreement CI >= 0.85",
        "h2b_caveat": (det["note"] if det["deterministic_scored_fields"] else ""),
        "fleiss_kappa_per_dimension": fleiss,
        "fleiss_kappa_macro": macro_kappa,
        "determinism": det,
        "per_doc_pairwise_agreement": doc_pair_agree,
    }


# --------------------------------------------------------------------------- #
# Task 6 — temperature stability
# --------------------------------------------------------------------------- #
def svr_for_runs(runs):
    n = v = 0
    for _m, recs in runs:
        for entry in recs.values():
            n += 1
            if L.validate_record(entry)["violation"]:
                v += 1
    return (v / n if n else 0.0), v, n


def task6_temperature(all_runs, gold):
    out = {}
    for tag, temp in TEMP_TAGS.items():
        runs = all_runs[tag]
        if not runs:
            continue
        f1s = []
        for _m, recs in runs:
            # entry already carries the 15 A4 fields at top level; score_rq1 reads
            # them by name and ignores the underscore bookkeeping keys.
            f1s.append(L.run_macro_f1(recs, gold))
        f1s = np.array(f1s)
        svr, nv, no = svr_for_runs(runs)
        seeds = [m.get("seed") for m, _ in runs]
        out[tag] = {
            "temperature": temp,
            "n_runs": len(runs),
            "seeds": seeds,
            "macro_f1_per_run": [float(x) for x in f1s],
            "macro_f1_mean": float(f1s.mean()),
            "macro_f1_var_sample": float(f1s.var(ddof=1)) if len(f1s) > 1 else 0.0,
            "macro_f1_std_sample": float(f1s.std(ddof=1)) if len(f1s) > 1 else 0.0,
            "macro_f1_min": float(f1s.min()),
            "macro_f1_max": float(f1s.max()),
            "svr": svr, "n_violation": nv, "n_outputs": no,
        }
    return out


# --------------------------------------------------------------------------- #
# Task 7 — heterogeneity
# --------------------------------------------------------------------------- #
def task7_heterogeneity(temp0_runs):
    smeta = L.subset_meta()
    runs = [recs for _m, recs in temp0_runs]
    ids = list(runs[0].keys())

    def group_of(rid, dim):
        if dim == "source":
            return classify_source(smeta[rid]["url"])
        return smeta[rid].get(dim) or "unknown"

    result = {}
    for dim in ["sector", "language", "source"]:
        # SVR per group over all temp0 runs
        g_n = Counter(); g_v = Counter()
        for _m, recs in temp0_runs:
            for rid, entry in recs.items():
                g = group_of(rid, dim)
                g_n[g] += 1
                if L.validate_record(entry)["violation"]:
                    g_v[g] += 1
        # mean pairwise agreement per group
        g_agree = defaultdict(list)
        for rid in ids:
            labels = [L.label_key(L.record_label(r[rid])) for r in runs]
            g_agree[group_of(rid, dim)].append(pairwise_agreement(labels))
        result[dim] = {
            g: {
                "n_docs": len({rid for rid in ids if group_of(rid, dim) == g}),
                "n_outputs": g_n[g],
                "svr": (g_v[g] / g_n[g]) if g_n[g] else 0.0,
                "n_violation": g_v[g],
                "mean_agreement": float(np.mean(g_agree[g])) if g_agree[g] else None,
            }
            for g in sorted(g_n)
        }
    result["_note"] = ("source-type is derived from URL domain; the in-scope "
                       "corpus is news/media-dominated (no BSSN domains present), "
                       "so the 'media' bucket dominates and other buckets are tiny.")
    return result


# --------------------------------------------------------------------------- #
def main():
    gold, sub_ids = L.load_gold_subset()
    all_runs = {tag: load_tag(tag) for tag in TEMP_TAGS}
    temp0_runs = all_runs["temp0"]
    assert temp0_runs, "no temp0 runs found"

    # cross-verification (Task 8 part 1)
    xverify = {"per_run": {}, "issues": []}
    for tag, runs in all_runs.items():
        for i, (m, recs) in enumerate(runs, 1):
            present = set(recs.keys())
            missing = [rid for rid in sub_ids if rid not in present]
            extra = [rid for rid in present if rid not in set(sub_ids)]
            # field-slot count = #records * 15
            slots = len(recs) * N_FIELDS
            cells = 0
            for e in recs.values():
                p = L.parsed_fields(e)
                cells += sum(1 for f in ALL_FIELDS if f in p)
            key = f"{tag}/run_{i}"
            xverify["per_run"][key] = {
                "n_records": len(recs),
                "expected_records": len(sub_ids),
                "missing_records": missing,
                "extra_records": extra,
                "field_slots_expected": slots,
                "field_cells_present": cells,
            }
            if missing:
                xverify["issues"].append(f"{key}: missing {missing}")
            if extra:
                xverify["issues"].append(f"{key}: extra {extra}")

    det = task3_determinism(temp0_runs)
    schema = task4_schema(temp0_runs)
    repro = task5_reproducibility(temp0_runs, det)
    temp = task6_temperature(all_runs, gold)
    hetero = task7_heterogeneity(temp0_runs)

    # consistency cross-check: SVR(temp0) from Task4 vs Task6 temp0
    schema["_xcheck_svr_temp0_matches_task6"] = (
        abs(schema["svr"] - temp["temp0"]["svr"]) < 1e-9)
    xverify["svr_temp0_task4"] = schema["svr"]
    xverify["svr_temp0_task6"] = temp["temp0"]["svr"]
    xverify["consistent"] = (not xverify["issues"]) and schema["_xcheck_svr_temp0_matches_task6"]

    json.dump(schema, open("rq2/rq2_schema_compliance.json", "w"), indent=2, ensure_ascii=False)
    json.dump(repro, open("rq2/rq2_reproducibility.json", "w"), indent=2, ensure_ascii=False)
    json.dump(temp, open("rq2/rq2_temperature_stability.json", "w"), indent=2, ensure_ascii=False)
    json.dump(hetero, open("rq2/rq2_heterogeneity.json", "w"), indent=2, ensure_ascii=False)
    json.dump(xverify, open("rq2/rq2_xverify.json", "w"), indent=2, ensure_ascii=False)

    print("[T3] deterministic(scored):", det["deterministic_scored_fields"],
          "| label-identical docs:", det["n_docs_label_identical"], "/", det["n_docs"],
          "| raw-identical docs:", det["n_docs_raw_identical"])
    print(f"[T4] SVR={schema['svr']:.4f} Wilson CI=[{schema['svr_wilson_ci95'][0]:.4f},"
          f"{schema['svr_wilson_ci95'][1]:.4f}] verdict={schema['h2a_verdict']} "
          f"| completeness={schema['field_completeness_rate']:.4f} "
          f"conformance={schema['vocabulary_conformance_rate']:.4f} "
          f"causes={schema['cause_breakdown_records']}")
    print(f"[T5] mean_pairwise_agree={repro['mean_pairwise_agreement']:.4f} "
          f"exact_all={repro['mean_exact_match_all_runs']:.4f} "
          f"CI={repro['agreement_ci95_t']} macroFleiss={repro['fleiss_kappa_macro']} "
          f"verdict={repro['h2b_verdict']}")
    for tag, d in temp.items():
        print(f"[T6] {tag}: F1 mean={d['macro_f1_mean']:.4f} var={d['macro_f1_var_sample']:.2e} "
              f"runs={d['macro_f1_per_run']} SVR={d['svr']:.4f}")
    print(f"[T8] xverify consistent={xverify['consistent']} issues={xverify['issues']}")


if __name__ == "__main__":
    main()
