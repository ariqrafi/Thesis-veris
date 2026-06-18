#!/usr/bin/env python3
"""RQ1 scorer: compare predictions_seed<SEED>.json against the scorable gold
subset and compute schema compliance (RQ2 by-product), RQ1 accuracy, and stats.

Outputs:
  metrics_seed<SEED>.json   machine-readable
  report_seed<SEED>.md      human-readable
  errors_seed<SEED>.csv     per-record per-single-label-dimension rows

Stdlib + numpy + scipy only.
"""
import argparse, json, csv, math
from collections import defaultdict, Counter

import numpy as np
from scipy import stats

from veris_enums import ENUMS
from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS, allowed_values

GOLD_FILE = "data/gold_standard.json"
H1 = 0.70
SECTORS = ["government", "financial", "telco", "education_healthcare", "unknown"]


# --------------------------------------------------------------------------- #
def load_gold():
    g = json.load(open(GOLD_FILE))
    if "annotations" in g and isinstance(g.get("annotations"), dict):
        g = g["annotations"]
    return {rid: v for rid, v in g.items() if v.get("in_scope") == "Yes"}


def norm_single(v):
    """Predicted single value -> string (or '' if missing/listy)."""
    if isinstance(v, list):
        return v[0] if len(v) == 1 else ("" if not v else str(v[0]))
    return "" if v is None else str(v)


def norm_multi(v):
    """Predicted/gold multi value -> list of strings."""
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v else []
    return [str(x) for x in v]


def sector_of(rid, gold):
    return gold[rid].get("_meta", {}).get("sector") or "unknown"


# --------------------------------------------------------------------------- #
# (A) Schema compliance
# --------------------------------------------------------------------------- #
def schema_compliance(preds, gold):
    per_field = {}  # field -> {total, off, off_values:Counter}
    for f in ALL_FIELDS:
        per_field[f] = {"total": 0, "off": 0, "off_values": Counter()}
    allowed = {f: allowed_values(f) for f in ALL_FIELDS}

    for rid in gold:
        p = preds.get(rid, {})
        for f in SINGLE_FIELDS:
            val = norm_single(p.get(f))
            if val == "":
                # missing prediction counts as 1 value, off-vocab
                per_field[f]["total"] += 1
                per_field[f]["off"] += 1
                per_field[f]["off_values"]["<missing>"] += 1
                continue
            per_field[f]["total"] += 1
            if val not in allowed[f]:
                per_field[f]["off"] += 1
                per_field[f]["off_values"][val] += 1
        for f in MULTI_FIELDS:
            for val in norm_multi(p.get(f)):
                per_field[f]["total"] += 1
                if val not in allowed[f]:
                    per_field[f]["off"] += 1
                    per_field[f]["off_values"][val] += 1

    total = sum(d["total"] for d in per_field.values())
    off = sum(d["off"] for d in per_field.values())
    return {
        "total_values": total,
        "off_vocab": off,
        "violation_rate": (off / total) if total else 0.0,
        "per_field": {
            f: {
                "total": d["total"], "off": d["off"],
                "rate": (d["off"] / d["total"]) if d["total"] else 0.0,
                "examples": d["off_values"].most_common(5),
            }
            for f, d in per_field.items()
        },
    }


# --------------------------------------------------------------------------- #
# (B) Accuracy helpers
# --------------------------------------------------------------------------- #
def prf_from_counts(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def single_label_metrics(field, preds, gold):
    """Accuracy + per-class P/R/F1 -> macro (incl/excl Unknown) + micro."""
    allowed = allowed_values(field)
    pairs = []  # (gold, pred, off_vocab)
    for rid in gold:
        g = norm_single(gold[rid].get(field))
        pv = norm_single(preds.get(rid, {}).get(field))
        off = pv not in allowed
        # off-vocab predictions are wrong (not remapped); keep raw for confusion
        pairs.append((g, pv, off))

    n = len(pairs)
    correct = sum(1 for g, p, _ in pairs if g == p)
    acc = correct / n if n else 0.0

    classes = sorted(set(g for g, _, _ in pairs) | set(p for _, p, _ in pairs if not _))
    per_class = {}
    for c in classes:
        tp = sum(1 for g, p, _ in pairs if g == c and p == c)
        fp = sum(1 for g, p, _ in pairs if g != c and p == c)
        fn = sum(1 for g, p, _ in pairs if g == c and p != c)
        pr, rc, f1 = prf_from_counts(tp, fp, fn)
        per_class[c] = {"p": pr, "r": rc, "f1": f1,
                        "support": sum(1 for g, _, _ in pairs if g == c)}

    gold_classes = sorted(set(g for g, _, _ in pairs))
    macro_incl = float(np.mean([per_class[c]["f1"] for c in gold_classes])) if gold_classes else 0.0
    gc_excl = [c for c in gold_classes if c != "Unknown"]
    macro_excl = float(np.mean([per_class[c]["f1"] for c in gc_excl])) if gc_excl else 0.0
    # micro over gold classes (= accuracy for single-label multiclass)
    micro = acc
    return {
        "accuracy": acc, "n": n, "correct": correct,
        "macro_f1_incl_unknown": macro_incl,
        "macro_f1_excl_unknown": macro_excl,
        "micro_f1": micro,
        "per_class": per_class,
        "pairs": pairs,
    }


def multi_label_metrics(field, preds, gold):
    """Per-record set P/R/F1 (macro-by-record) + micro by pooling."""
    allowed = allowed_values(field)
    rec_f1 = []
    rec_p = []
    rec_r = []
    micro_tp = micro_fp = micro_fn = 0
    per_record = {}
    for rid in gold:
        gset = set(norm_multi(gold[rid].get(field)))
        # off-vocab predicted labels are kept (they simply won't match gold)
        pset = set(norm_multi(preds.get(rid, {}).get(field)))
        tp = len(gset & pset)
        fp = len(pset - gset)
        fn = len(gset - pset)
        p, r, f = prf_from_counts(tp, fp, fn)
        # convention: both empty -> perfect (no labels expected, none given)
        if not gset and not pset:
            p = r = f = 1.0
        rec_p.append(p); rec_r.append(r); rec_f1.append(f)
        micro_tp += tp; micro_fp += fp; micro_fn += fn
        per_record[rid] = f
    mp, mr, mf = (float(np.mean(rec_p)), float(np.mean(rec_r)), float(np.mean(rec_f1))) \
        if rec_f1 else (0.0, 0.0, 0.0)
    up, ur, uf = prf_from_counts(micro_tp, micro_fp, micro_fn)
    return {
        "macro_p": mp, "macro_r": mr, "macro_f1": mf,
        "micro_p": up, "micro_r": ur, "micro_f1": uf,
        "per_record": per_record,
    }


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--runs", type=int, default=1, help="reserved for RQ2 multi-run")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--tag", default="", help="output label, e.g. v2 -> *_v2_seed42.*")
    ap.add_argument("--preds", default=None, help="predictions file (default by seed/tag)")
    args = ap.parse_args()

    suffix = f"_{args.tag}_seed{args.seed}" if args.tag else f"_seed{args.seed}"
    preds_path = args.preds or f"rq1/predictions{suffix}.json"
    preds_all = json.load(open(preds_path))
    run_meta = preds_all.get("_run_meta", {})
    preds = {k: v for k, v in preds_all.items() if not k.startswith("_")}
    gold = load_gold()
    rids = list(gold.keys())
    n_salvaged = sum(1 for rid in rids if preds.get(rid, {}).get("_salvaged"))
    salvaged_ids = [rid for rid in rids if preds.get(rid, {}).get("_salvaged")]

    # ---- (A) schema compliance
    schema = schema_compliance(preds, gold)

    # ---- (B) per-dimension metrics
    single_res = {f: single_label_metrics(f, preds, gold) for f in SINGLE_FIELDS}
    multi_res = {f: multi_label_metrics(f, preds, gold) for f in MULTI_FIELDS}

    # per-record per-dimension F1, then per-record macro-F1 (headline distribution)
    rid_idx = {rid: i for i, rid in enumerate(rids)}
    single_correct = {f: {} for f in SINGLE_FIELDS}
    for f in SINGLE_FIELDS:
        for i, rid in enumerate(rids):
            g, p, off = single_res[f]["pairs"][i]
            single_correct[f][rid] = 1.0 if g == p else 0.0

    per_record_f1 = {}  # rid -> macro over 15 dims (7 single + 8 multi)
    for rid in rids:
        dims = [single_correct[f][rid] for f in SINGLE_FIELDS]
        dims += [multi_res[f]["per_record"][rid] for f in MULTI_FIELDS]
        per_record_f1[rid] = float(np.mean(dims))

    record_macro = np.array([per_record_f1[rid] for rid in rids])
    overall_macro_f1 = float(record_macro.mean())

    # per-dimension headline F1 (single: macro incl Unknown; multi: macro-by-record)
    dim_headline = {}
    for f in SINGLE_FIELDS:
        dim_headline[f] = single_res[f]["macro_f1_incl_unknown"]
    for f in MULTI_FIELDS:
        dim_headline[f] = multi_res[f]["macro_f1"]
    macro_over_dims = float(np.mean([dim_headline[f] for f in ALL_FIELDS]))

    # ---- (C) statistics
    # Wilson interval for each single-label accuracy
    def wilson(k, n, z=1.96):
        if n == 0:
            return (0.0, 0.0)
        phat = k / n
        denom = 1 + z*z/n
        center = (phat + z*z/(2*n)) / denom
        half = (z * math.sqrt(phat*(1-phat)/n + z*z/(4*n*n))) / denom
        return (center - half, center + half)

    wilson_ci = {}
    for f in SINGLE_FIELDS:
        k = single_res[f]["correct"]; n = single_res[f]["n"]
        lo, hi = wilson(k, n)
        wilson_ci[f] = {"acc": k/n if n else 0.0, "lo": lo, "hi": hi, "k": k, "n": n}

    # bootstrap CI for overall macro-F1 (resample records)
    rng = np.random.default_rng(args.seed)
    n = len(record_macro)
    boots = np.array([
        record_macro[rng.integers(0, n, n)].mean() for _ in range(args.bootstrap)
    ])
    boot_mean = float(boots.mean())
    boot_lo, boot_hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    if boot_lo > H1:
        h1_verdict = "SUPPORTED (95% CI entirely above 0.70)"
    elif boot_hi < H1:
        h1_verdict = "NOT SUPPORTED (95% CI entirely below 0.70)"
    else:
        h1_verdict = "INCONCLUSIVE (95% CI straddles 0.70)"

    # one-sample t-test of per-record macro-F1 vs 0.70
    t_stat, p_val = stats.ttest_1samp(record_macro, H1)

    # ---- per-sector breakdown (overall macro-F1 by sector)
    sector_scores = defaultdict(list)
    for rid in rids:
        sector_scores[sector_of(rid, gold)].append(per_record_f1[rid])
    per_sector = {
        s: {"n": len(v), "macro_f1": float(np.mean(v)) if v else None}
        for s, v in sector_scores.items()
    }

    # ----------------------------------------------------------------- #
    # Assemble metrics
    # ----------------------------------------------------------------- #
    metrics = {
        "run_meta": run_meta,
        "h1_threshold": H1,
        "n_scorable": len(rids),
        "n_salvaged_json": n_salvaged,
        "salvaged_ids": salvaged_ids,
        "schema_compliance": schema,
        "single_label": {
            f: {k: v for k, v in single_res[f].items() if k != "pairs"}
            for f in SINGLE_FIELDS
        },
        "multi_label": {
            f: {k: v for k, v in multi_res[f].items() if k != "per_record"}
            for f in MULTI_FIELDS
        },
        "dimension_headline_f1": dim_headline,
        "overall": {
            "macro_f1_per_record_mean": overall_macro_f1,
            "macro_f1_over_dimensions": macro_over_dims,
            "bootstrap_mean": boot_mean,
            "bootstrap_ci95": [boot_lo, boot_hi],
            "h1_verdict": h1_verdict,
            "ttest_t": float(t_stat), "ttest_p": float(p_val),
        },
        "wilson_ci": wilson_ci,
        "per_sector": per_sector,
    }
    json.dump(metrics, open(f"rq1/metrics{suffix}.json", "w"),
              indent=2, ensure_ascii=False)

    # ----------------------------------------------------------------- #
    # errors CSV (single-label dims)
    # ----------------------------------------------------------------- #
    with open(f"rq1/errors{suffix}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", "sector", "dimension", "gold", "pred", "correct", "off_vocab"])
        for f in SINGLE_FIELDS:
            for i, rid in enumerate(rids):
                g, p, off = single_res[f]["pairs"][i]
                w.writerow([rid, sector_of(rid, gold), f, g, p,
                            1 if g == p else 0, 1 if off else 0])

    # ----------------------------------------------------------------- #
    # Markdown report
    # ----------------------------------------------------------------- #
    md = build_report(metrics, single_res, multi_res, run_meta, args.seed)
    open(f"rq1/report{suffix}.md", "w").write(md)
    print(md)


def pct(x):
    return f"{100*x:.1f}%"


def build_report(m, single_res, multi_res, run_meta, seed):
    L = []
    L.append(f"# RQ1 Evaluation Report — seed {seed}\n")
    L.append(f"**Model:** `{run_meta.get('model','?')}` "
             f"(digest `{run_meta.get('model_digest','')[:12]}`), "
             f"Ollama `{run_meta.get('ollama_version','?')}`, "
             f"temperature 0, think=false, seed {run_meta.get('seed','?')}.")
    L.append(f"**Scorable records:** {m['n_scorable']} (gold in_scope==Yes). "
             f"**JSON salvaged:** {m['n_salvaged_json']} record(s) where the model "
             f"emitted a malformed (unquoted) `rationale`; scored fields recovered "
             f"from the raw response, no re-generation.\n")

    ov = m["overall"]
    L.append("## Headline\n")
    L.append(f"- **Overall macro-F1 (mean per-record): {ov['macro_f1_per_record_mean']:.3f}**")
    L.append(f"- Bootstrap mean {ov['bootstrap_mean']:.3f}, "
             f"95% CI [{ov['bootstrap_ci95'][0]:.3f}, {ov['bootstrap_ci95'][1]:.3f}] "
             f"({m['bootstrap'] if 'bootstrap' in m else 1000} resamples)")
    L.append(f"- Macro-F1 averaged over the {len(ALL_FIELDS)} dimensions: "
             f"{ov['macro_f1_over_dimensions']:.3f}")
    L.append(f"- **H1 (F1 ≥ 0.70): {ov['h1_verdict']}**")
    L.append(f"- One-sample t-test of per-record macro-F1 vs 0.70: "
             f"t = {ov['ttest_t']:.3f}, p = {ov['ttest_p']:.4g}\n")

    sc = m["schema_compliance"]
    L.append("## (A) Schema compliance (RQ2 by-product)\n")
    L.append(f"Grammar was NOT enforced (think=false), so this is a real measurement.")
    L.append(f"- Total predicted values: **{sc['total_values']}**")
    L.append(f"- Off-vocabulary values: **{sc['off_vocab']}**")
    L.append(f"- **Schema-violation rate: {pct(sc['violation_rate'])}**\n")
    L.append("| Dimension | Values | Off-vocab | Rate | Top off-vocab examples |")
    L.append("|---|---:|---:|---:|---|")
    for f in ALL_FIELDS:
        d = sc["per_field"][f]
        ex = ", ".join(f"{v}×{c}" for v, c in d["examples"]) if d["examples"] else "—"
        L.append(f"| {f} | {d['total']} | {d['off']} | {pct(d['rate'])} | {ex} |")
    L.append("")

    L.append("## (B) Per-dimension accuracy\n")
    L.append("### Single-label dimensions\n")
    L.append("| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) | micro-F1 |")
    L.append("|---|---:|---:|---:|---:|")
    for f in SINGLE_FIELDS:
        r = single_res[f]
        L.append(f"| {f} | {pct(r['accuracy'])} | {r['macro_f1_incl_unknown']:.3f} | "
                 f"{r['macro_f1_excl_unknown']:.3f} | {r['micro_f1']:.3f} |")
    L.append("")
    L.append("### Multi-label dimensions (set P/R/F1)\n")
    L.append("| Dimension | macro-P | macro-R | macro-F1 | micro-F1 |")
    L.append("|---|---:|---:|---:|---:|")
    for f in MULTI_FIELDS:
        r = multi_res[f]
        L.append(f"| {f} | {r['macro_p']:.3f} | {r['macro_r']:.3f} | "
                 f"{r['macro_f1']:.3f} | {r['micro_f1']:.3f} |")
    L.append("")

    L.append("### Wilson 95% CIs (single-label accuracy)\n")
    L.append("| Dimension | Acc | 95% CI |")
    L.append("|---|---:|---|")
    for f, w in m["wilson_ci"].items():
        L.append(f"| {f} | {pct(w['acc'])} | [{pct(w['lo'])}, {pct(w['hi'])}] |")
    L.append("")

    L.append("## (B) Per-sector breakdown\n")
    L.append("| Sector | n | macro-F1 |")
    L.append("|---|---:|---:|")
    for s in SECTORS:
        if s in m["per_sector"]:
            d = m["per_sector"][s]
            L.append(f"| {s} | {d['n']} | {d['macro_f1']:.3f} |")
    for s, d in m["per_sector"].items():
        if s not in SECTORS:
            L.append(f"| {s} | {d['n']} | {d['macro_f1']:.3f} |")
    L.append("\n> ⚠️ Caveat: telco (n≤3) and education_healthcare (n≤4) cells are "
             "tiny and unstable; treat those numbers as indicative only.\n")

    L.append("## Narrative\n")
    best = max(ALL_FIELDS, key=lambda f: m["dimension_headline_f1"][f])
    worst = min(ALL_FIELDS, key=lambda f: m["dimension_headline_f1"][f])
    L.append(
        f"The overall per-record macro-F1 is "
        f"**{ov['macro_f1_per_record_mean']:.3f}** "
        f"(95% bootstrap CI [{ov['bootstrap_ci95'][0]:.3f}, {ov['bootstrap_ci95'][1]:.3f}]), "
        f"so H1 is **{ov['h1_verdict'].split('(')[0].strip().lower()}**. "
        f"The strongest dimension is `{best}` "
        f"(F1 {m['dimension_headline_f1'][best]:.3f}); the weakest is `{worst}` "
        f"(F1 {m['dimension_headline_f1'][worst]:.3f}). "
        f"The measured schema-violation rate is {pct(sc['violation_rate'])}, "
        f"recorded as an RQ2 by-product since the JSON grammar was deliberately "
        f"not enforced."
    )
    return "\n".join(L)


if __name__ == "__main__":
    main()
