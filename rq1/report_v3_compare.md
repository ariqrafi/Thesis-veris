# RQ1 Part B — v2 zero-shot vs v3 few-shot (seed 42)

_v3 few-shot exemplars (6, leakage-safe): FS-01, FS-02, FS-04, FS-05, FS-06, FS-07. Exemplar annotations corrected 2026-06-14 (action_vector now filled on all 6; FS-01 conf fields)._

## Headline

| Metric | v2 zero-shot | v3 few-shot | Δ vs v2 |
|---|---:|---:|---:|
| Overall per-record macro-F1 (15 dim) | 0.573 | 0.684 | +0.111 |
| — 95% bootstrap CI | [0.545, 0.600] | [0.645, 0.719] | |
| Core-A4 macro-F1 incl Unknown | 0.480 | 0.528 | +0.048 |
| Core-A4 macro-F1 excl Unknown | 0.585 | 0.717 | +0.132 |
| Schema-violation rate | 0.1% | 0.2% | |

**H1 (overall ≥ 0.70):** v2 NOT SUPPORTED (0.573) → v3 **INCONCLUSIVE** (0.684, CI [0.645, 0.719] straddles 0.70).
**Core-A4 excl-Unknown:** v2 0.585 → v3 0.717 (CI [0.620, 0.796] straddles 0.70 → INCONCLUSIVE).

## Per-dimension headline F1

| Dimension | v2 | v3 (old/flawed) | v3 (corrected) | Δ vs v2 |
|---|---:|---:|---:|---:|
| actor_category | 0.573 | 0.678 | 0.628 | +0.055 |
| action_category | 0.484 | 0.502 | 0.517 | +0.033 |
| asset_category | 0.341 | 0.280 | 0.265 | -0.076 🔴 |
| attr_conf_present | 0.641 | 0.585 | 0.649 | +0.008 |
| attr_integrity_present | 0.353 | 0.562 | 0.562 | +0.209 🟢 |
| attr_avail_present | 0.489 | 0.549 | 0.549 | +0.060 |
| attr_conf_disclosure | 0.062 | 0.455 | 0.323 | +0.261 🟢 |
| actor_variety | 0.400 | 0.530 | 0.553 | +0.153 🟢 |
| actor_motive | 0.829 | 0.706 | 0.678 | -0.151 🔴 |
| action_variety | 0.149 | 0.536 | 0.654 | +0.505 🟢 |
| action_vector | 0.150 | 0.042 | 0.567 | +0.417 🟢 |
| asset_variety | 0.579 | 0.588 | 0.580 | +0.001 |
| attr_conf_data_variety | 0.719 | 0.755 | 0.766 | +0.047 |
| attr_integrity_variety | 0.861 | 0.893 | 0.886 | +0.025 |
| attr_avail_variety | 0.782 | 0.898 | 0.898 | +0.116 🟢 |

🟢 ≥+0.10  🔴 ≤−0.05

**action_vector fix:** the regression is resolved — 0.042 (empty-vector exemplars) → 0.567 (corrected). Filling action_vector in all 6 exemplars stopped the model under-predicting it.
