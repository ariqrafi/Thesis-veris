# Enum changelog — VERIS-A4 controlled vocabulary (2026-06-15)

**Trigger:** RQ2 Task 4 flagged 10 vocabulary violations (Defacement ×5, Obscuration ×5).
Suspicion: some are *false* violations from an incomplete enum.

**Policy adopted (Task C):** controlled vocabulary = full official VERIS 1.3.x per
field, and the enum MUST be a superset of every value in the frozen
`gold_standard.json` (gold is the scoring truth). Off-vocabulary = violation,
never remapped. Add-only — no value removed.

**Authoritative source:** `vz-risk/veris` `verisc-enum.json` (fetched 2026-06-15).

## Gold-superset invariant (Task B) — values in gold but missing from their enum

| Field (predicted) | Gold value | Records | Official VERIS home | Action |
|---|---|---|---|---|
| `action_variety` | `Defacement` | GS-080 | `attribute.integrity.variety` | **add to `action.hacking.variety`** |
| `attr_integrity_variety` | `Destroy data` | GS-020 | `action.malware.variety` | **add to `attribute.integrity.variety`** |
| `attr_avail_variety` | `Encryption` | GS-026 | *(not in VERIS)* | **add to `attribute.availability.variety`** |

All three were genuine enum gaps: a gold-correct answer was being scored as a
schema violation. Fixed.

## Diff (`veris_enums.py`, add-only)

```
action.hacking.variety:
  ... "Cross-site scripting (XSS)", "Cryptanalysis", → "...", "Cryptanalysis", "Defacement", ...

attribute.integrity.variety:
  ... "Repurpose", "Software installation", "Other", "Unknown"]
  →   ... "Repurpose", "Software installation", "Destroy data", "Other", "Unknown"]

attribute.availability.variety:
  ... "Loss", "Obscuration", "Outage", "Other", "Unknown"]
  →   ... "Loss", "Obscuration", "Outage", "Encryption", "Other", "Unknown"]
```

### Per-value justification
- **Defacement → `action.hacking.variety`.** Official VERIS classes Defacement as an
  *integrity* variety (gold GS-080 also uses it there). But gold additionally annotates
  `action_variety=["Defacement"]` for the same Hacking/web-defacement incident, so the
  action-variety union must admit it. Placed under the Hacking sub-list (GS-080 is
  `action_category=Hacking`, `action_vector=Web application`). Non-standard vs official
  VERIS action varieties, but required by frozen gold.
- **Destroy data → `attribute.integrity.variety`.** Official VERIS lists "Destroy data"
  under `action.malware.variety`; gold GS-020 applies it as an integrity impact
  (data destruction). Added for gold coverage.
- **Encryption → `attribute.availability.variety`.** Not an official VERIS enum value, but
  a frozen gold label (GS-026 ransomware → encryption renders data unavailable). Added for
  gold coverage.

## NOT changed (rejected)
- **`Obscuration` → integrity:** REJECTED. The user's premise that Obscuration is a valid
  *integrity* variety is a misattribution. In official VERIS 1.3.x, `Obscuration` is an
  `attribute.availability.variety` (already present in our enum), not integrity, and gold
  never uses it in any field. The model's `attr_integrity_variety=["Obscuration"]` (GS-099,
  whose gold `attr_integrity_variety=[]`) is a genuine off-vocab misplacement and **remains
  a schema violation** — not remapped, not absorbed.

## Effect (see rq2_schema_compliance_v2.json, rq2_f1_delta_enumfix.json)
- **SVR unchanged: 8.00% → 8.00%.** The Defacement record (GS-080) is *also* a
  missing-field violation, so removing its vocab cause does not make it compliant; the
  Obscuration violation is genuine and stays. The fix changes *cause attribution*, not the
  headline SVR.
- **Vocabulary conformance: 99.705% → 99.853%** (5 off-vocab values cleared: Defacement ×5).
- **Cause breakdown:** vocabulary records 10 → 5; missing unchanged at 15.
- **F1 unchanged everywhere** (RQ1 n=72 overall 0.6841, action_variety 0.6537,
  attr_integrity_variety 0.8861; RQ2 n=50 0.6757). The F1 scorer matches predicted vs gold
  label *sets* by string and never dropped/remapped off-vocab predictions, so the Defacement
  match was already credited. **No RQ1 / chapter_4 table change needed.**
