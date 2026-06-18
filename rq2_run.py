#!/usr/bin/env python3
"""RQ2 Tasks 2 & 6 — repeated inference with the v3 few-shot extractor.

Reuses extract_qwen_fewshot / extract_qwen_v2 verbatim for prompt, schema,
exemplars and JSON salvage so the inference path is byte-identical to the RQ1 v3
main run. Only adds: a temperature knob, a per-run seed, and per-run output files.

Each (temperature, run) pair writes runs/<tag>/run_<i>.jsonl :
  line 1            {"_run_meta": {...}}   run_id, timestamp, digest, temperature,
                                           seed, ollama_version, num_ctx, ...
  lines 2..N+1      one record per line: {"record_id":..., <15 A4 fields>,
                                          "_raw", "_latency_s", "_prompt_eval_count",
                                          "_salvaged"?, "_error"?}

Seed strategy (documented for the thesis):
  * temp 0  -> the same seed (42) on every run, matching the v3 config exactly;
              this is the determinism test (Task 3). Greedy decoding => expected
              identical, but we run it 5x to confirm empirically.
  * temp>0  -> a distinct seed per run, so the sampler actually explores the
              output distribution and run-to-run F1 variance (Task 6) is
              meaningful (a fixed seed would make Ollama deterministic even at
              temp>0, giving a degenerate variance of 0).

Usage:
  python rq2_run.py --temp 0   --tag temp0   --seeds 42,42,42,42,42 --infile repro_subset_50.jsonl
  python rq2_run.py --temp 0.3 --tag temp0.3 --seeds 42,43,44,45,46 --infile repro_subset_50.jsonl
  python rq2_run.py --temp 0.7 --tag temp0.7 --seeds 42,43,44,45,46 --infile repro_subset_50.jsonl
"""
import argparse, json, os, time, urllib.request, urllib.error

import extract_qwen_v2 as v2
import extract_qwen_fewshot as fs
from veris_fields import ALL_FIELDS

MODEL = v2.MODEL
RETRIES = v2.RETRIES


def call_ollama(messages, schema, temperature, seed, num_ctx):
    options = {"temperature": temperature, "seed": seed}
    if num_ctx:
        options["num_ctx"] = num_ctx
    payload = {
        "model": MODEL,
        "think": False,
        "stream": False,
        "options": options,
        "format": schema,
        "messages": messages,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        v2.OLLAMA_URL + "/api/chat", data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())


def run_once(records, text_field, system_prompt, schema, exemplars,
             temperature, seed, num_ctx, run_id, tag, outpath, digest, oversion):
    meta = {
        "run_id": run_id,
        "tag": tag,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": MODEL,
        "model_digest": digest,
        "ollama_version": oversion,
        "prompt_version": fs.PROMPT_VERSION,
        "temperature": temperature,
        "seed": seed,
        "think": False,
        "num_ctx": num_ctx,
        "max_chars": v2.MAX_CHARS,
        "text_field": text_field,
        "n_records": len(records),
        "n_exemplars": len(exemplars),
        "exemplar_ids": [c for c, _, _ in exemplars],
    }
    lines = [json.dumps({"_run_meta": meta}, ensure_ascii=False)]
    t_run = time.time()
    for idx, rec in enumerate(records, 1):
        rid = rec["record_id"]
        user_prompt = v2.build_user_prompt(rec, text_field)
        messages = fs.build_messages(system_prompt, exemplars, user_prompt)
        parsed, raw, latency, err, salvaged, peval = None, "", 0.0, None, False, None
        for attempt in range(1, RETRIES + 1):
            t0 = time.time()
            try:
                resp = call_ollama(messages, schema, temperature, seed, num_ctx)
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
                if attempt < RETRIES:
                    time.sleep(2)

        entry = {"record_id": rid}
        if parsed is not None:
            entry.update(parsed)
        entry["_raw"] = raw
        entry["_latency_s"] = round(latency, 2)
        entry["_prompt_eval_count"] = peval
        if salvaged:
            entry["_salvaged"] = True
        if err:
            entry["_error"] = err
        lines.append(json.dumps(entry, ensure_ascii=False))

    with open(outpath, "w") as f:
        f.write("\n".join(lines) + "\n")
    dt = time.time() - t_run
    print(f"[{tag} run {run_id}] seed={seed} temp={temperature} "
          f"-> {outpath} ({len(records)} recs, {dt:.0f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temp", type=float, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--seeds", required=True, help="comma-separated, one per run")
    ap.add_argument("--infile", default="data/repro_subset_50.jsonl")
    ap.add_argument("--num-ctx", type=int, default=32768)
    ap.add_argument("--outroot", default="rq2/runs")
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    outdir = os.path.join(args.outroot, args.tag)
    os.makedirs(outdir, exist_ok=True)

    system_prompt = v2.build_system_prompt()
    schema = v2.build_format_schema()
    exemplars = fs.load_exemplars()
    records, text_field = v2.load_scorable(args.infile)
    digest = v2.get_model_digest()
    oversion = v2.get_ollama_version()

    print(f"[meta] model={MODEL} digest={digest[:12]} ollama={oversion} "
          f"prompt={fs.PROMPT_VERSION} text_field={text_field} n={len(records)} "
          f"fewshot={len(exemplars)} temp={args.temp} tag={args.tag} seeds={seeds}")
    assert len(records) == 50, f"expected 50 records, got {len(records)}"

    for i, seed in enumerate(seeds, 1):
        outpath = os.path.join(outdir, f"run_{i}.jsonl")
        run_once(records, text_field, system_prompt, schema, exemplars,
                 args.temp, seed, args.num_ctx, i, args.tag, outpath, digest, oversion)
    print(f"[done] {args.tag}: {len(seeds)} runs in {outdir}")


if __name__ == "__main__":
    main()
