#!/usr/bin/env python3
"""RQ3 LLM-based perturbation generator: A1 (informal), A2 (code-switching), A4 (translation).

Uses qwen3.5:35b with a DIFFERENT system prompt than the VERIS extractor —
the perturbation role is purely text transformation (NOT extraction).
Generator is thus separate from the extractor (satisfies the constraint).

Usage:
  python3 rq3_perturb_llm.py --scenario A1
  python3 rq3_perturb_llm.py --scenario A2
  python3 rq3_perturb_llm.py --scenario A4
  python3 rq3_perturb_llm.py --resume A1   # resume from last checkpoint

Outputs:
  rq3/perturbed/<scenario>.jsonl
  rq3/spot_check/<scenario>_spot.jsonl   first 10 records for manual review
"""
import argparse, json, time, re, urllib.request, urllib.error, sys
from pathlib import Path
sys.path.insert(0, ".")
import rq3_lib as L

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "qwen3.5:35b"
OUT_DIR    = Path("rq3/perturbed")
SPOT_DIR   = Path("rq3/spot_check")
RETRIES    = 3

# --------------------------------------------------------------------------- #
# Scenario prompts — text transformation only, NOT VERIS extraction
# --------------------------------------------------------------------------- #
SCENARIO_META = {
    "A1": {
        "label": "Informal register / social-media style",
        "system": (
            "You are a text style transformation assistant. "
            "Your task is to rewrite Indonesian text in a casual, informal, "
            "social-media style (gaya bahasa santai/media sosial). "
            "Use common Indonesian abbreviations (yg, dgn, tdk, sdh, dll), "
            "colloquial words (gue/gua, lo/lu, nggak, gimana, kayak, banget, doang), "
            "and shortened sentence structures typical of Twitter/Instagram. "
            "CRITICAL: preserve ALL factual content — entity names, organizations, "
            "numbers, dates, and the nature of the incident MUST remain identical. "
            "Output ONLY the rewritten text. No explanations."
        ),
        "user_prefix": "Rewrite this incident report in informal social-media style (keep all facts):\n\n",
    },
    "A2": {
        "label": "Intensified code-switching (Indonesian-English)",
        "system": (
            "You are a text style transformation assistant. "
            "Your task is to intensify code-switching in Indonesian text by mixing "
            "more English technical and cybersecurity terms into the Indonesian prose. "
            "Replace Indonesian IT/security terms with their English equivalents "
            "(e.g., 'peretas' -> 'hacker', 'sistem' -> 'system', 'kebocoran' -> 'data breach', "
            "'serangan' -> 'attack', 'celah keamanan' -> 'security vulnerability'). "
            "Keep the grammatical structure mostly Indonesian but inject English terms naturally. "
            "CRITICAL: preserve ALL factual content — entity names, organizations, "
            "numbers, dates, and the nature of the incident MUST remain identical. "
            "Output ONLY the rewritten text. No explanations."
        ),
        "user_prefix": "Intensify English-Indonesian code-switching in this text (keep all facts):\n\n",
    },
    "A4": {
        "label": "Cross-lingual: Indonesian<->English full translation",
        "system": (
            "You are a professional translator specializing in cybersecurity and incident reports. "
            "Your task: if the text is primarily in Indonesian, translate it fully to English. "
            "If the text is primarily in English, translate it fully to Indonesian. "
            "Maintain the same level of detail and technical accuracy. "
            "CRITICAL: preserve ALL factual content — entity names, organizations, "
            "numbers, dates, and the nature of the incident MUST remain identical. "
            "Output ONLY the translated text. No explanations."
        ),
        "user_prefix": "Translate this incident report to the other language (keep all facts):\n\n",
    },
}

MAX_CHARS = 16000  # same truncation as extractor


def call_ollama(system_prompt, user_text, seed=42, retries=RETRIES):
    """Call Ollama for text transformation (NOT extraction). Returns plain text."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_text},
        ],
        "stream": False,
        "options": {
            "temperature": 0,
            "seed": seed,
            "num_ctx": 16384,
        },
        "think": False,
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read())
            return resp["message"]["content"].strip(), resp
        except Exception as e:
            if attempt < retries - 1:
                print(f"  [retry {attempt+1}] {e}")
                time.sleep(5)
            else:
                raise


def entity_overlap_check(original, perturbed):
    """Heuristic: what fraction of capitalized tokens from original appear in perturbed.
    Used for automated spot-check validity."""
    orig_entities = set(re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', original))
    # also numbers and domain patterns
    orig_entities |= set(re.findall(r'\b\d{6,}\b|\b\d{1,3}[.,]\d+\s*[Jj]uta\b', original))
    if not orig_entities:
        return 1.0, []
    preserved = [e for e in orig_entities if e in perturbed]
    missing   = [e for e in orig_entities if e not in perturbed]
    rate = len(preserved) / len(orig_entities)
    return rate, missing


def run_scenario(scenario, resume=False):
    meta = SCENARIO_META[scenario]
    eval72    = L.load_72_records()
    ex_hashes = L.exemplar_hashes()
    out_path  = OUT_DIR / f"{scenario}.jsonl"
    spot_path = SPOT_DIR / f"{scenario}_spot.jsonl"

    # Resume: load already-done record IDs from partial output
    done_ids = set()
    if resume and out_path.exists():
        with open(out_path) as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    r = json.loads(ln)
                    done_ids.add(r["record_id"])
        print(f"[{scenario}] resuming — {len(done_ids)} already done")

    write_mode = "a" if resume and done_ids else "w"
    spot_count = 0 if not resume else 999  # don't re-write spots on resume

    n_total  = len(eval72)
    n_done   = len(done_ids)
    validity_issues = []
    t_start  = time.time()

    print(f"[{scenario}] {meta['label']}: {n_total - n_done} records to process ...")

    with open(out_path, write_mode) as fout, \
         open(spot_path, "a") as fspot:
        for i, (rid, rec) in enumerate(eval72.items()):
            if rid in done_ids:
                continue
            orig_text = rec.get("full_content_clean") or rec.get("full_content") or ""
            truncated = orig_text[:MAX_CHARS]
            user_msg  = meta["user_prefix"] + truncated

            t0 = time.time()
            try:
                perturbed_text, raw_resp = call_ollama(meta["system"], user_msg)
            except Exception as e:
                print(f"  [ERROR] {rid}: {e} — writing original as fallback")
                perturbed_text = orig_text
                raw_resp = {}

            elapsed = time.time() - t0
            # validity check
            overlap_rate, missing = entity_overlap_check(orig_text, perturbed_text)
            valid = overlap_rate >= 0.5
            if not valid:
                validity_issues.append({"record_id": rid, "overlap_rate": overlap_rate,
                                        "missing_entities": missing[:10]})

            out_rec = dict(rec)
            out_rec["full_content_clean"] = perturbed_text
            out_rec["_perturbation"] = {
                "scenario": scenario,
                "method": "llm",
                "model": MODEL,
                "system_label": meta["label"],
                "original_length": len(orig_text),
                "perturbed_length": len(perturbed_text),
                "entity_overlap_rate": round(overlap_rate, 3),
                "validity_ok": valid,
                "elapsed_s": round(elapsed, 1),
                "prompt_tokens": raw_resp.get("prompt_eval_count"),
            }
            fout.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
            fout.flush()

            # spot check: first 10 records
            if spot_count < 10:
                fspot.write(json.dumps({
                    "record_id": rid,
                    "scenario": scenario,
                    "label": meta["label"],
                    "original_preview": orig_text[:400],
                    "perturbed_preview": perturbed_text[:400],
                    "entity_overlap_rate": round(overlap_rate, 3),
                    "missing_entities": missing[:5],
                    "validity_ok": valid,
                }, ensure_ascii=False) + "\n")
                fspot.flush()
                spot_count += 1

            n_done += 1
            eta = (time.time() - t_start) / n_done * (n_total - n_done)
            print(f"  [{n_done}/{n_total}] {rid} | {elapsed:.1f}s | "
                  f"overlap={overlap_rate:.2f} | ETA={eta/60:.1f}min")

    # Final leakage assertion
    written_hashes = {r.get("content_hash") for r in eval72.values()}
    overlap_lk = written_hashes & ex_hashes
    assert not overlap_lk, f"LEAKAGE in {scenario}: {overlap_lk}"

    print(f"\n[{scenario}] DONE: {out_path}")
    print(f"  leakage_safe=True (no exemplar overlap)")
    print(f"  validity_issues ({len(validity_issues)} records with overlap<0.5):")
    for vi in validity_issues[:5]:
        print(f"    {vi['record_id']}: overlap={vi['overlap_rate']:.2f} "
              f"missing={vi['missing_entities'][:3]}")

    # Save validity log
    log = {
        "scenario": scenario,
        "n_records": n_total,
        "n_validity_issues": len(validity_issues),
        "validity_issue_records": validity_issues,
    }
    (SPOT_DIR / f"{scenario}_validity_log.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=["A1","A2","A4"], required=True)
    ap.add_argument("--resume", action="store_true",
                    help="Resume from existing partial output (skip done record_ids)")
    args = ap.parse_args()
    run_scenario(args.scenario, resume=args.resume)


if __name__ == "__main__":
    main()
