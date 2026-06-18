# RQ1 Evaluation Report — seed 42

**Model:** `qwen3.5:35b` (digest `3460ffeede54`), Ollama `0.30.8`, temperature 0, think=false, seed 42.
**Scorable records:** 72 (gold in_scope==Yes). **JSON salvaged:** 0 record(s) where the model emitted a malformed (unquoted) `rationale`; scored fields recovered from the raw response, no re-generation.

## Headline

- **Overall macro-F1 (mean per-record): 0.650**
- Bootstrap mean 0.650, 95% CI [0.612, 0.683] (1000 resamples)
- Macro-F1 averaged over the 15 dimensions: 0.570
- **H1 (F1 ≥ 0.70): NOT SUPPORTED (95% CI entirely below 0.70)**
- One-sample t-test of per-record macro-F1 vs 0.70: t = -2.665, p = 0.009522

## (A) Schema compliance (RQ2 by-product)

Grammar was NOT enforced (think=false), so this is a real measurement.
- Total predicted values: **919**
- Off-vocabulary values: **1**
- **Schema-violation rate: 0.1%**

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
| actor_motive | 70 | 0 | 0.0% | — |
| action_variety | 75 | 1 | 1.3% | Defacement×1 |
| action_vector | 7 | 0 | 0.0% | — |
| asset_variety | 77 | 0 | 0.0% | — |
| attr_conf_data_variety | 96 | 0 | 0.0% | — |
| attr_integrity_variety | 13 | 0 | 0.0% | — |
| attr_avail_variety | 5 | 0 | 0.0% | — |

## (B) Per-dimension accuracy

### Single-label dimensions

| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) | micro-F1 |
|---|---:|---:|---:|---:|
| actor_category | 79.2% | 0.678 | 0.782 | 0.792 |
| action_category | 43.1% | 0.502 | 0.627 | 0.431 |
| asset_category | 65.3% | 0.280 | 0.373 | 0.653 |
| attr_conf_present | 90.3% | 0.585 | 0.877 | 0.903 |
| attr_integrity_present | 81.9% | 0.562 | 0.732 | 0.819 |
| attr_avail_present | 84.7% | 0.549 | 0.823 | 0.847 |
| attr_conf_disclosure | 36.1% | 0.455 | 0.426 | 0.361 |

### Multi-label dimensions (set P/R/F1)

| Dimension | macro-P | macro-R | macro-F1 | micro-F1 |
|---|---:|---:|---:|---:|
| actor_variety | 0.542 | 0.525 | 0.530 | 0.520 |
| actor_motive | 0.722 | 0.697 | 0.706 | 0.721 |
| action_variety | 0.549 | 0.531 | 0.536 | 0.523 |
| action_vector | 0.042 | 0.042 | 0.042 | 0.074 |
| asset_variety | 0.625 | 0.576 | 0.588 | 0.577 |
| attr_conf_data_variety | 0.801 | 0.751 | 0.755 | 0.743 |
| attr_integrity_variety | 0.896 | 0.898 | 0.893 | 0.519 |
| attr_avail_variety | 0.903 | 0.896 | 0.898 | 0.316 |

### Wilson 95% CIs (single-label accuracy)

| Dimension | Acc | 95% CI |
|---|---:|---|
| actor_category | 79.2% | [68.4%, 86.9%] |
| action_category | 43.1% | [32.3%, 54.6%] |
| asset_category | 65.3% | [53.8%, 75.2%] |
| attr_conf_present | 90.3% | [81.3%, 95.2%] |
| attr_integrity_present | 81.9% | [71.5%, 89.1%] |
| attr_avail_present | 84.7% | [74.7%, 91.2%] |
| attr_conf_disclosure | 36.1% | [26.0%, 47.6%] |

## (B) Per-sector breakdown

| Sector | n | macro-F1 |
|---|---:|---:|
| government | 53 | 0.631 |
| financial | 7 | 0.802 |
| telco | 3 | 0.733 |
| education_healthcare | 4 | 0.663 |
| unknown | 5 | 0.580 |

> ⚠️ Caveat: telco (n≤3) and education_healthcare (n≤4) cells are tiny and unstable; treat those numbers as indicative only.

## Narrative

The overall per-record macro-F1 is **0.650** (95% bootstrap CI [0.612, 0.683]), so H1 is **not supported**. The strongest dimension is `attr_avail_variety` (F1 0.898); the weakest is `action_vector` (F1 0.042). The measured schema-violation rate is 0.1%, recorded as an RQ2 by-product since the JSON grammar was deliberately not enforced.