# RQ1 Evaluation Report — seed 42

**Model:** `qwen3.5:35b` (digest `3460ffeede54`), Ollama `0.30.8`, temperature 0, think=false, seed 42.
**Scorable records:** 72 (gold in_scope==Yes). **JSON salvaged:** 0 record(s) where the model emitted a malformed (unquoted) `rationale`; scored fields recovered from the raw response, no re-generation.

## Headline

- **Overall macro-F1 (mean per-record): 0.684**
- Bootstrap mean 0.684, 95% CI [0.645, 0.719] (1000 resamples)
- Macro-F1 averaged over the 15 dimensions: 0.605
- **H1 (F1 ≥ 0.70): INCONCLUSIVE (95% CI straddles 0.70)**
- One-sample t-test of per-record macro-F1 vs 0.70: t = -0.787, p = 0.4337

## (A) Schema compliance (RQ2 by-product)

Grammar was NOT enforced (think=false), so this is a real measurement.
- Total predicted values: **976**
- Off-vocabulary values: **2**
- **Schema-violation rate: 0.2%**

| Dimension | Values | Off-vocab | Rate | Top off-vocab examples |
|---|---:|---:|---:|---|
| actor_category | 72 | 0 | 0.0% | — |
| action_category | 72 | 0 | 0.0% | — |
| asset_category | 72 | 0 | 0.0% | — |
| attr_conf_present | 72 | 0 | 0.0% | — |
| attr_integrity_present | 72 | 0 | 0.0% | — |
| attr_avail_present | 72 | 0 | 0.0% | — |
| attr_conf_disclosure | 72 | 0 | 0.0% | — |
| actor_variety | 72 | 0 | 0.0% | — |
| actor_motive | 68 | 0 | 0.0% | — |
| action_variety | 73 | 1 | 1.4% | Defacement×1 |
| action_vector | 73 | 0 | 0.0% | — |
| asset_variety | 74 | 0 | 0.0% | — |
| attr_conf_data_variety | 99 | 0 | 0.0% | — |
| attr_integrity_variety | 8 | 1 | 12.5% | Obscuration×1 |
| attr_avail_variety | 5 | 0 | 0.0% | — |

## (B) Per-dimension accuracy

### Single-label dimensions

| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) | micro-F1 |
|---|---:|---:|---:|---:|
| actor_category | 75.0% | 0.628 | 0.774 | 0.750 |
| action_category | 41.7% | 0.517 | 0.647 | 0.417 |
| asset_category | 63.9% | 0.265 | 0.354 | 0.639 |
| attr_conf_present | 90.3% | 0.649 | 0.974 | 0.903 |
| attr_integrity_present | 81.9% | 0.562 | 0.732 | 0.819 |
| attr_avail_present | 84.7% | 0.549 | 0.823 | 0.847 |
| attr_conf_disclosure | 30.6% | 0.323 | 0.403 | 0.306 |

### Multi-label dimensions (set P/R/F1)

| Dimension | macro-P | macro-R | macro-F1 | micro-F1 |
|---|---:|---:|---:|---:|
| actor_variety | 0.569 | 0.546 | 0.553 | 0.547 |
| actor_motive | 0.694 | 0.669 | 0.678 | 0.703 |
| action_variety | 0.667 | 0.649 | 0.654 | 0.636 |
| action_vector | 0.569 | 0.565 | 0.567 | 0.571 |
| asset_variety | 0.625 | 0.559 | 0.580 | 0.562 |
| attr_conf_data_variety | 0.812 | 0.754 | 0.766 | 0.742 |
| attr_integrity_variety | 0.889 | 0.884 | 0.886 | 0.455 |
| attr_avail_variety | 0.903 | 0.896 | 0.898 | 0.316 |

### Wilson 95% CIs (single-label accuracy)

| Dimension | Acc | 95% CI |
|---|---:|---|
| actor_category | 75.0% | [63.9%, 83.6%] |
| action_category | 41.7% | [31.0%, 53.2%] |
| asset_category | 63.9% | [52.4%, 74.0%] |
| attr_conf_present | 90.3% | [81.3%, 95.2%] |
| attr_integrity_present | 81.9% | [71.5%, 89.1%] |
| attr_avail_present | 84.7% | [74.7%, 91.2%] |
| attr_conf_disclosure | 30.6% | [21.1%, 42.0%] |

## (B) Per-sector breakdown

| Sector | n | macro-F1 |
|---|---:|---:|
| government | 53 | 0.671 |
| financial | 7 | 0.774 |
| telco | 3 | 0.800 |
| education_healthcare | 4 | 0.694 |
| unknown | 5 | 0.618 |

> ⚠️ Caveat: telco (n≤3) and education_healthcare (n≤4) cells are tiny and unstable; treat those numbers as indicative only.

## Narrative

The overall per-record macro-F1 is **0.684** (95% bootstrap CI [0.645, 0.719]), so H1 is **inconclusive**. The strongest dimension is `attr_avail_variety` (F1 0.898); the weakest is `asset_category` (F1 0.265). The measured schema-violation rate is 0.2%, recorded as an RQ2 by-product since the JSON grammar was deliberately not enforced.