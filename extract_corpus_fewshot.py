#!/usr/bin/env python3
"""Label the FULL corpus (not just the 72 in-scope eval records) with the exact
same schema-constrained few-shot (v3) framework used for RQ1.

It reuses everything from extract_qwen_v2 / extract_qwen_fewshot unchanged
(system prompt, VERIS schema, the 6 leakage-safe exemplars, call_ollama, JSON
salvage, temp=0/seed=42/think=false/num_ctx=32768). The ONLY difference vs
extract_qwen_fewshot.py is the loader: instead of v2.load_scorable() (which
filters to the gold-standard in_scope==Yes IDs), we iterate over EVERY record in
--infile. Each record must carry a "record_id".

Usage:
  python extract_corpus_fewshot.py --infile data/corpus_canonical.jsonl --seed 42
  python extract_corpus_fewshot.py --infile data/corpus_canonical.jsonl --limit 2   # smoke test
"""
import argparse, json, time, urllib.error

import extract_qwen_v2 as v2
import extract_qwen_fewshot as fs


def load_all(infile):
    """Read every record; pick text field with fallback (clean -> raw)."""
    records = []
    with open(infile) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if not records:
        raise SystemExit(f"no records in {infile}")
    text_field = "full_content_clean" if records[0].get("full_content_clean") else "full_content"
    return records, text_field


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="data/corpus_canonical.jsonl")
    ap.add_argument("--outfile", default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--num-ctx", type=int, default=32768)
    args = ap.parse_args()

    system_prompt = v2.build_system_prompt()
    schema = v2.build_format_schema()
    exemplars = fs.load_exemplars()
    records, text_field = load_all(args.infile)
    if args.limit:
        records = records[: args.limit]

    out_path = args.outfile or f"rq1/predictions_corpus_v3_seed{args.seed}.json"
    results = {
        "_run_meta": {
            "model": v2.MODEL,
            "model_digest": v2.get_model_digest(),
            "ollama_version": v2.get_ollama_version(),
            "prompt_version": "v3_fewshot",
            "seed": args.seed,
            "temperature": 0,
            "think": False,
            "max_chars": v2.MAX_CHARS,
            "num_ctx": args.num_ctx,
            "text_field": text_field,
            "infile": args.infile,
            "n_records": len(records),
            "n_exemplars": len(exemplars),
            "exemplar_ids": [c for c, _, _ in exemplars],
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    }
    json.dump(results, open(out_path, "w"), indent=2, ensure_ascii=False)

    print(f"[meta] model={v2.MODEL} digest={results['_run_meta']['model_digest'][:12]} "
          f"prompt=v3_fewshot seed={args.seed} text_field={text_field} "
          f"n={len(records)} fewshot={len(exemplars)}")

    for idx, rec in enumerate(records, 1):
        rid = rec["record_id"]
        user_prompt = v2.build_user_prompt(rec, text_field)
        messages = fs.build_messages(system_prompt, exemplars, user_prompt)
        parsed, raw, latency, err, salvaged, peval = None, "", 0.0, None, False, None
        for attempt in range(1, v2.RETRIES + 1):
            t0 = time.time()
            try:
                resp = fs.call_ollama(messages, schema, args.seed, args.num_ctx)
                latency = time.time() - t0
                raw = resp.get("message", {}).get("content", "")
                peval = resp.get("prompt_eval_count")
                parsed, salvaged = v2.salvage_json(raw)
                if parsed is None:
                    raise ValueError("no JSON object in response")
                err = None
                break
            except (urllib.error.URLError, ValueError, json.JSONDecodeError, KeyError) as e:
                err = f"{type(e).__name__}: {e}"
                latency = time.time() - t0
                if attempt < v2.RETRIES:
                    time.sleep(2)

        entry = {} if parsed is None else dict(parsed)
        entry["_latency_s"] = round(latency, 2)
        entry["_prompt_eval_count"] = peval
        if salvaged:
            entry["_salvaged"] = True
        if err:
            entry["_error"] = err
        results[rid] = entry
        json.dump(results, open(out_path, "w"), indent=2, ensure_ascii=False)

        ac = entry.get("action_category", "?")
        acr = entry.get("actor_category", "?")
        flag = " ERROR" if err else ""
        print(f"[{idx:>3}/{len(records)}] {rid} -> action={ac} actor={acr} ({latency:.1f}s){flag}")

    print(f"[done] wrote {out_path}")


if __name__ == "__main__":
    main()
