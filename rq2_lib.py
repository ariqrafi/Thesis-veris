#!/usr/bin/env python3
"""RQ2 shared library: load runs, validate schema compliance, canonicalise the
scored A4 label, and score macro-F1 vs gold.

The validation module is the single source of truth (same vocab as veris_fields,
same gold as score_rq1). An off-vocabulary value is a VIOLATION — never remapped.
"""
import json, os
from collections import Counter

import numpy as np

import extract_qwen_v2 as v2
import score_rq1 as sc
from veris_fields import (SINGLE_FIELDS, MULTI_FIELDS, ALL_FIELDS, allowed_values)

GOLD_FILE = "data/gold_standard.json"
SUBSET_FILE = "data/repro_subset_50.jsonl"

ALLOWED = {f: allowed_values(f) for f in ALL_FIELDS}
NULLISH = (None,)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_run(path):
    """Return (meta, {record_id: entry}). entry keeps the parsed A4 fields plus
    the underscore bookkeeping keys (_raw, _error, _salvaged, ...)."""
    meta, recs = {}, {}
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            obj = json.loads(ln)
            if "_run_meta" in obj:
                meta = obj["_run_meta"]
                continue
            recs[obj["record_id"]] = obj
    return meta, recs


def list_runs(tagdir):
    """runs/<tag>/run_*.jsonl in numeric run order."""
    if not os.path.isdir(tagdir):
        return []
    files = [f for f in os.listdir(tagdir) if f.startswith("run_") and f.endswith(".jsonl")]
    files.sort(key=lambda f: int(f[len("run_"):-len(".jsonl")]))
    return [os.path.join(tagdir, f) for f in files]


def load_gold_subset():
    """Gold restricted to the 50 ids actually present in repro_subset_50."""
    gold = sc.load_gold()
    sub_ids = []
    with open(SUBSET_FILE) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                sub_ids.append(json.loads(ln)["record_id"])
    return {rid: gold[rid] for rid in sub_ids if rid in gold}, sub_ids


def subset_meta():
    """record_id -> {sector, language, source, url} from the subset file."""
    meta = {}
    with open(SUBSET_FILE) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            r = json.loads(ln)
            meta[r["record_id"]] = {
                "sector": r.get("sector"),
                "language": r.get("language"),
                "source": r.get("source"),
                "url": r.get("url"),
            }
    return meta


# --------------------------------------------------------------------------- #
# Validation (Task 4) — the source of truth for schema compliance
# --------------------------------------------------------------------------- #
def parsed_fields(entry):
    return {k: v for k, v in entry.items()
            if not k.startswith("_") and k != "record_id"}


def syntax_ok(entry):
    """True iff the raw model output strictly parses as JSON without salvage."""
    raw = entry.get("_raw", "")
    block = v2.first_json_block(raw)
    if block is None:
        return False
    try:
        json.loads(block)
        return True
    except json.JSONDecodeError:
        return False


def validate_record(entry):
    """Return dict of failure flags for one prediction record.
      causes: set of {'syntax','missing','vocabulary','null'}
    A record is a violation iff causes is non-empty."""
    causes = set()
    detail = {"missing": [], "off_vocab": [], "null": []}

    # syntax: did the raw output parse strictly? (salvage / hard failure => syntax)
    if not syntax_ok(entry):
        causes.add("syntax")
    # belt-and-braces: trust the extractor's own flags too
    if entry.get("_salvaged"):
        causes.add("syntax")
    if entry.get("_error"):
        causes.add("syntax")

    p = parsed_fields(entry)

    for f in ALL_FIELDS:
        if f not in p:
            causes.add("missing")
            detail["missing"].append(f)
            continue
        v = p[f]
        if f in SINGLE_FIELDS:
            if v is None:
                causes.add("null"); detail["null"].append(f); continue
            if isinstance(v, list):
                # wrong container type for a single-label field
                causes.add("null"); detail["null"].append(f + "(list)")
                # still vocab-check its element(s)
                for x in v:
                    if str(x) not in ALLOWED[f]:
                        causes.add("vocabulary"); detail["off_vocab"].append((f, str(x)))
                continue
            sv = str(v)
            if sv == "":
                causes.add("null"); detail["null"].append(f + "(empty)"); continue
            if sv not in ALLOWED[f]:
                causes.add("vocabulary"); detail["off_vocab"].append((f, sv))
        else:  # MULTI
            if v is None:
                causes.add("null"); detail["null"].append(f); continue
            if not isinstance(v, list):
                causes.add("null"); detail["null"].append(f + "(non-list)")
                if str(v) not in ALLOWED[f]:
                    causes.add("vocabulary"); detail["off_vocab"].append((f, str(v)))
                continue
            for x in v:
                if str(x) not in ALLOWED[f]:
                    causes.add("vocabulary"); detail["off_vocab"].append((f, str(x)))

    return {"causes": causes, "violation": bool(causes), "detail": detail}


def value_cells(entry):
    """(#value cells, #in-vocab cells, #present-required-fields) for completeness
    & conformance. A single field contributes 1 value; a multi field contributes
    one value per list element (an empty multi list contributes 0 value cells but
    is a present field)."""
    p = parsed_fields(entry)
    total_vals = 0
    in_vocab = 0
    present_fields = 0
    for f in ALL_FIELDS:
        if f not in p or p[f] is None:
            continue
        present_fields += 1
        v = p[f]
        if f in SINGLE_FIELDS:
            vals = v if isinstance(v, list) else [v]
        else:
            vals = v if isinstance(v, list) else [v]
        for x in vals:
            sx = str(x)
            if sx == "":
                continue
            total_vals += 1
            if sx in ALLOWED[f]:
                in_vocab += 1
    return total_vals, in_vocab, present_fields


# --------------------------------------------------------------------------- #
# Canonical scored A4 label (Tasks 3, 5)
# --------------------------------------------------------------------------- #
def canon_single(v):
    return sc.norm_single(v)


def canon_multi(v):
    return tuple(sorted(sc.norm_multi(v)))


def record_label(entry):
    """Per-dimension canonical value: single -> str, multi -> sorted tuple."""
    p = parsed_fields(entry)
    lab = {}
    for f in SINGLE_FIELDS:
        lab[f] = canon_single(p.get(f))
    for f in MULTI_FIELDS:
        lab[f] = canon_multi(p.get(f))
    return lab


def label_key(lab):
    """Hashable, comparable canonical key for the full 15-field A4 label."""
    return json.dumps({f: (list(lab[f]) if isinstance(lab[f], tuple) else lab[f])
                       for f in ALL_FIELDS}, sort_keys=True, ensure_ascii=False)


def dim_category(lab, f):
    """Single categorical token for dimension f (for Fleiss)."""
    v = lab[f]
    if isinstance(v, tuple):
        return "|".join(v) if v else "<empty>"
    return v if v != "" else "<missing>"


# --------------------------------------------------------------------------- #
# Scoring vs gold (Task 6) — reuse score_rq1's exact per-record macro-F1
# --------------------------------------------------------------------------- #
def per_record_macro_f1(preds, gold):
    """Mean over the 15 dimensions per record (single: exact match; multi: set-F1),
    matching score_rq1's headline. Returns {rid: f1} over gold keys."""
    single_res = {f: sc.single_label_metrics(f, preds, gold) for f in SINGLE_FIELDS}
    multi_res = {f: sc.multi_label_metrics(f, preds, gold) for f in MULTI_FIELDS}
    rids = list(gold.keys())
    out = {}
    for i, rid in enumerate(rids):
        dims = []
        for f in SINGLE_FIELDS:
            g, pr, _ = single_res[f]["pairs"][i]
            dims.append(1.0 if g == pr else 0.0)
        for f in MULTI_FIELDS:
            dims.append(multi_res[f]["per_record"][rid])
        out[rid] = float(np.mean(dims))
    return out


def run_macro_f1(preds, gold):
    prf = per_record_macro_f1(preds, gold)
    return float(np.mean(list(prf.values()))) if prf else 0.0
