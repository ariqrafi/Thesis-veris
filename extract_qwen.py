#!/usr/bin/env python3
"""RQ1 extractor: call local qwen3.5:35b (Ollama) once per scorable record and
save raw + parsed VERIS A4 predictions.

Key environment decisions (see CLAUDE/thesis notes):
  * think=false  -> avoids ~80s reasoning traces. Side effect: Ollama does NOT
    enforce the `format` JSON-schema grammar, so off-vocabulary values are
    possible. We embed the FULL controlled vocabulary in the prompt, generate
    freely, and validate in Python (score_rq1.py). `format` is still passed as a
    field-name hint.
  * temperature 0 + fixed seed for reproducibility.

Usage:
  python extract_qwen.py --seed 42 [--limit N] [--infile eval_set_100.jsonl]
"""
import argparse, json, re, sys, time, urllib.request, urllib.error

from veris_enums import ENUMS
from veris_fields import SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen3.5:35b"
MAX_CHARS = 16000
RETRIES = 3
GOLD_FILE = "gold_standard.json"

# --------------------------------------------------------------------------- #
# Prompt construction (programmatic, from ENUMS — embeds the full vocabulary)
# --------------------------------------------------------------------------- #
def _vlist(enum_key):
    return ", ".join(ENUMS[enum_key])

def build_system_prompt():
    P = []
    P.append(
        "You are a cybersecurity incident analyst. You classify a single "
        "data-breach report (Indonesian, English, or mixed) into the VERIS A4 "
        "model (Actor, Action, Asset, Attribute). Annotate the MEANING of the "
        "incident, not the surface language."
    )
    P.append(
        "\nUse ONLY these exact strings (copy verbatim, case-sensitive). Do not "
        "invent values, translate them, or use synonyms.\n"
    )

    P.append("== ACTOR ==")
    P.append(f"actor_category (choose ONE): {_vlist('actor.category')}")
    P.append(f"actor_variety (list; if category=External use): {_vlist('actor.external.variety')}")
    P.append(f"actor_variety (if category=Internal use): {_vlist('actor.internal.variety')}")
    P.append(f"actor_variety (if category=Partner use): {_vlist('actor.partner.variety')}")
    P.append(f"actor_motive (list): {_vlist('actor.motive')}")

    P.append("\n== ACTION ==")
    P.append(f"action_category (choose ONE): {_vlist('action.category')}")
    for cat in ["malware", "hacking", "social", "misuse", "physical", "error", "environmental"]:
        vk = f"action.{cat}.variety"
        P.append(f"action_variety (if category={cat.capitalize()} use): {_vlist(vk)}")
        ck = f"action.{cat}.vector"
        if ck in ENUMS:
            P.append(f"action_vector (if category={cat.capitalize()} use): {_vlist(ck)}")

    P.append("\n== ASSET ==")
    P.append(f"asset_category (choose ONE): {_vlist('asset.category')}")
    asset_map = {
        "Server": "asset.server.variety", "User Device": "asset.user_device.variety",
        "Media": "asset.media.variety", "Network": "asset.network.variety",
        "Person": "asset.person.variety", "Kiosk/Terminal": "asset.kiosk_terminal.variety",
        "Embedded": "asset.embedded.variety",
    }
    for cat, vk in asset_map.items():
        P.append(f"asset_variety (if category={cat} use): {_vlist(vk)}")

    P.append("\n== ATTRIBUTE ==")
    P.append(f"attr_conf_present (choose ONE): {_vlist('yes_no_unknown')}")
    P.append(f"attr_conf_disclosure (choose ONE): {_vlist('attribute.confidentiality.data_disclosure')}")
    P.append(f"attr_conf_data_variety (list): {_vlist('attribute.confidentiality.data.variety')}")
    P.append(f"attr_integrity_present (choose ONE): {_vlist('yes_no_unknown')}")
    P.append(f"attr_integrity_variety (list): {_vlist('attribute.integrity.variety')}")
    P.append(f"attr_avail_present (choose ONE): {_vlist('yes_no_unknown')}")
    P.append(f"attr_avail_variety (list): {_vlist('attribute.availability.variety')}")

    P.append("\n== MAPPING RULES ==")
    P.append("- peretasan / diretas / hacked -> action_category=Hacking.")
    P.append("- ransomware / tebusan -> action_category=Malware, action_variety includes Ransomware.")
    P.append("- phishing -> action_category=Social, action_variety includes Phishing.")
    P.append("- salah konfigurasi / database terbuka / misconfigured / open database -> action_category=Error, action_variety includes Misconfiguration.")
    P.append("- 'data dijual di dark web' / data sold with NO method stated -> action_variety=[\"Unknown\"].")
    P.append("- The variety/vector values MUST belong to the chosen category (e.g. if action_category=Hacking, use only the Hacking variety/vector lists above).")
    P.append("- Use \"Unknown\" when a dimension applies but the report does not state it. Never speculate beyond the text.")

    P.append("\n== OUTPUT ==")
    P.append(
        "Output ONLY a single JSON object, no markdown, no prose, with EXACTLY "
        "these keys: actor_category (string), actor_variety (list of strings), "
        "actor_motive (list), action_category (string), action_variety (list), "
        "action_vector (list), asset_category (string), asset_variety (list), "
        "attr_conf_present (string), attr_conf_disclosure (string), "
        "attr_conf_data_variety (list), attr_integrity_present (string), "
        "attr_integrity_variety (list), attr_avail_present (string), "
        "attr_avail_variety (list), rationale (string: 1-2 sentences citing "
        "evidence from the report)."
    )
    return "\n".join(P)


def build_user_prompt(rec, text_field):
    text = (rec.get(text_field) or "")[:MAX_CHARS]
    meta = (
        f"sector: {rec.get('sector','')}\n"
        f"language: {rec.get('language','')}\n"
        f"title: {rec.get('title','')}\n"
        f"url: {rec.get('url','')}\n"
    )
    return f"REPORT METADATA:\n{meta}\nREPORT TEXT:\n{text}"


# --------------------------------------------------------------------------- #
# JSON schema hint (field names; arrays NOT enum-constrained by design)
# --------------------------------------------------------------------------- #
def build_format_schema():
    props = {}
    for f, ek in SINGLE_FIELDS.items():
        props[f] = {"type": "string", "enum": list(ENUMS[ek])}
    for f in MULTI_FIELDS:
        props[f] = {"type": "array", "items": {"type": "string"}}
    props["rationale"] = {"type": "string"}
    return {"type": "object", "properties": props, "required": ALL_FIELDS}


# --------------------------------------------------------------------------- #
# Ollama call + JSON extraction
# --------------------------------------------------------------------------- #
def first_json_block(s):
    """Extract the first balanced {...} object from a string."""
    start = s.find("{")
    if start < 0:
        return None
    depth = 0; in_str = False; esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
    return None


def salvage_json(raw):
    """Parse the model's JSON, tolerating a common failure mode where the LAST
    field (`rationale`, which is NOT scored) is emitted unquoted/malformed and
    breaks the whole object. All scored fields precede `rationale`, so on a hard
    parse failure we drop everything from `"rationale"` onward and parse the rest.
    Returns (parsed_dict_or_None, salvaged_bool)."""
    block = first_json_block(raw)
    if block is not None:
        try:
            return json.loads(block), False
        except json.JSONDecodeError:
            pass
    # Salvage: cut at the rationale key, close the object before it.
    idx = raw.find('"rationale"')
    if idx != -1:
        start = raw.find("{")
        if 0 <= start < idx:
            head = raw[start:idx].rstrip().rstrip(",").rstrip()
            cand = head + "}"
            try:
                return json.loads(cand), True
            except json.JSONDecodeError:
                pass
    return None, False


def call_ollama(system_prompt, user_prompt, schema, seed):
    payload = {
        "model": MODEL,
        "think": False,
        "stream": False,
        "options": {"temperature": 0, "seed": seed},
        "format": schema,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL + "/api/chat", data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())


def get_model_digest():
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=30) as r:
            tags = json.loads(r.read().decode())
        for m in tags.get("models", []):
            if m.get("name") == MODEL:
                return m.get("digest", "")
    except Exception:
        pass
    return ""


def get_ollama_version():
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/version", timeout=30) as r:
            return json.loads(r.read().decode()).get("version", "")
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
def load_scorable(infile):
    gold = json.load(open(GOLD_FILE))
    if "annotations" in gold and isinstance(gold.get("annotations"), dict):
        gold = gold["annotations"]
    scorable_ids = [rid for rid, v in gold.items() if v.get("in_scope") == "Yes"]

    eval_recs = {}
    text_field = "full_content_clean"
    with open(infile) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            eval_recs[r["record_id"]] = r
    # pick text field with fallback
    sample = eval_recs[scorable_ids[0]]
    if not sample.get("full_content_clean"):
        text_field = "full_content"
    return [eval_recs[i] for i in scorable_ids if i in eval_recs], text_field


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--infile", default="data/eval_set_100.jsonl")
    args = ap.parse_args()

    system_prompt = build_system_prompt()
    schema = build_format_schema()
    records, text_field = load_scorable(args.infile)
    if args.limit:
        records = records[: args.limit]

    out_path = f"rq1/predictions_seed{args.seed}.json"
    results = {
        "_run_meta": {
            "model": MODEL,
            "model_digest": get_model_digest(),
            "ollama_version": get_ollama_version(),
            "seed": args.seed,
            "temperature": 0,
            "think": False,
            "max_chars": MAX_CHARS,
            "text_field": text_field,
            "n_records": len(records),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    }
    json.dump(results, open(out_path, "w"), indent=2, ensure_ascii=False)

    print(f"[meta] model={MODEL} digest={results['_run_meta']['model_digest'][:12]} "
          f"ollama={results['_run_meta']['ollama_version']} seed={args.seed} "
          f"text_field={text_field} n={len(records)}")

    for idx, rec in enumerate(records, 1):
        rid = rec["record_id"]
        user_prompt = build_user_prompt(rec, text_field)
        parsed, raw, latency, err, salvaged = None, "", 0.0, None, False
        for attempt in range(1, RETRIES + 1):
            t0 = time.time()
            try:
                resp = call_ollama(system_prompt, user_prompt, schema, args.seed)
                latency = time.time() - t0
                raw = resp.get("message", {}).get("content", "")
                parsed, salvaged = salvage_json(raw)
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
