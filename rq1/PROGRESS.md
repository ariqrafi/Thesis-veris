# RQ1 — Progress / Status Log

_Last updated: 2026-06-13. Schema-constrained VERIS A4 extraction from Indonesian
data-breach reports. Model under eval: local **qwen3.5:35b** (Ollama, digest
`3460ffeede54`). Gold: `gold_standard.json` (100 records, 72 scorable / `in_scope==Yes`).
Hypothesis H1: overall F1 ≥ 0.70._

## Fixed run settings (all runs)
- temperature 0, seed 42, `think:false`, `num_ctx:32768`, pinned digest `3460ffeede54`
- Ollama 0.30.7. Grammar NOT enforced (think:false) → schema compliance is a real measured quantity.
- `gold_standard.json` is never edited. Few-shot exemplars only from corpus OUTSIDE the 100 eval records.
- Scorer needs numpy/scipy → run as **`/venv/main/bin/python score_rq1.py`** (extractor uses stdlib only).

## Status by stage

| Stage | State | Headline result |
|---|---|---|
| Pipeline build (enums, fields, extractor, scorer) | ✅ done | — |
| v1 zero-shot (baseline prompt) | ✅ done | overall macro-F1 **0.543** (CI 0.513–0.571), H1 **not supported** |
| v2 zero-shot (structural prompt fixes) | ✅ done | overall macro-F1 **0.573** (CI 0.545–0.600), H1 **not supported** |
| Core-A4 metric (6 category dims) v1 & v2 | ✅ done | v2 incl-Unk 0.480, excl-Unk 0.585 — H1 not supported |
| Part 0 — num_ctx / truncation check | ✅ done | **No truncation** (max prompt 5029 tok; default==32768). Baseline valid. |
| Part A — few-shot candidate selection | ✅ done | `fewshot_candidates.json` (8 candidates, leakage-safe) |
| Part A — human annotation of 6 exemplars | ✅ done | `fewshot_exemplars.json` (FS-01,02,04,05,06,07 use:true; validated, no leakage) |
| Part B — few-shot v3 run + comparison | ✅ done (re-run, corrected exemplars) | overall macro-F1 **0.684** (CI 0.645–0.719), H1 **inconclusive**; Core-A4 excl-Unk **0.717** (CI 0.620–0.796 → inconclusive) |

## v1 vs v2 vs v3 numbers (seed 42)
| Metric | v1 | v2 | v3 few-shot (corrected) |
|---|---:|---:|---:|
| Schema-violation rate | 2.0% | **0.1%** | 0.2% |
| Overall macro-F1 (15 dim, per-record) | 0.543 | 0.573 | **0.684** |
| — 95% bootstrap CI | [0.513, 0.571] | [0.545, 0.600] | [0.645, 0.719] |
| Core-A4 macro-F1 incl Unknown | 0.423 | 0.480 | 0.528 |
| Core-A4 macro-F1 excl Unknown | 0.526 | 0.585 | **0.717** (CI [0.620,0.796]) |
| H1 (≥0.70) | NOT SUPPORTED | NOT SUPPORTED | INCONCLUSIVE (overall & excl-Unk CI straddle 0.70) |

**v3 re-run note (2026-06-14):** first v3 used flawed exemplars (action_vector left empty on most) → action_vector
regressed to 0.04 and overall was 0.650. Researcher corrected `fewshot_exemplars.json` (action_vector filled on
all 6; FS-01 conf fields). The flawed run is archived in `_v3_old_flawed/`.
v2→v3(corrected) biggest gains: `action_variety` (+0.505, was a worst dim), `action_vector` (+0.417, fix worked),
`attr_conf_disclosure` (+0.261), `attr_integrity_present` (+0.209), `actor_variety` (+0.153), `attr_avail_variety` (+0.116).
v2→v3 regressions: `actor_motive` (−0.151, was strongest — few-shot likely biases to "Financial"),
`asset_category` (−0.076, still confused with asset_variety).
Still weak after few-shot: `asset_category` (F1 0.265, acc 64%), `attr_conf_disclosure` (acc 31%), `action_category` (acc 42%).
Full comparison (incl old/flawed column): `report_v3_compare.md`.

## v3 few-shot setup
- `extract_qwen_fewshot.py` (PROMPT_VERSION="v3_fewshot"): reuses v2 system prompt + format schema + parsing;
  inserts 6 exemplars as alternating user/assistant turns before the real query (assistant = 15-key gold JSON).
- Exemplars: `fewshot_exemplars.json` (use:true → FS-01,02,04,05,06,07; text pulled from `fewshot_candidates.json`).
  Leakage re-checked at load time. Prompt size ~8.6k tok (exemplars add ~5.7k over baseline) — well under num_ctx 32768.
- Outputs: `predictions_v3_fewshot_seed42.json`, `metrics_v3_seed42.json`, `metrics_core_v3_seed42.json`,
  `report_v3_seed42.md`, `errors_v3_seed42.csv`, `report_v3_compare.md`, `extract_v3_seed42.log`.

## v2 → v3 changes (already coded, two STRUCTURAL prompt edits only)
1. Emphatic CATEGORY-vs-VARIETY separation rule (+ Server/Database illustration; generic, not a corpus exemplar).
2. `rationale` removed from required output + `format` schema (killed the 13 unquoted-JSON salvages).
`extract_qwen_v2.py` also now: `--num-ctx` default 32768, persists `_prompt_eval_count`.

## Part 0 evidence (num_ctx)
Prompt sizes across 72 records: max **5029** (GS-052), mean 2909, min 2426; 3 records >4096, none >8192.
GS-052 without `num_ctx` = 5029, with `num_ctx=32768` = 5029 (identical) → default did NOT truncate.
Decision: pin `num_ctx=32768` for all subsequent runs anyway (few-shot adds tokens). v2 baseline stands.

## Part A — few-shot candidate pool
- Source corpus `dataset_clean.jsonl` (642 records; has `full_content`, no `_clean`, no `record_id`).
- Excluded all 100 eval `content_hash`es → **542-record leakage-safe pool**. Leakage check on the 8: **none in eval-100 ✓**.
- `fewshot_candidates.json`: FS-01..FS-08, each = {cand_id, sector, language, title, url, content_hash,
  text (full_content[:4000]), empty `annotation` template (15 scored fields)}.

| cid | suggested bucket | sector(tag) | lang | incident |
|---|---|---|---|---|
| FS-01 | Malware/Ransomware | government | mixed | PDNS 2 / Brain Cipher (Jun 2024) |
| FS-02 | Hacking (published) | e-commerce | en | Tokopedia 15M leaked |
| FS-03 | Hacking | government | en | Edu & Culture Ministry 1.3M |
| FS-04 | DoS | financial | en | BI + Bank of Korea DDoS |
| FS-05 | Hacking (sold) | government | en | KPU 2.3M voters on raidforums |
| FS-06 | Hacking/Misuse | financial | en | BRI Life 2M sold on RaidForums |
| FS-07 | Misuse/insider | telco | id | Telkomsel / Denny Siregar leak |
| FS-08 | Hacking (sold) | education | id | UI/ITB/UGM/UNPAD student data on dark web |

Caveats: no clean Phishing- or Misconfiguration-origin single incident in the out-of-eval corpus
(dominated by "data sold on dark web"); corpus sector tags are noisy. cids are NOT stable across
re-filtering — anchor on content_hash.

## NEXT STEPS
Part B done. Candidate directions (none started):
1. **Fix the action_vector regression:** the 6 exemplars mostly left `action_vector=[]`, so the model now
   under-predicts it (F1 0.042). Either annotate action_vector in the exemplars (e.g. "Web application" for the
   hacking/DoS ones) and re-run, or add a vector exemplar — cheapest single lever left.
2. **RQ2 stability:** repeat v3 (and v2 baseline) across ≥5 seeds for mean±sd / CI on the headline; the
   extractor already persists `_prompt_eval_count` and accepts `--seed`.
3. **Exemplar count/selection ablation:** vary K (3/6/8) or swap exemplars to test sensitivity.
4. **Error-driven:** mine `errors_v3_seed42.csv` for the still-weak single dims (action_category 43%,
   attr_conf_disclosure 36%, asset_category 65%).

## File inventory (in /root/rq1)
- Code: `veris_enums.py`, `veris_fields.py`, `extract_qwen.py` (v1), `extract_qwen_v2.py` (v2/v3-base), `score_rq1.py`, `score_core.py`
- v1 outputs: `predictions_seed42.json`, `metrics_seed42.json`, `metrics_core_seed42.json`, `report_seed42.md`, `errors_seed42.csv`
- v2 outputs: `predictions_v2_seed42.json`, `metrics_v2_seed42.json`, `metrics_core_v2_seed42.json`, `report_v2_seed42.md`, `errors_v2_seed42.csv`
- v3 outputs: `predictions_v3_fewshot_seed42.json`, `metrics_v3_seed42.json`, `metrics_core_v3_seed42.json`, `report_v3_seed42.md`, `errors_v3_seed42.csv`, `report_v3_compare.md`, `extract_v3_seed42.log`
- Consolidated: `RINGKASAN_RQ1.md`
- Few-shot: `dataset_clean.jsonl` (corpus), `fewshot_candidates.json`, `fewshot_exemplars.json` (filled), `extract_qwen_fewshot.py`
- Data: `eval_set_100.jsonl`, `gold_standard.json` (do not edit)
