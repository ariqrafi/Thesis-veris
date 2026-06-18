# RQ1 Evaluation Report — seed 42

**Model:** `qwen3.5:35b` (digest `3460ffeede54`), Ollama `0.30.7`, temperature 0, think=false, seed 42.
**Scorable records:** 72 (gold in_scope==Yes). **JSON salvaged:** 0 record(s) where the model emitted a malformed (unquoted) `rationale`; scored fields recovered from the raw response, no re-generation.

## Headline

- **Overall macro-F1 (mean per-record): 0.573**
- Bootstrap mean 0.573, 95% CI [0.545, 0.600] (1000 resamples)
- Macro-F1 averaged over the 15 dimensions: 0.494
- **H1 (F1 ≥ 0.70): NOT SUPPORTED (95% CI entirely below 0.70)**
- One-sample t-test of per-record macro-F1 vs 0.70: t = -8.928, p = 3.19e-13

## (A) Schema compliance (RQ2 by-product)

Grammar was NOT enforced (think=false), so this is a real measurement.
- Total predicted values: **1004**
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
| actor_motive | 75 | 0 | 0.0% | — |
| action_variety | 74 | 1 | 1.4% | Defacement×1 |
| action_vector | 74 | 0 | 0.0% | — |
| asset_variety | 74 | 0 | 0.0% | — |
| attr_conf_data_variety | 111 | 0 | 0.0% | — |
| attr_integrity_variety | 3 | 0 | 0.0% | — |
| attr_avail_variety | 17 | 0 | 0.0% | — |

## (B) Per-dimension accuracy

### Single-label dimensions

| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) | micro-F1 |
|---|---:|---:|---:|---:|
| actor_category | 79.2% | 0.573 | 0.537 | 0.792 |
| action_category | 40.3% | 0.484 | 0.605 | 0.403 |
| asset_category | 66.7% | 0.341 | 0.455 | 0.667 |
| attr_conf_present | 83.3% | 0.641 | 0.785 | 0.833 |
| attr_integrity_present | 59.7% | 0.353 | 0.530 | 0.597 |
| attr_avail_present | 65.3% | 0.489 | 0.600 | 0.653 |
| attr_conf_disclosure | 18.1% | 0.062 | 0.077 | 0.181 |

### Multi-label dimensions (set P/R/F1)

| Dimension | macro-P | macro-R | macro-F1 | micro-F1 |
|---|---:|---:|---:|---:|
| actor_variety | 0.417 | 0.394 | 0.400 | 0.400 |
| actor_motive | 0.840 | 0.826 | 0.829 | 0.829 |
| action_variety | 0.167 | 0.142 | 0.149 | 0.158 |
| action_vector | 0.153 | 0.148 | 0.150 | 0.162 |
| asset_variety | 0.618 | 0.562 | 0.579 | 0.575 |
| attr_conf_data_variety | 0.736 | 0.739 | 0.719 | 0.702 |
| attr_integrity_variety | 0.861 | 0.861 | 0.861 | 0.118 |
| attr_avail_variety | 0.785 | 0.785 | 0.782 | 0.258 |

### Wilson 95% CIs (single-label accuracy)

| Dimension | Acc | 95% CI |
|---|---:|---|
| actor_category | 79.2% | [68.4%, 86.9%] |
| action_category | 40.3% | [29.7%, 51.8%] |
| asset_category | 66.7% | [55.2%, 76.5%] |
| attr_conf_present | 83.3% | [73.1%, 90.2%] |
| attr_integrity_present | 59.7% | [48.2%, 70.3%] |
| attr_avail_present | 65.3% | [53.8%, 75.2%] |
| attr_conf_disclosure | 18.1% | [10.9%, 28.5%] |

## (B) Per-sector breakdown

| Sector | n | macro-F1 |
|---|---:|---:|
| government | 53 | 0.558 |
| financial | 7 | 0.669 |
| telco | 3 | 0.581 |
| education_healthcare | 4 | 0.622 |
| unknown | 5 | 0.549 |

> ⚠️ Caveat: telco (n≤3) and education_healthcare (n≤4) cells are tiny and unstable; treat those numbers as indicative only.

## Narrative

The overall per-record macro-F1 is **0.573** (95% bootstrap CI [0.545, 0.600]), so H1 is **not supported**. The strongest dimension is `attr_integrity_variety` (F1 0.861); the weakest is `attr_conf_disclosure` (F1 0.062). The measured schema-violation rate is 0.1%, recorded as an RQ2 by-product since the JSON grammar was deliberately not enforced.

## Core-A4 (category-level) — v2

Secondary headline restricted to the six single-label A4 *category* dimensions (actor/action/asset category + the three attribute-present flags).

| Dimension | Accuracy | macro-F1 (incl Unk) | macro-F1 (excl Unk) |
|---|---:|---:|---:|
| actor_category | 79.2% | 0.573 | 0.537 |
| action_category | 40.3% | 0.484 | 0.605 |
| asset_category | 66.7% | 0.341 | 0.455 |
| attr_conf_present | 83.3% | 0.641 | 0.785 |
| attr_integrity_present | 59.7% | 0.353 | 0.530 |
| attr_avail_present | 65.3% | 0.489 | 0.600 |
| **CORE-A4 macro-F1** | | **0.480** | **0.585** |

- **Incl. Unknown:** 0.480, 95% CI [0.402, 0.552] → **H1 NOT SUPPORTED (95% CI entirely below 0.70)**
- **Excl. Unknown:** 0.585, 95% CI [0.487, 0.691] → **H1 NOT SUPPORTED (95% CI entirely below 0.70)**
- Per-record macro-F1 mean 0.657; one-sample t-test vs 0.70: t = -1.777, p = 0.07992
