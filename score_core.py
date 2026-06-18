#!/usr/bin/env python3
"""Core-A4 (category-level) secondary headline metric.

Restricts scoring to the six single-label A4 *category* dimensions and reports
macro-F1 averaged across them, computed twice (including / excluding the
"Unknown" class), with a bootstrap CI and an H1 (>=0.70) verdict. Reusable for
any predictions file (v1, v2, ...) via CLI args; performs NO model calls.
"""
import argparse, json
import numpy as np
from scipy import stats

from score_rq1 import load_gold, single_label_metrics, norm_single

H1 = 0.70
CORE_DIMS = [
    "actor_category", "action_category", "asset_category",
    "attr_conf_present", "attr_integrity_present", "attr_avail_present",
]


def macro_f1_from_pairs(pairs, exclude_unknown=False):
    """pairs: list of (gold, pred). Macro-F1 over gold classes."""
    gold_classes = sorted(set(g for g, _ in pairs))
    f1s = []
    for c in gold_classes:
        if exclude_unknown and c == "Unknown":
            continue
        tp = sum(1 for g, p in pairs if g == c and p == c)
        fp = sum(1 for g, p in pairs if g != c and p == c)
        fn = sum(1 for g, p in pairs if g == c and p != c)
        pr = tp / (tp + fp) if (tp + fp) else 0.0
        rc = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * pr * rc / (pr + rc) if (pr + rc) else 0.0)
    return float(np.mean(f1s)) if f1s else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--preds", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None, help="report .md to append a section to")
    ap.add_argument("--tag", default="", help="label for the run, e.g. v2")
    ap.add_argument("--bootstrap", type=int, default=1000)
    args = ap.parse_args()

    preds_file = args.preds or f"rq1/predictions_seed{args.seed}.json"
    out_file = args.out or f"rq1/metrics_core_seed{args.seed}.json"

    preds_all = json.load(open(preds_file))
    run_meta = preds_all.get("_run_meta", {})
    preds = {k: v for k, v in preds_all.items() if not k.startswith("_")}
    gold = load_gold()
    rids = list(gold.keys())

    # per-dimension single-label metrics + aligned (gold,pred) pairs
    per_dim = {}
    pairs_by_dim = {}  # dim -> list aligned to rids: (gold, pred)
    for f in CORE_DIMS:
        r = single_label_metrics(f, preds, gold)
        per_dim[f] = {
            "accuracy": r["accuracy"],
            "macro_f1_incl_unknown": r["macro_f1_incl_unknown"],
            "macro_f1_excl_unknown": r["macro_f1_excl_unknown"],
            "per_class": r["per_class"],
        }
        pairs_by_dim[f] = [(g, p) for (g, p, _off) in r["pairs"]]

    core_incl = float(np.mean([per_dim[f]["macro_f1_incl_unknown"] for f in CORE_DIMS]))
    core_excl = float(np.mean([per_dim[f]["macro_f1_excl_unknown"] for f in CORE_DIMS]))

    # per-record macro-F1 (single-label per-record F1 = 1 if correct else 0), mean over 6 dims
    n = len(rids)
    rec_macro = np.array([
        np.mean([1.0 if pairs_by_dim[f][i][0] == pairs_by_dim[f][i][1] else 0.0
                 for f in CORE_DIMS])
        for i in range(n)
    ])

    # bootstrap over records: recompute core class-macro-F1 (incl & excl) each resample
    rng = np.random.default_rng(args.seed)
    boot_incl, boot_excl = [], []
    for _ in range(args.bootstrap):
        idx = rng.integers(0, n, n)
        bi = np.mean([macro_f1_from_pairs([pairs_by_dim[f][j] for j in idx], False)
                      for f in CORE_DIMS])
        be = np.mean([macro_f1_from_pairs([pairs_by_dim[f][j] for j in idx], True)
                      for f in CORE_DIMS])
        boot_incl.append(bi); boot_excl.append(be)
    boot_incl = np.array(boot_incl); boot_excl = np.array(boot_excl)
    ci_incl = [float(np.percentile(boot_incl, 2.5)), float(np.percentile(boot_incl, 97.5))]
    ci_excl = [float(np.percentile(boot_excl, 2.5)), float(np.percentile(boot_excl, 97.5))]

    def verdict(ci):
        if ci[0] > H1:
            return "SUPPORTED (95% CI entirely above 0.70)"
        if ci[1] < H1:
            return "NOT SUPPORTED (95% CI entirely below 0.70)"
        return "INCONCLUSIVE (95% CI straddles 0.70)"

    t_stat, p_val = stats.ttest_1samp(rec_macro, H1)

    metrics = {
        "run_meta": run_meta,
        "tag": args.tag,
        "h1_threshold": H1,
        "core_dims": CORE_DIMS,
        "n_scorable": n,
        "per_dimension": per_dim,
        "core_macro_f1_incl_unknown": core_incl,
        "core_macro_f1_excl_unknown": core_excl,
        "bootstrap": {
            "n_resamples": args.bootstrap,
            "incl_unknown": {"mean": float(boot_incl.mean()), "ci95": ci_incl,
                             "h1_verdict": verdict(ci_incl)},
            "excl_unknown": {"mean": float(boot_excl.mean()), "ci95": ci_excl,
                             "h1_verdict": verdict(ci_excl)},
        },
        "per_record_macro_f1": {
            "mean": float(rec_macro.mean()),
            "ttest_t": float(t_stat), "ttest_p": float(p_val),
        },
    }
    json.dump(metrics, open(out_file, "w"), indent=2, ensure_ascii=False)

    # console
    label = f" [{args.tag}]" if args.tag else ""
    print(f"=== Core-A4 (category-level){label} — {preds_file} ===")
    print(f"{'dimension':<24}{'acc':>8}{'F1 incl Unk':>14}{'F1 excl Unk':>14}")
    for f in CORE_DIMS:
        d = per_dim[f]
        print(f"{f:<24}{d['accuracy']*100:>7.1f}%{d['macro_f1_incl_unknown']:>14.3f}"
              f"{d['macro_f1_excl_unknown']:>14.3f}")
    print("-" * 60)
    print(f"{'CORE-A4 macro-F1':<24}{'':>8}{core_incl:>14.3f}{core_excl:>14.3f}")
    print(f"\nBootstrap 95% CI ({args.bootstrap} resamples):")
    print(f"  incl Unknown: {core_incl:.3f}  CI [{ci_incl[0]:.3f}, {ci_incl[1]:.3f}]  -> {verdict(ci_incl)}")
    print(f"  excl Unknown: {core_excl:.3f}  CI [{ci_excl[0]:.3f}, {ci_excl[1]:.3f}]  -> {verdict(ci_excl)}")
    print(f"\nPer-record macro-F1 mean = {rec_macro.mean():.3f}; "
          f"t-test vs 0.70: t = {t_stat:.3f}, p = {p_val:.4g}")

    # append section to report
    if args.report:
        sec = build_section(metrics, args.tag)
        with open(args.report, "a") as fh:
            fh.write("\n\n" + sec + "\n")
        print(f"\n[appended Core-A4 section to {args.report}]")

    return metrics


def build_section(m, tag):
    label = f" — {tag}" if tag else ""
    L = [f"## Core-A4 (category-level){label}\n"]
    L.append("Secondary headline restricted to the six single-label A4 *category* "
             "dimensions (actor/action/asset category + the three attribute-present flags).\n")
    L.append("| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) |")
    L.append("|---|---:|---:|---:|")
    for f in CORE_DIMS:
        d = m["per_dimension"][f]
        L.append(f"| {f} | {d['accuracy']*100:.1f}% | "
                 f"{d['macro_f1_incl_unknown']:.3f} | {d['macro_f1_excl_unknown']:.3f} |")
    bi = m["bootstrap"]["incl_unknown"]; be = m["bootstrap"]["excl_unknown"]
    L.append(f"| **CORE-A4 macro-F1** | | **{m['core_macro_f1_incl_unknown']:.3f}** | "
             f"**{m['core_macro_f1_excl_unknown']:.3f}** |")
    L.append("")
    L.append(f"- **Incl. Unknown:** {m['core_macro_f1_incl_unknown']:.3f}, "
             f"95% CI [{bi['ci95'][0]:.3f}, {bi['ci95'][1]:.3f}] → **H1 {bi['h1_verdict']}**")
    L.append(f"- **Excl. Unknown:** {m['core_macro_f1_excl_unknown']:.3f}, "
             f"95% CI [{be['ci95'][0]:.3f}, {be['ci95'][1]:.3f}] → **H1 {be['h1_verdict']}**")
    pr = m["per_record_macro_f1"]
    L.append(f"- Per-record macro-F1 mean {pr['mean']:.3f}; one-sample t-test vs 0.70: "
             f"t = {pr['ttest_t']:.3f}, p = {pr['ttest_p']:.4g}")
    return "\n".join(L)


if __name__ == "__main__":
    main()
