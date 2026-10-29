"""Incident-level overlap between the six v3 few-shot exemplars and the 72
in-scope evaluation records, and whether it inflates the pipeline's score.

The exemplars are disjoint from the evaluation set by content hash, but several
evaluation articles report the same incident as an exemplar. The overlap set
below was identified by reading titles and text; it is deliberately strict and
excludes records that only mention an exemplar's incident in passing.
"""
import collections, json, os, random, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gold = json.load(open(os.path.join(ROOT, "data", "gold_standard.json")))
v3 = json.load(open(os.path.join(ROOT, "rq1", "predictions_v3_fewshot_seed42.json")))
ids = sorted(k for k in v3 if not k.startswith("_"))

SINGLE = ["actor_category", "action_category", "asset_category", "attr_conf_present",
          "attr_integrity_present", "attr_avail_present", "attr_conf_disclosure"]
MULTI = ["actor_variety", "actor_motive", "action_variety", "action_vector", "asset_variety",
         "attr_conf_data_variety", "attr_integrity_variety", "attr_avail_variety"]

OVERLAP = {
    "FS-01 PDNS 2 ransomware (2024)": ["GS-020", "GS-022", "GS-026", "GS-078"],
    "FS-02 Tokopedia (2020)": ["GS-014", "GS-015", "GS-096"],
    "FS-04 Bank Indonesia": ["GS-054", "GS-055"],
    "FS-06 BRI Life (2021)": ["GS-011", "GS-016", "GS-040", "GS-048", "GS-049"],
    "FS-07 Telkomsel / Denny Siregar (2020)": ["GS-027", "GS-043", "GS-088", "GS-090"],
}
ov = {r for rs in OVERLAP.values() for r in rs}


def s(d, p, g):
    if d in SINGLE:
        return 1.0 if p == g else 0.0
    a, b = set(p or []), set(g or [])
    if not a and not b:
        return 1.0
    return 2 * len(a & b) / (len(a) + len(b))


def rec(pred, i):
    return st.mean(s(d, pred[i].get(d), gold[i][d]) for d in SINGLE + MULTI)


mode = {d: collections.Counter(gold[i][d] for i in ids).most_common(1)[0][0] for d in SINGLE}
mode.update({d: list(collections.Counter(tuple(sorted(gold[i][d])) for i in ids).most_common(1)[0][0])
             for d in MULTI})
b0 = {i: mode for i in ids}

A = [i for i in ids if i in ov]
B = [i for i in ids if i not in ov]
print(f"overlap records: {len(A)}   non-overlap records: {len(B)}")
for name, pred in [("B0 constant", b0), ("v3 framework", v3)]:
    print(f"{name:14s} overlap {st.mean(rec(pred, i) for i in A):.4f}"
          f"   non-overlap {st.mean(rec(pred, i) for i in B):.4f}")

diff = [rec(b0, i) - rec(v3, i) for i in B]
random.seed(0)
boot = sorted(st.mean(random.choices(diff, k=len(diff))) for _ in range(5000))
print(f"B0 minus v3 on non-overlap: {st.mean(diff):.4f}  95% CI [{boot[125]:.4f}, {boot[4874]:.4f}]")
