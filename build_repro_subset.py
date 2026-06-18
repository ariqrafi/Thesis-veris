#!/usr/bin/env python3
"""RQ2 Task 1 — build the leakage-safe reproducibility subset (n=50).

Stratified by `sector` over the 72 in_scope==Yes gold records, proportional
allocation by the largest-remainder (Hamilton) method, with a fixed seed for the
within-stratum draw. Verifies that no selected record shares a content_hash with
any of the 6 few-shot exemplars (leakage guard); if any did, it is dropped and
replaced from the remaining pool of that stratum (then any stratum) before the
allocation is finalised.

Outputs:
  repro_subset_50.jsonl   one full eval record per line + explicit sector,
                          language, source columns.
  repro_subset_leakage_check.json   the audit log (allocation, final hashes,
                          overlap result).

Stdlib only.
"""
import argparse, json, hashlib
from collections import Counter, defaultdict

GOLD_FILE = "data/gold_standard.json"
EVAL_FILE = "data/eval_set_100.jsonl"
EXEMPLAR_FILE = "data/fewshot_exemplars.json"
N = 50
SEED = 20260615


def load_gold():
    g = json.load(open(GOLD_FILE))
    if "annotations" in g and isinstance(g.get("annotations"), dict):
        g = g["annotations"]
    return {rid: v for rid, v in g.items() if v.get("in_scope") == "Yes"}


def load_eval():
    recs = {}
    with open(EVAL_FILE) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                r = json.loads(ln)
                recs[r["record_id"]] = r
    return recs


def exemplar_hashes():
    doc = json.load(open(EXEMPLAR_FILE))
    return {e.get("content_hash") for e in doc["exemplars"] if e.get("use")}


def largest_remainder(counts, n_total, target):
    """Hamilton apportionment: dict stratum->pop -> dict stratum->quota summing to target."""
    quotas = {s: target * c / n_total for s, c in counts.items()}
    floors = {s: int(q) for s, q in quotas.items()}
    used = sum(floors.values())
    remaining = target - used
    # distribute remaining seats to largest fractional remainders (ties: larger pop, then name)
    order = sorted(counts, key=lambda s: (-(quotas[s] - floors[s]), -counts[s], s))
    alloc = dict(floors)
    for s in order[:remaining]:
        alloc[s] += 1
    # never allocate more than a stratum has
    for s in alloc:
        if alloc[s] > counts[s]:
            alloc[s] = counts[s]
    return alloc, quotas


def deterministic_shuffle(ids, seed):
    """Seeded, reproducible ordering independent of Python's hash randomisation:
    sort by sha256(seed||id)."""
    return sorted(ids, key=lambda i: hashlib.sha256(f"{seed}:{i}".encode()).hexdigest())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n", type=int, default=N)
    args = ap.parse_args()

    gold = load_gold()
    eval_recs = load_eval()
    ex_hashes = exemplar_hashes()

    ids = list(gold.keys())
    sector = {rid: (gold[rid].get("_meta", {}).get("sector") or "unknown") for rid in ids}
    chash = {rid: eval_recs[rid].get("content_hash") for rid in ids}

    counts = Counter(sector.values())
    alloc, quotas = largest_remainder(counts, len(ids), args.n)

    # group ids by stratum, deterministically ordered
    by_sector = defaultdict(list)
    for rid in ids:
        by_sector[sector[rid]].append(rid)
    for s in by_sector:
        by_sector[s] = deterministic_shuffle(by_sector[s], args.seed)

    # select per stratum, skipping any leaked content_hash; record replacements
    selected = []
    leakage_hits = []
    per_sector_selected = {}
    for s, k in alloc.items():
        pool = by_sector[s]
        picked = []
        for rid in pool:
            if len(picked) >= k:
                break
            if chash[rid] in ex_hashes:
                leakage_hits.append({"record_id": rid, "sector": s,
                                     "content_hash": chash[rid]})
                continue  # skip leaked, take next from pool (replacement)
            picked.append(rid)
        per_sector_selected[s] = picked
        selected.extend(picked)

    # if any stratum came up short (leakage exhausted its pool), backfill from any
    # remaining non-leaked, not-yet-selected record
    if len(selected) < args.n:
        chosen = set(selected)
        spare = [rid for rid in deterministic_shuffle(ids, args.seed)
                 if rid not in chosen and chash[rid] not in ex_hashes]
        for rid in spare:
            if len(selected) >= args.n:
                break
            selected.append(rid)
            per_sector_selected[sector[rid]].append(rid)

    # final leakage assertion
    final_hashes = {rid: chash[rid] for rid in selected}
    overlap = sorted(set(final_hashes.values()) & ex_hashes)
    assert not overlap, f"LEAKAGE in final subset: {overlap}"
    assert len(selected) == args.n, f"got {len(selected)} != {args.n}"

    # write subset (full eval record + explicit columns), ordered by gold id order
    sel_set = set(selected)
    ordered = [rid for rid in ids if rid in sel_set]
    with open("data/repro_subset_50.jsonl", "w") as f:
        for rid in ordered:
            r = dict(eval_recs[rid])
            r["sector"] = sector[rid]
            r["language"] = gold[rid].get("_meta", {}).get("language") or r.get("language")
            r["source"] = (gold[rid].get("_meta", {}).get("source")
                           or r.get("source_type"))
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    log = {
        "task": "RQ2-T1 reproducibility subset",
        "seed": args.seed,
        "n_target": args.n,
        "n_selected": len(selected),
        "pool_in_scope": len(ids),
        "sector_population": dict(counts),
        "sector_quota_exact": {s: round(q, 4) for s, q in quotas.items()},
        "sector_allocation": {s: alloc[s] for s in alloc},
        "sector_selected_counts": {s: len(v) for s, v in per_sector_selected.items()},
        "exemplar_content_hashes": sorted(ex_hashes),
        "leakage_overlap_with_exemplars": overlap,
        "leakage_hits_skipped": leakage_hits,
        "leakage_safe": not overlap,
        "selected_ids": ordered,
        "selected_content_hashes": {rid: final_hashes[rid] for rid in ordered},
    }
    json.dump(log, open("data/repro_subset_leakage_check.json", "w"),
              indent=2, ensure_ascii=False)

    print(f"[T1] population by sector: {dict(counts)}")
    print(f"[T1] exact quotas: {log['sector_quota_exact']}")
    print(f"[T1] allocation (largest-remainder): {log['sector_allocation']} "
          f"sum={sum(alloc.values())}")
    print(f"[T1] selected per sector: {log['sector_selected_counts']}")
    print(f"[T1] leakage hits skipped: {len(leakage_hits)}; "
          f"final overlap with 6 exemplars: {overlap} -> leakage_safe={not overlap}")
    print(f"[T1] wrote repro_subset_50.jsonl ({len(ordered)} records) "
          f"+ repro_subset_leakage_check.json")


if __name__ == "__main__":
    main()
