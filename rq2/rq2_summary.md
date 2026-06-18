# RQ2 — Consistency, Reproducibility & Schema Compliance

**Model:** `qwen3.5:35b` (digest `3460ffeede54`), Ollama `0.30.8`, think=false, num_ctx=32768, input=full_content_clean[:16000], few-shot v3 (6 exemplars).  
**Subset:** 50 records, stratified by sector (largest-remainder, seed 20260615), leakage-safe vs the 6 exemplars (overlap=[]).  
**Seed strategy:** temp=0 → seed 42 on all 5 runs (determinism test); temp=0.3/0.7 → seeds 42–46 (sample the stochastic distribution).

## Task 3 — Determinism (5× temp=0, seed=42)

- Scored A4 labels identical across all 5 runs: **True** (50/50 docs).
- Raw byte-identical across all 5 runs: **True** (50/50 docs).

> All scored A4 labels identical across the 5 temp=0/seed=42 runs: agreement=1.0 is trivial and Fleiss is undefined for constant dimensions; reproducibility evidence rests on the temperature stability analysis (Task 6).

## Task 4 — Schema compliance (H2a)

Aggregated over all 250 temp=0 outputs (50 docs × 5 runs). Validation module is the source of truth; off-vocabulary = violation (not remapped).

| Metric | Value |
|---|---:|
| Schema-violation rate (SVR) | **8.00%** |
| SVR Wilson 95% CI | [5.24%, 12.03%] |
| Field completeness rate | 99.47% |
| Vocabulary conformance rate | 99.71% |
| Violation records | 20 / 250 |

**Failure causes** (record counts; a record may have several):  
`{'missing': 15, 'vocabulary': 10}` — sole-cause: `{'missing': 10, 'vocabulary': 5}`

One-sample proportion test vs 0.10: two-sided z=-1.054 (p=0.292); directional (SVR<0.10) z=-1.054 (p=0.146); binomtest p=0.342.

Per-field off-vocabulary (value-level):

| Field | values | off | rate | top examples |
|---|---:|---:|---:|---|
| action_variety | 255 | 5 | 1.96% | Defacement×5 |
| attr_integrity_variety | 40 | 5 | 12.50% | Obscuration×5 |

**H2a verdict (pre-registered 3-way rule): INCONCLUSIVE** — Wilson 95% CI [5.24%, 12.03%] straddles 10% (SUPPORTED iff upper < 10%; NOT SUPPORTED iff CI entirely ≥ 10%).

> Enum-completeness audit (2026-06-15, see `CHANGELOG_enum_2026-06-15.md` / `rq2_schema_compliance_v2.json`): three gold-superset enum gaps were fixed (Defacement→action, Destroy data→integrity, Encryption→availability). SVR is **unchanged at 8.00%** — the Defacement record (GS-080) also fails on missing fields, and the Obscuration case (GS-099) is a genuine off-vocab violation (Obscuration is VERIS *availability*, not integrity, and absent from gold). Only effects: vocabulary conformance 99.71% → 99.85%, vocabulary-cause records 10 → 5. F1 unchanged everywhere.

## Task 5 — Reproducibility (H2b)

- Mean per-doc pairwise agreement (full A4 label, 5 runs → 10 pairs): **1.000**
- Mean exact-match-all-runs: **1.000**
- Agreement 95% CI(t): [1.000, 1.000]  (zero variance across documents (degenerate) — all per-doc agreements identical; t-test undefined, CI collapses to the mean)
- Fleiss' κ macro (over defined dims): **1.000**

| Dimension | Fleiss κ |
|---|---:|
| actor_category | 1.000 |
| action_category | 1.000 |
| asset_category | 1.000 |
| attr_conf_present | 1.000 |
| attr_integrity_present | 1.000 |
| attr_avail_present | 1.000 |
| attr_conf_disclosure | 1.000 |
| actor_variety | 1.000 |
| actor_motive | 1.000 |
| action_variety | 1.000 |
| action_vector | 1.000 |
| asset_variety | 1.000 |
| attr_conf_data_variety | 1.000 |
| attr_integrity_variety | 1.000 |
| attr_avail_variety | 1.000 |

> All scored A4 labels identical across the 5 temp=0/seed=42 runs: agreement=1.0 is trivial and Fleiss is undefined for constant dimensions; reproducibility evidence rests on the temperature stability analysis (Task 6).

**H2b verdict: SUPPORTED** (SUPPORTED iff lower bound of mean-agreement CI >= 0.85: lower CI = 1.000).

## Task 6 — Temperature stability

| Temp | runs | F1 mean | F1 variance | F1 std | F1 range | SVR |
|---|---:|---:|---:|---:|---|---:|
| 0.0 | 5 | 0.676 | 0.00e+00 | 0.0000 | [0.676, 0.676] | 8.00% |
| 0.3 | 5 | 0.673 | 4.84e-05 | 0.0070 | [0.662, 0.680] | 6.00% |
| 0.7 | 5 | 0.655 | 3.43e-04 | 0.0185 | [0.633, 0.675] | 8.80% |

## Task 7 — Heterogeneity

### By sector

| Group | docs | outputs | SVR | mean agreement |
|---|---:|---:|---:|---:|
| education_healthcare | 3 | 15 | 0.00% | 1.000 |
| financial | 5 | 25 | 0.00% | 1.000 |
| government | 37 | 185 | 8.11% | 1.000 |
| telco | 2 | 10 | 0.00% | 1.000 |
| unknown | 3 | 15 | 33.33% | 1.000 |

### By language

| Group | docs | outputs | SVR | mean agreement |
|---|---:|---:|---:|---:|
| en | 5 | 25 | 20.00% | 1.000 |
| id | 42 | 210 | 7.14% | 1.000 |
| mixed | 3 | 15 | 0.00% | 1.000 |

### By source

| Group | docs | outputs | SVR | mean agreement |
|---|---:|---:|---:|---:|
| media | 43 | 215 | 4.65% | 1.000 |
| regulatory | 1 | 5 | 0.00% | 1.000 |
| vendor | 6 | 30 | 33.33% | 1.000 |

> source-type is derived from URL domain; the in-scope corpus is news/media-dominated (no BSSN domains present), so the 'media' bucket dominates and other buckets are tiny.

## Task 8 — Cross-verification

- Field-slot accounting per run (50 × 15 = 750) verified; all runs consistent: **True**.
- SVR(temp0) Task4=8.00% vs Task6=8.00% → match.
- No missing/extra records in any run.

## Verdicts

- **H2a (schema compliance, SVR < 0.10): INCONCLUSIVE** (pre-registered 3-way rule) — SVR 8.00%, Wilson 95% CI [5.24%, 12.03%] straddles 10% (unchanged after the 2026-06-15 enum-completeness fix).
- **H2b (reproducibility, mean agreement ≥ 0.85): SUPPORTED** — mean agreement 1.000, lower CI 1.000.

> Note: at temp=0/seed=42 the extractor is fully deterministic, so H2b's agreement is trivially 1.0; the substantive reproducibility evidence is the low F1 variance across temperatures (Task 6).
