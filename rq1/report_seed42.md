# RQ1 Evaluation Report — seed 42

**Model:** `qwen3.5:35b` (digest `3460ffeede54`), Ollama `0.30.7`, temperature 0, think=false, seed 42.
**Scorable records:** 72 (gold in_scope==Yes). **JSON salvaged:** 13 record(s) where the model emitted a malformed (unquoted) `rationale`; scored fields recovered from the raw response, no re-generation.

## Headline

- **Overall macro-F1 (mean per-record): 0.543**
- Bootstrap mean 0.542, 95% CI [0.513, 0.571] (1000 resamples)
- Macro-F1 averaged over the 15 dimensions: 0.460
- **H1 (F1 ≥ 0.70): NOT SUPPORTED (95% CI entirely below 0.70)**
- One-sample t-test of per-record macro-F1 vs 0.70: t = -10.544, p = 3.551e-16

## (A) Schema compliance (RQ2 by-product)

Grammar was NOT enforced (think=false), so this is a real measurement.
- Total predicted values: **1006**
- Off-vocabulary values: **20**
- **Schema-violation rate: 2.0%**

| Dimension | Values | Off-vocab | Rate | Top off-vocab examples |
|---|---:|---:|---:|---|
| actor_category | 72 | 0 | 0.0% | — |
| action_category | 72 | 0 | 0.0% | — |
| asset_category | 72 | 18 | 25.0% | Database×18 |
| attr_conf_present | 72 | 0 | 0.0% | — |
| attr_integrity_present | 72 | 0 | 0.0% | — |
| attr_avail_present | 72 | 0 | 0.0% | — |
| attr_conf_disclosure | 72 | 0 | 0.0% | — |
| actor_variety | 72 | 0 | 0.0% | — |
| actor_motive | 73 | 0 | 0.0% | — |
| action_variety | 75 | 1 | 1.3% | Defacement×1 |
| action_vector | 75 | 0 | 0.0% | — |
| asset_variety | 76 | 1 | 1.3% | User Device×1 |
| attr_conf_data_variety | 121 | 0 | 0.0% | — |
| attr_integrity_variety | 1 | 0 | 0.0% | — |
| attr_avail_variety | 9 | 0 | 0.0% | — |

## (B) Per-dimension accuracy

### Single-label dimensions

| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) | micro-F1 |
|---|---:|---:|---:|---:|
| actor_category | 69.4% | 0.527 | 0.507 | 0.694 |
| action_category | 40.3% | 0.475 | 0.593 | 0.403 |
| asset_category | 37.5% | 0.212 | 0.282 | 0.375 |
| attr_conf_present | 86.1% | 0.308 | 0.463 | 0.861 |
| attr_integrity_present | 59.7% | 0.361 | 0.465 | 0.597 |
| attr_avail_present | 81.9% | 0.654 | 0.847 | 0.819 |
| attr_conf_disclosure | 19.4% | 0.163 | 0.204 | 0.194 |

### Multi-label dimensions (set P/R/F1)

| Dimension | macro-P | macro-R | macro-F1 | micro-F1 |
|---|---:|---:|---:|---:|
| actor_variety | 0.250 | 0.227 | 0.234 | 0.240 |
| actor_motive | 0.896 | 0.873 | 0.877 | 0.867 |
| action_variety | 0.139 | 0.115 | 0.121 | 0.131 |
| action_vector | 0.132 | 0.130 | 0.131 | 0.134 |
| asset_variety | 0.403 | 0.354 | 0.368 | 0.383 |
| attr_conf_data_variety | 0.696 | 0.760 | 0.705 | 0.689 |
| attr_integrity_variety | 0.875 | 0.875 | 0.875 | 0.133 |
| attr_avail_variety | 0.889 | 0.882 | 0.884 | 0.348 |

### Wilson 95% CIs (single-label accuracy)

| Dimension | Acc | 95% CI |
|---|---:|---|
| actor_category | 69.4% | [58.0%, 78.9%] |
| action_category | 40.3% | [29.7%, 51.8%] |
| asset_category | 37.5% | [27.2%, 49.0%] |
| attr_conf_present | 86.1% | [76.3%, 92.3%] |
| attr_integrity_present | 59.7% | [48.2%, 70.3%] |
| attr_avail_present | 81.9% | [71.5%, 89.1%] |
| attr_conf_disclosure | 19.4% | [12.0%, 30.0%] |

## (B) Per-sector breakdown

| Sector | n | macro-F1 |
|---|---:|---:|
| government | 53 | 0.547 |
| financial | 7 | 0.567 |
| telco | 3 | 0.515 |
| education_healthcare | 4 | 0.522 |
| unknown | 5 | 0.493 |

> ⚠️ Caveat: telco (n≤3) and education_healthcare (n≤4) cells are tiny and unstable; treat those numbers as indicative only.

## Narrative

The overall per-record macro-F1 is **0.543** (95% bootstrap CI [0.513, 0.571]), so H1 is **not supported**. The strongest dimension is `attr_avail_variety` (F1 0.884); the weakest is `action_variety` (F1 0.121). The measured schema-violation rate is 2.0%, recorded as an RQ2 by-product since the JSON grammar was deliberately not enforced.

## Core-A4 (category-level)

Secondary headline restricted to the six single-label A4 *category* dimensions (actor/action/asset category + the three attribute-present flags).

| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) |
|---|---:|---:|---:|
| actor_category | 69.4% | 0.527 | 0.507 |
| action_category | 40.3% | 0.475 | 0.593 |
| asset_category | 37.5% | 0.212 | 0.282 |
| attr_conf_present | 86.1% | 0.308 | 0.463 |
| attr_integrity_present | 59.7% | 0.361 | 0.465 |
| attr_avail_present | 81.9% | 0.654 | 0.847 |
| **CORE-A4 macro-F1** | | **0.423** | **0.526** |

- **Incl. Unknown:** 0.423, 95% CI [0.367, 0.484] → **H1 NOT SUPPORTED (95% CI entirely below 0.70)**
- **Excl. Unknown:** 0.526, 95% CI [0.460, 0.628] → **H1 NOT SUPPORTED (95% CI entirely below 0.70)**
- Per-record macro-F1 mean 0.625; one-sample t-test vs 0.70: t = -3.047, p = 0.003244
