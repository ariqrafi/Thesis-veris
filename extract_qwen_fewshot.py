#!/usr/bin/env python3
"""RQ1 v3 extractor: few-shot variant of extract_qwen_v2.

Identical model/options/system-prompt/schema/parsing as v2, but inserts K human-
annotated exemplars (leakage-safe, from OUTSIDE the eval-100) as alternating
user/assistant turns BEFORE the real query. Each exemplar's assistant turn is the
gold annotation rendered as a single JSON object with exactly the 15 scored keys
(same shape the model must produce) — so the model sees worked examples of the
CATEGORY-vs-VARIETY split and the "Unknown when unstated" convention.

Exemplars: fewshot_exemplars.json (use==true only); text pulled from
fewshot_candidates.json by cand_id. Both are leakage-checked vs eval-100.

Usage:
  python extract_qwen_fewshot.py --seed 42 [--limit N]
"""
import argparse, json, time, urllib.request, urllib.error

from veris_enums import ENUMS
from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS
import extract_qwen_v2 as v2

OLLAMA_URL = v2.OLLAMA_URL
MODEL = v2.MODEL
PROMPT_VERSION = "v3_fewshot"
MAX_CHARS = v2.MAX_CHARS
RETRIES = v2.RETRIES

EXEMPLAR_FILE = "data/fewshot_exemplars.json"
CANDIDATE_FILE = "data/fewshot_candidates.json"


# --------------------------------------------------------------------------- #
# Few-shot exemplar assembly
# --------------------------------------------------------------------------- #
def load_exemplars():
    """Return [(cand_id, user_prompt, assistant_json_str)] for use==true entries,
    in file order. Validates values are in-vocab and not leaked into eval-100."""
    doc = json.load(open(EXEMPLAR_FILE))
    cands = json.load(open(CANDIDATE_FILE))

    # leakage guard
    eval_hashes = set()
    with open("data/eval_set_100.jsonl") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                eval_hashes.add(json.loads(ln).get("content_hash"))

    out = []
    for e in doc["exemplars"]:
        if not e.get("use"):
            continue
        cid = e["cand_id"]
        if e.get("content_hash") in eval_hashes:
            raise SystemExit(f"LEAKAGE: exemplar {cid} content_hash in eval-100")
        cand = cands.get(cid)
        if cand is None:
            raise SystemExit(f"exemplar {cid} not found in {CANDIDATE_FILE}")

        # exemplar 'record' shaped like an eval record so v2.build_user_prompt works
        rec = {
            "full_content_clean": cand.get("text", ""),
            "sector": cand.get("sector", ""),
            "language": cand.get("language", ""),
            "title": cand.get("title", ""),
            "url": cand.get("url", ""),
        }
        user_prompt = v2.build_user_prompt(rec, "full_content_clean")

        ann = e["annotation"]
        # render assistant answer with EXACTLY the 15 scored keys, in canonical order
        ordered = {f: ann[f] for f in ALL_FIELDS}
        assistant = json.dumps(ordered, ensure_ascii=False)
        out.append((cid, user_prompt, assistant))
    return out


def build_messages(system_prompt, exemplars, user_prompt):
    msgs = [{"role": "system", "content": system_prompt}]
    for _cid, ex_user, ex_assistant in exemplars:
        msgs.append({"role": "user", "content": ex_user})
        msgs.append({"role": "assistant", "content": ex_assistant})
    msgs.append({"role": "user", "content": user_prompt})
    return msgs


def call_ollama(messages, schema, seed, num_ctx=32768):
    options = {"temperature": 0, "seed": seed}
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
        OLLAMA_URL + "/api/chat", data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--infile", default="data/eval_set_100.jsonl")
    ap.add_argument("--num-ctx", type=int, default=32768)
    args = ap.parse_args()

    system_prompt = v2.build_system_prompt()
    schema = v2.build_format_schema()
    exemplars = load_exemplars()
    records, text_field = v2.load_scorable(args.infile)
    if args.limit:
        records = records[: args.limit]

    out_path = f"rq1/predictions_{PROMPT_VERSION}_seed{args.seed}.json"
    results = {
        "_run_meta": {
            "model": MODEL,
            "model_digest": v2.get_model_digest(),
            "ollama_version": v2.get_ollama_version(),
            "prompt_version": PROMPT_VERSION,
            "seed": args.seed,
            "temperature": 0,
            "think": False,
            "max_chars": MAX_CHARS,
            "num_ctx": args.num_ctx,
            "text_field": text_field,
            "n_records": len(records),
            "n_exemplars": len(exemplars),
            "exemplar_ids": [c for c, _, _ in exemplars],
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    }
    json.dump(results, open(out_path, "w"), indent=2, ensure_ascii=False)

    print(f"[meta] model={MODEL} digest={results['_run_meta']['model_digest'][:12]} "
          f"prompt={PROMPT_VERSION} ollama={results['_run_meta']['ollama_version']} "
          f"seed={args.seed} text_field={text_field} n={len(records)} "
          f"fewshot={len(exemplars)}({','.join(c for c,_,_ in exemplars)})")

    for idx, rec in enumerate(records, 1):
        rid = rec["record_id"]
        user_prompt = v2.build_user_prompt(rec, text_field)
        messages = build_messages(system_prompt, exemplars, user_prompt)
        parsed, raw, latency, err, salvaged, peval = None, "", 0.0, None, False, None
        for attempt in range(1, RETRIES + 1):
            t0 = time.time()
            try:
                resp = call_ollama(messages, schema, args.seed, args.num_ctx)
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

        entry = {} if parsed is None else dict(parsed)
        entry["_raw"] = raw
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
        print(f"[{idx:>3}/{len(records)}] {rid} -> action={ac} actor={acr} "
              f"({latency:.1f}s){flag}")

    print(f"[done] wrote {out_path}")


if __name__ == "__main__":
    main()
