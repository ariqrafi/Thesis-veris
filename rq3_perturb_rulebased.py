#!/usr/bin/env python3
"""RQ3 rule-based perturbation generator for scenarios A3, C1, C2.

Usage:
  python3 rq3_perturb_rulebased.py --scenario A3
  python3 rq3_perturb_rulebased.py --scenario C1_headline
  python3 rq3_perturb_rulebased.py --scenario C1_25pct
  python3 rq3_perturb_rulebased.py --scenario C1_50pct
  python3 rq3_perturb_rulebased.py --scenario C2_actor
  python3 rq3_perturb_rulebased.py --scenario C2_action
  python3 rq3_perturb_rulebased.py --scenario C2_asset
  python3 rq3_perturb_rulebased.py --all   # run all rule-based scenarios

Outputs: rq3/perturbed/<scenario>.jsonl  (same schema as eval_set_100.jsonl,
  with full_content_clean replaced by perturbed text + perturbation metadata)
"""
import argparse, json, re, random, unicodedata, sys
from pathlib import Path
sys.path.insert(0, ".")
import rq3_lib as L

OUT_DIR = Path("rq3/perturbed")

# --------------------------------------------------------------------------- #
# A3 — Noise injection (rule-based, deterministic with seed)
# --------------------------------------------------------------------------- #

# Indonesian OCR/typo substitutions (character level)
_OCR_MAP = {
    'l': '1', 'I': 'l', 'o': '0', 'O': '0',
    'a': '@', 'e': '3', 's': '5', 'g': '9',
}

# Common Indonesian informal abbreviations (expand -> contract for noise)
_ABBREV = {
    'tidak': 'tdk', 'yang': 'yg', 'dengan': 'dgn',
    'untuk': 'utk', 'bahwa': 'bhw', 'sebagai': 'sbg',
    'atau': 'atau', 'kepada': 'kpd', 'karena': 'krn',
    'sudah': 'sdh', 'belum': 'blm', 'juga': 'jg',
    'dalam': 'dlm', 'sehingga': 'shg', 'tersebut': 'tsb',
    'melalui': 'mlui', 'terhadap': 'thdp', 'namun': 'nmn',
}

def _remove_diacritics(text):
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def _typo_word(word, rng):
    """Introduce one character-level perturbation in a word (if len>3)."""
    if len(word) <= 3:
        return word
    choice = rng.integers(0, 3)
    idx = int(rng.integers(1, len(word) - 1))
    w = list(word)
    if choice == 0 and idx < len(w) - 1:
        w[idx], w[idx+1] = w[idx+1], w[idx]   # swap adjacent
    elif choice == 1:
        if w[idx] in _OCR_MAP:
            w[idx] = _OCR_MAP[w[idx]]           # OCR substitution
    else:
        w.pop(idx)                               # delete char
    return ''.join(w)

def perturb_a3(text, noise_rate=0.07, seed=42):
    """Inject noise into ~noise_rate fraction of tokens.
    Returns (perturbed_text, stats_dict)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    # Step 1: diacritic removal (mild, applied to all text)
    text_nd = _remove_diacritics(text)
    # Step 2: tokenise by whitespace-preserving split
    tokens = re.split(r'(\s+)', text_nd)
    words  = [t for t in tokens if t.strip()]
    spaces = [t for t in tokens if not t.strip()]
    n_words = len(words)
    n_target = max(1, int(n_words * noise_rate))
    # sample indices to perturb (alphabetic words only)
    eligible = [i for i, w in enumerate(words) if w.isalpha() and len(w) > 2]
    rng.shuffle(eligible)
    to_perturb = set(eligible[:n_target])
    # Step 3: typo or abbreviation
    perturbed_words = []
    n_abbrev = 0; n_typo = 0
    for i, w in enumerate(words):
        wl = w.lower()
        if i in to_perturb:
            if wl in _ABBREV and rng.random() < 0.5:
                abbr = _ABBREV[wl]
                perturbed_words.append(abbr if w.islower() else abbr.upper())
                n_abbrev += 1
            else:
                perturbed_words.append(_typo_word(w, rng))
                n_typo += 1
        else:
            perturbed_words.append(w)
    # re-interleave with spaces
    out_tokens = []
    si = 0
    for i, t in enumerate(tokens):
        if t.strip():
            wi = [j for j, x in enumerate(words) if x == words[[k for k,x in enumerate(tokens) if x.strip()].index(i)] ][0] if False else None
            out_tokens.append(perturbed_words.pop(0) if perturbed_words else t)
        else:
            out_tokens.append(t)
    result = ''.join(out_tokens)
    stats = {
        "n_words": n_words, "n_target": n_target,
        "n_abbrev": n_abbrev, "n_typo": n_typo,
        "noise_rate_actual": (n_abbrev + n_typo) / n_words if n_words else 0,
    }
    return result, stats

# Simpler, more reliable A3 implementation
def perturb_a3_v2(text, noise_rate=0.07, seed=42):
    """Inject noise: diacritics removed + token-level perturbations."""
    import numpy as np
    rng = np.random.default_rng(seed)
    # Step 1: diacritic removal
    text = _remove_diacritics(text)
    # Step 2: split into word tokens preserving whitespace
    parts = re.split(r'(\s+)', text)
    words   = [p for p in parts if p.strip()]
    n_words = len(words)
    n_perturb = max(1, int(n_words * noise_rate))
    eligible  = [i for i, w in enumerate(words) if len(w) > 2 and w.isalpha()]
    if not eligible:
        return text, {"n_words": n_words, "n_perturb": 0, "noise_rate_actual": 0}
    rng.shuffle(eligible)
    to_perturb = set(eligible[:min(n_perturb, len(eligible))])
    out_words = []
    n_done = 0
    for i, w in enumerate(words):
        if i in to_perturb:
            wl = w.lower()
            if wl in _ABBREV and rng.random() < 0.4:
                abbr = _ABBREV[wl]
                out_words.append(abbr if w[0].islower() else abbr.upper())
            else:
                out_words.append(_typo_word(w, rng))
            n_done += 1
        else:
            out_words.append(w)
    # rebuild preserving original whitespace
    result_parts = []
    wi = 0
    for p in parts:
        if p.strip():
            result_parts.append(out_words[wi]); wi += 1
        else:
            result_parts.append(p)
    result = ''.join(result_parts)
    stats = {
        "n_words": n_words,
        "n_perturb": n_done,
        "noise_rate_actual": n_done / n_words if n_words else 0,
        "diacritics_removed": True,
    }
    return result, stats

# --------------------------------------------------------------------------- #
# C1 — Truncation
# --------------------------------------------------------------------------- #
def _split_sentences(text):
    """Split text into sentences (simple heuristic)."""
    # Split on . ! ? followed by space or newline, or on newlines
    sents = re.split(r'(?<=[.!?])\s+|\n{2,}', text.strip())
    return [s.strip() for s in sents if s.strip()]

def perturb_c1_headline(text):
    sents = _split_sentences(text)
    out = ' '.join(sents[:2]) if len(sents) >= 2 else text[:200]
    return out, {"kept_sentences": min(2, len(sents)), "total_sentences": len(sents),
                 "kept_pct": len(out)/max(1,len(text))}

def perturb_c1_pct(text, pct):
    n = max(100, int(len(text) * pct))
    out = text[:n]
    # trim to last sentence boundary if possible
    last_punct = max(out.rfind('.'), out.rfind('!'), out.rfind('?'), out.rfind('\n'))
    if last_punct > n // 2:
        out = out[:last_punct+1]
    return out, {"kept_chars": len(out), "total_chars": len(text),
                 "kept_pct": len(out)/max(1,len(text))}

# --------------------------------------------------------------------------- #
# C2 — Sentence / field dropout
# --------------------------------------------------------------------------- #

# Keywords by VERIS dimension group (Indonesian + English, case-insensitive)
_ACTOR_KEYWORDS = re.compile(
    r'\b(pelaku|attacker|hacker|peretas|threat\s*actor|penyerang|criminal|'
    r'kelompok|group|gang|tim\s+hacker|tim\s+penyerang|sindikat|aktor\s+ancaman|'
    r'nation.state|state.sponsored|insider|orang\s+dalam|karyawan\s+nakal)\b',
    re.IGNORECASE
)
_ACTION_KEYWORDS = re.compile(
    r'\b(menyerang|meretas|attack|hacked|exploit|phishing|ransomware|'
    r'mengenkripsi|encrypt|leaked|bocor|dijual|sold|dibobol|breach|'
    r'infiltrat|compromise|inject|malware|backdoor|brute.force|credential)\b',
    re.IGNORECASE
)
_ASSET_KEYWORDS = re.compile(
    r'\b(server|database|sistem|system|website|aplikasi|application|'
    r'data\s+pengguna|user\s+data|backup|file|records|credentials|'
    r'informasi|network|jaringan|infrastruktur|cloud|email|workstation)\b',
    re.IGNORECASE
)
_KW_MAP = {"actor": _ACTOR_KEYWORDS, "action": _ACTION_KEYWORDS, "asset": _ASSET_KEYWORDS}

def perturb_c2(text, dimension):
    """Remove sentences containing keywords for `dimension` (actor/action/asset)."""
    kw_re = _KW_MAP[dimension]
    sents = _split_sentences(text)
    kept, dropped = [], []
    for s in sents:
        if kw_re.search(s):
            dropped.append(s)
        else:
            kept.append(s)
    out = ' '.join(kept) if kept else "[No content remaining after dropout]"
    stats = {
        "dimension": dimension,
        "total_sentences": len(sents),
        "dropped_sentences": len(dropped),
        "kept_sentences": len(kept),
        "dropout_rate": len(dropped) / max(1, len(sents)),
    }
    return out, stats

# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
SCENARIO_FUNS = {
    "A3":           lambda t, rid: perturb_a3_v2(t, noise_rate=0.07, seed=42),
    "C1_headline":  lambda t, rid: perturb_c1_headline(t),
    "C1_25pct":     lambda t, rid: perturb_c1_pct(t, 0.25),
    "C1_50pct":     lambda t, rid: perturb_c1_pct(t, 0.50),
    "C2_actor":     lambda t, rid: perturb_c2(t, "actor"),
    "C2_action":    lambda t, rid: perturb_c2(t, "action"),
    "C2_asset":     lambda t, rid: perturb_c2(t, "asset"),
}

ALL_RULE_SCENARIOS = list(SCENARIO_FUNS.keys())


def run_scenario(scenario):
    fun = SCENARIO_FUNS[scenario]
    eval72 = L.load_72_records()
    ex_hashes = L.exemplar_hashes()

    out_path = OUT_DIR / f"{scenario}.jsonl"
    spot_path = Path("rq3/spot_check") / f"{scenario}_spot.jsonl"
    aggregate_stats = []
    n_written = 0

    with open(out_path, "w") as fout, open(spot_path, "w") as fspot:
        for rid, rec in eval72.items():
            orig_text = rec.get("full_content_clean") or rec.get("full_content") or ""
            perturbed_text, stats = fun(orig_text, rid)
            out_rec = dict(rec)
            out_rec["full_content_clean"] = perturbed_text
            out_rec["_perturbation"] = {
                "scenario": scenario,
                "method": "rule_based",
                "original_length": len(orig_text),
                "perturbed_length": len(perturbed_text),
                "stats": stats,
            }
            fout.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
            aggregate_stats.append(stats)
            n_written += 1
            # spot check: first 10 records
            if n_written <= 10:
                fspot.write(json.dumps({
                    "record_id": rid,
                    "scenario": scenario,
                    "original_preview": orig_text[:300],
                    "perturbed_preview": perturbed_text[:300],
                    "stats": stats,
                }, ensure_ascii=False) + "\n")

    # leakage assertion: no exemplar hash in perturbed set
    written_hashes = {r.get("content_hash") for r in eval72.values()}
    overlap = written_hashes & ex_hashes
    assert not overlap, f"LEAKAGE in {scenario}: {overlap}"

    print(f"[{scenario}] wrote {n_written} records -> {out_path}")
    print(f"  leakage_safe=True (overlap={overlap})")
    # Print aggregate stat summary if available
    if aggregate_stats and "noise_rate_actual" in aggregate_stats[0]:
        rates = [s["noise_rate_actual"] for s in aggregate_stats]
        import numpy as np
        print(f"  noise_rate: mean={np.mean(rates):.3f} min={min(rates):.3f} max={max(rates):.3f}")
    if aggregate_stats and "dropout_rate" in aggregate_stats[0]:
        rates = [s["dropout_rate"] for s in aggregate_stats]
        import numpy as np
        print(f"  dropout_rate: mean={np.mean(rates):.3f} min={min(rates):.3f} max={max(rates):.3f}")
    if aggregate_stats and "kept_pct" in aggregate_stats[0]:
        kpts = [s["kept_pct"] for s in aggregate_stats]
        import numpy as np
        print(f"  kept_pct: mean={np.mean(kpts):.3f}")


def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--scenario", choices=ALL_RULE_SCENARIOS)
    grp.add_argument("--all", action="store_true")
    args = ap.parse_args()

    scenarios = ALL_RULE_SCENARIOS if args.all else [args.scenario]
    for sc in scenarios:
        run_scenario(sc)


if __name__ == "__main__":
    main()
