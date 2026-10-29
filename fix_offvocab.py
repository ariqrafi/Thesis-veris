#!/usr/bin/env python3
"""Method B: deterministic normalization of off-vocabulary values by RELOCATION.

Both known off-vocab values are actually valid VERIS terms that landed in the
wrong field, so we MOVE them to the field where they are valid (preserving the
information) instead of dropping. The original prediction file is never modified;
a new *_fixed.json is written, plus a changelog of every edit.

FIXES: (field, value) -> ("move", target_field)
  ("action_variety", "Carelessness")     -> action_vector    (valid in action.error.vector)
  ("attr_integrity_variety","Obscuration")-> attr_avail_variety (valid in availability.variety)

Usage:
  python fix_offvocab.py --pred rq1/predictions_corpus_v3_seed42.json
"""
import argparse, json

from veris_fields import MULTI_FIELDS, allowed_values

FIXES = {
    ("action_variety", "Carelessness"): ("move", "action_vector"),
    ("attr_integrity_variety", "Obscuration"): ("move", "attr_avail_variety"),
}

META = "_run_meta"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="rq1/predictions_corpus_v3_seed42.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or args.pred.replace(".json", "_fixed.json")

    pred = json.load(open(args.pred))
    allowed = {}  # cache target-field vocab
    changelog = []

    for rid, rec in pred.items():
        if rid == META or not isinstance(rec, dict):
            continue
        for (field, value), (op, target) in FIXES.items():
            vals = rec.get(field)
            if not isinstance(vals, list) or value not in vals:
                continue
            if op != "move":
                continue
            # validate target vocab
            allowed.setdefault(target, allowed_values(target))
            if value not in allowed[target]:
                raise SystemExit(f"{rid}: '{value}' not valid in target field {target}")
            # remove from source
            rec[field] = [x for x in vals if x != value]
            # add to target (dedup, target must be a multi-label list field)
            if target not in MULTI_FIELDS:
                raise SystemExit(f"target {target} is not a multi-label field")
            tgt = rec.get(target)
            tgt = tgt if isinstance(tgt, list) else []
            if value not in tgt:
                tgt.append(value)
            rec[target] = tgt
            changelog.append({"record_id": rid, "value": value,
                              "from": field, "to": target})

    # annotate meta with the normalization step
    if META in pred:
        pred[META]["normalization"] = {
            "method": "B_relocation_deterministic",
            "n_edits": len(changelog),
            "edits": changelog,
        }

    json.dump(pred, open(out, "w"), indent=2, ensure_ascii=False)
    print(f"[fixed] {len(changelog)} edit(s) applied -> {out}")
    for c in changelog:
        print(f"  {c['record_id']}: '{c['value']}'  {c['from']} -> {c['to']}")


if __name__ == "__main__":
    main()
