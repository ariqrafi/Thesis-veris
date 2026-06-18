# RQ1 Part B — v2 zero-shot vs v3 few-shot (seed 42)

_v3 few-shot exemplars (6, leakage-safe, from outside eval-100): FS-01, FS-02, FS-04, FS-05, FS-06, FS-07._

## Headline

| Metric | v2 zero-shot | v3 few-shot | Δ |
|---|---:|---:|---:|
| Overall per-record macro-F1 (15 dim) | 0.573 | 0.650 | +0.077 |
| — 95% bootstrap CI | [0.545, 0.600] | [0.612, 0.683] | |
| Core-A4 macro-F1 incl Unknown | 0.480 | 0.526 | +0.046 |
| Core-A4 macro-F1 excl Unknown | 0.585 | 0.703 | +0.117 |
| Schema-violation rate | 0.1% | 0.1% | +0.0pp |

**H1 (overall ≥ 0.70):** v2 NOT SUPPORTED (0.573) → v3 NOT SUPPORTED (0.650, CI [0.612, 0.683]).
**Core-A4 excl-Unknown:** v2 0.585 → v3 0.703 (CI [0.606, 0.787], straddles 0.70 → INCONCLUSIVE).

## Per-dimension headline F1

| Dimension | v2 | v3 | Δ |
|---|---:|---:|---:|
| actor_category | 0.573 | 0.678 | +0.104 🟢 |
| action_category | 0.484 | 0.502 | +0.017 |
| asset_category | 0.341 | 0.280 | -0.061 🔴 |
| attr_conf_present | 0.641 | 0.585 | -0.056 🔴 |
| attr_integrity_present | 0.353 | 0.562 | +0.209 🟢 |
| attr_avail_present | 0.489 | 0.549 | +0.060 |
| attr_conf_disclosure | 0.062 | 0.455 | +0.393 🟢 |
| actor_variety | 0.400 | 0.530 | +0.130 🟢 |
| actor_motive | 0.829 | 0.706 | -0.123 🔴 |
| action_variety | 0.149 | 0.536 | +0.387 🟢 |
| action_vector | 0.150 | 0.042 | -0.108 🔴 |
| asset_variety | 0.579 | 0.588 | +0.009 |
| attr_conf_data_variety | 0.719 | 0.755 | +0.036 |
| attr_integrity_variety | 0.861 | 0.893 | +0.032 |
| attr_avail_variety | 0.782 | 0.898 | +0.116 🟢 |

🟢 ≥+0.10  🔴 ≤−0.05

**Biggest gains:** attr_conf_disclosure (+0.393), action_variety (+0.387), attr_integrity_present (+0.209), actor_variety (+0.130), attr_avail_variety (+0.116), actor_category (+0.104). The two dimensions v2 was worst at — action_variety and attr_conf_disclosure — improved the most, which drove the headline jump.

**Regressions:** actor_motive (−0.123, was v2's strongest dim — few-shot may have biased it toward "Financial"), action_vector (−0.108, now ~0.04: the 6 exemplars mostly left action_vector empty, so the model now under-predicts it), asset_category (−0.061), attr_conf_present (−0.056).

**Still weak after few-shot:** action_vector (0.042), asset_category (single-acc 65%, F1 incl-Unk 0.280), action_category (acc 43%), attr_conf_disclosure (single-acc 36%).
