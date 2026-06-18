#!/usr/bin/env python3
"""RQ3 extractor wrapper — runs v3 few-shot extractor on perturbed JSONL inputs.

Identical prompt/config to RQ1 v3 (extract_qwen_fewshot.py):
  model=qwen3.5:35b, digest=3460ffeede54, temp=0, seed=42, think=false,
  num_ctx=32768, 6 frozen exemplars. The ONLY difference is the input text
  (perturbed) and the output file path.

Usage:
  python3 rq3_extract_scenario.py --scenario A3
  python3 rq3_extract_scenario.py --scenario C1_25pct
  python3 rq3_extract_scenario.py --scenario A1 --resume
"""
import argparse, json, time, urllib.error, sys
from pathlib import Path
sys.path.insert(0, ".")

import extract_qwen_v2  as v2
import extract_qwen_fewshot as fs
import rq3_lib as L

PERTURB_DIR = Path("rq3/perturbed")
OUT_DIR     = Path("rq3/predictions")
SEED        = 42
NUM_CTX     = 32768
RETRIES     = 3

ALL_SCENARIOS = [
    "A1","A2","A3","A4",
    "C1_headline","C1_25pct","C1_50pct",
    "C2_actor","C2_action","C2_asset",
]


def load_perturbed_as_records(scenario):
    """Return list of records (dicts) from rq3/perturbed/<scenario>.jsonl,
    for the 72 in-scope IDs only."""
    path = PERTURB_DIR / f"{scenario}.jsonl"
    gold = L.load_gold()
    recs = []
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                r = json.loads(ln)
                if r["record_id"] in gold:
                    recs.append(r)
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=ALL_SCENARIOS, required=True)
    ap.add_argument("--seed",    type=int, default=SEED)
    ap.add_argument("--num-ctx", type=int, default=NUM_CTX)
    ap.add_argument("--resume",  action="store_true")
    args = ap.parse_args()

    scenario = args.scenario
    out_path = OUT_DIR / f"{scenario}_seed{args.seed}.json"

    # Load perturbed records
    records  = load_perturbed_as_records(scenario)
    n_total  = len(records)
    print(f"[{scenario}] {n_total} perturbed records")

    # Leakage check
    ex_hashes   = L.exemplar_hashes()
    eval_hashes = {r.get("content_hash","") for r in records}
    overlap     = eval_hashes & ex_hashes
    assert not overlap, f"LEAKAGE: {overlap}"
    print(f"[{scenario}] leakage_safe=True")

    # Prompt components (same as RQ1 v3)
    system_prompt = v2.build_system_prompt()
    schema_fmt    = v2.build_format_schema()
    exemplars     = fs.load_exemplars()
    print(f"[{scenario}] exemplars={len(exemplars)} "
          f"({','.join(c for c,_,_ in exemplars)})")

    # Resume
    results  = {}
    done_ids = set()
    if args.resume and out_path.exists():
        results  = json.load(open(out_path))
        done_ids = {k for k in results if not k.startswith("_")}
        print(f"[{scenario}] resuming: {len(done_ids)} done")
    else:
        results = {
            "_run_meta": {
                "model":          v2.MODEL,
                "model_digest":   v2.get_model_digest(),
                "ollama_version": v2.get_ollama_version(),
                "prompt_version": "v3_fewshot",
                "scenario":       scenario,
                "rq3":            True,
                "seed":           args.seed,
                "temperature":    0,
                "think":          False,
                "max_chars":      v2.MAX_CHARS,
                "num_ctx":        args.num_ctx,
                "n_records":      n_total,
                "n_exemplars":    len(exemplars),
                "exemplar_ids":   [c for c,_,_ in exemplars],
                "started_at":     time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        }

    n_done  = len(done_ids)
    t_start = time.time()

    for idx, rec in enumerate(records, 1):
        rid = rec["record_id"]
        if rid in done_ids:
            continue

        # Build user prompt exactly like v2 (uses full_content_clean from perturbed rec)
        user_prompt = v2.build_user_prompt(rec, "full_content_clean")
        messages    = fs.build_messages(system_prompt, exemplars, user_prompt)

        parsed, raw_txt, latency, err, salvaged, peval = None, "", 0.0, None, False, None
        for attempt in range(1, RETRIES + 1):
            t0 = time.time()
            try:
                resp    = fs.call_ollama(messages, schema_fmt, args.seed, args.num_ctx)
                latency = time.time() - t0
                raw_txt = resp.get("message", {}).get("content", "")
                peval   = resp.get("prompt_eval_count")
                parsed, salvaged = v2.salvage_json(raw_txt)
                if parsed is None:
                    raise ValueError("no JSON object in response")
                err = None
                break
            except (urllib.error.URLError, ValueError, json.JSONDecodeError, KeyError) as e:
                err     = f"{type(e).__name__}: {e}"
                latency = time.time() - t0
                if attempt < RETRIES:
                    time.sleep(2)

        entry = {} if parsed is None else dict(parsed)
        entry["_raw"]                = raw_txt
        entry["_latency_s"]          = round(latency, 2)
        entry["_prompt_eval_count"]  = peval
        if salvaged: entry["_salvaged"] = True
        if err:      entry["_error"]    = err
        results[rid] = entry

        # Incremental save
        json.dump(results, open(out_path, "w"), indent=2, ensure_ascii=False)

        n_done += 1
        eta = (time.time() - t_start) / n_done * (n_total - n_done) if n_done else 0
        flag = " ERROR" if err else ""
        print(f"  [{n_done}/{n_total}] {rid} -> "
              f"action={entry.get('action_category','?')} "
              f"actor={entry.get('actor_category','?')} "
              f"({latency:.1f}s) ETA={eta/60:.1f}min{flag}")

    results["_run_meta"]["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(results, open(out_path, "w"), indent=2, ensure_ascii=False)
    print(f"\n[{scenario}] DONE -> {out_path} ({n_done} records)")


if __name__ == "__main__":
    main()
