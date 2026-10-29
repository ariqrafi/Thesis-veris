#!/usr/bin/env python3
"""Post-process the full-corpus VERIS predictions:
  1. validate every scored field against the VERIS controlled vocabulary,
  2. report schema-violation rate + field completeness (same spirit as RQ2),
  3. report the A4 label distribution over the corpus,
  4. export a flat CSV dataset (one row per record) + a JSON summary.

Usage:
  python summarize_corpus.py --pred rq1/predictions_corpus_v3_seed42.json \
      --corpus data/corpus_canonical.jsonl
"""
import argparse, csv, json
from collections import Counter

from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS, allowed_values

META = "_run_meta"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="rq1/predictions_corpus_v3_seed42.json")
    ap.add_argument("--corpus", default="data/corpus_canonical.jsonl")
    ap.add_argument("--out-csv", default="rq1/corpus_veris_labeled.csv")
    ap.add_argument("--out-json", default="rq1/corpus_veris_summary.json")
    args = ap.parse_args()

    pred = json.load(open(args.pred))
    pred.pop(META, None)

    # corpus metadata by record_id (for the CSV context columns)
    meta = {}
    for ln in open(args.corpus):
        ln = ln.strip()
        if ln:
            r = json.loads(ln)
            meta[r["record_id"]] = r

    allowed = {f: allowed_values(f) for f in ALL_FIELDS}

    n = 0
    n_error = 0
    n_violation_records = 0
    filled_cells = total_cells = 0
    offvocab_per_field = Counter()
    dist = {f: Counter() for f in ("actor_category", "action_category", "asset_category",
                                   "attr_conf_present", "attr_integrity_present", "attr_avail_present")}

    rows = []
    for rid, rec in pred.items():
        n += 1
        if rec.get("_error"):
            n_error += 1
        row = {"record_id": rid,
               "title": (meta.get(rid, {}).get("title", "")),
               "sector": meta.get(rid, {}).get("sector", ""),
               "language": meta.get(rid, {}).get("language", ""),
               "url": meta.get(rid, {}).get("url", "")}
        rec_has_violation = False
        for f in ALL_FIELDS:
            val = rec.get(f)
            if f in SINGLE_FIELDS:
                v = val if isinstance(val, str) else ""
                row[f] = v
                total_cells += 1
                # thesis definition: field complete if present with a valid-type,
                # non-empty value ("Unknown" counts; missing/null/"" does not).
                if isinstance(val, str) and val.strip():
                    filled_cells += 1
                if v and v not in allowed[f]:
                    offvocab_per_field[f] += 1
                    rec_has_violation = True
                elif not v:
                    # empty single field = should have been "Unknown"
                    rec_has_violation = True
            else:  # multi
                vals = val if isinstance(val, list) else []
                row[f] = "; ".join(str(x) for x in vals)
                total_cells += 1
                # thesis definition: an empty array [] is a VALID populated
                # response (attribute not affected) -> counts as complete;
                # only a missing key / null / wrong type is incomplete.
                if isinstance(val, list):
                    filled_cells += 1
                bad = [x for x in vals if x not in allowed[f]]
                if bad:
                    offvocab_per_field[f] += len(bad)
                    rec_has_violation = True
            if f in dist and isinstance(val, str):
                dist[f][val or "(empty)"] += 1
        if rec_has_violation:
            n_violation_records += 1
        rows.append(row)

    # write CSV
    fieldnames = ["record_id", "title", "sector", "language", "url"] + ALL_FIELDS
    with open(args.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    summary = {
        "n_records": n,
        "n_error_records": n_error,
        "schema_violation_rate_pct": round(100 * n_violation_records / n, 2) if n else 0,
        "n_violation_records": n_violation_records,
        "field_completeness_pct": round(100 * filled_cells / total_cells, 2) if total_cells else 0,
        "offvocab_per_field": dict(offvocab_per_field.most_common()),
        "distribution": {k: dict(v.most_common()) for k, v in dist.items()},
    }
    json.dump(summary, open(args.out_json, "w"), indent=2, ensure_ascii=False)

    print(f"records          : {n}  (errors: {n_error})")
    print(f"schema-violation : {summary['schema_violation_rate_pct']}%  "
          f"({n_violation_records}/{n} records)")
    print(f"field completeness: {summary['field_completeness_pct']}%")
    print("\nActor category :", dict(dist["actor_category"].most_common()))
    print("Action category:", dict(dist["action_category"].most_common()))
    print("Asset category :", dict(dist["asset_category"].most_common()))
    print(f"\n[out] {args.out_csv}\n[out] {args.out_json}")


if __name__ == "__main__":
    main()
