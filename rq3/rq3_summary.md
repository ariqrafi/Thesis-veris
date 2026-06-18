# RQ3 — Robustness Evaluation Report

**Research Question 3:** How robust is the schema-constrained LLM framework against (A) linguistic variation, (B) class imbalance, and (C) incomplete information typical of Indonesian data breach incident reports?

**Hypothesis H3:** Performance degradation (ΔF1 = F1_baseline − F1_scenario) ≤ 0.15 across all stress-test scenarios. *SUPPORTED* iff the upper bound of the 95% bootstrap CI for ΔF1 < 0.15 for every scenario.

## 1. Baseline (Task 0 — Clean v3 Predictions)

| Metric | Value |
|---|---:|
| Overall macro-F1 (15 dim, per-record) | **0.6841** |
| — 95% bootstrap CI | [0.6446, 0.7190] |
| Core-A4 macro-F1 excl-Unknown | **0.7172** |
| Schema-violation rate (SVR) | 0.10% |
| n_records | 72 |

## 2. Scenario Results — F1, ΔF1, and H3 Verdict

ΔF1 = F1_baseline − F1_scenario (paired, same 72 documents). H3 SUPPORTED iff CI upper < 0.15.

| Scenario | F1 | ΔF1 | 95% CI ΔF1 | SVR | H3 |
|---|---:|---:|---|---:|---|
| A1 — Informal register (LLM) | 0.6918 | -0.0076 | [-0.0268, 0.0081] | 0.00% | **SUPPORTED** |
| A2 — Code-switching (LLM) | 0.6786 | 0.0056 | [-0.0082, 0.0180] | 0.00% | **SUPPORTED** |
| A3 — Noise injection (rule-based, 7%) | 0.6771 | 0.0071 | [-0.0076, 0.0196] | 0.00% | **SUPPORTED** |
| A4 — Cross-lingual translation (LLM) | 0.6851 | -0.0010 | [-0.0164, 0.0138] | 0.00% | **SUPPORTED** |
| C1a — Truncation: headline-only | 0.6468 | 0.0374 | [0.0040, 0.0701] | 0.00% | **SUPPORTED** |
| C1b — Truncation: 25% of text | 0.6528 | 0.0313 | [0.0009, 0.0612] | 0.00% | **SUPPORTED** |
| C1c — Truncation: 50% of text | 0.6832 | 0.0009 | [-0.0190, 0.0217] | 0.00% | **SUPPORTED** |
| C2a — Sentence dropout: actor keywords | 0.6857 | -0.0016 | [-0.0141, 0.0104] | 1.39% | **SUPPORTED** |
| C2b — Sentence dropout: action keywords | 0.6635 | 0.0206 | [0.0056, 0.0367] | 0.00% | **SUPPORTED** |
| C2c — Sentence dropout: asset keywords | 0.6875 | -0.0034 | [-0.0196, 0.0133] | 0.00% | **SUPPORTED** |

### C3 — Short-Report Natural Cross-Check (no perturbation)

Bottom quartile (n=18, len≤1717 chars) vs top 3/4 (n=54):

| Subset | n | Mean F1 |
|---|---:|---:|
| Short reports (C3) | 18 | 0.7074 |
| Longer reports     | 54 | 0.6764 |

Δ(long−short) = -0.0310  95% CI = [-0.1259, 0.0696]
> C3 is a natural cross-check (not a perturbed scenario); delta is long-doc F1 minus short-doc F1 (positive = long docs score better). Not directly used for H3 verdict (no paired baseline-scenario comparison).

## 3. Scenario B — Class Imbalance

### B1 — Per-Dimension Macro vs Micro F1 Gap

Positive gap = macro > micro (model performs better on balanced per-class metric than on overall token counts; driven by small-class recall).

| Dimension | Type | Macro-F1 | Micro-F1 | Gap |
|---|---|---:|---:|---:|
| asset_category | single | 0.2654 | 0.7188 | -0.4534 |
| asset_variety | multi | 0.1331 | 0.5625 | -0.4402 |
| attr_conf_data_variety | multi | 0.3125 | 0.7418 | -0.4399 |
| attr_avail_present | single | 0.5489 | 0.8652 | -0.3164 |
| attr_conf_present | single | 0.6491 | 0.9489 | -0.2998 |
| action_variety | multi | 0.4129 | 0.6358 | -0.2930 |
| attr_conf_disclosure | single | 0.3227 | 0.1071 | 0.2156 |
| attr_integrity_variety | multi | 0.2875 | 0.4545 | -0.1887 |
| actor_variety | multi | 0.3785 | 0.5467 | -0.1718 |
| actor_motive | multi | 0.5730 | 0.7034 | -0.1353 |
| attr_avail_variety | multi | 0.2619 | 0.3158 | -0.0539 |
| action_category | single | 0.5172 | 0.5607 | -0.0435 |
| actor_category | single | 0.6279 | 0.6067 | 0.0212 |
| action_vector | multi | 0.6112 | 0.5714 | 0.0154 |
| attr_integrity_present | single | 0.5621 | 0.5488 | 0.0132 |

### B1 — Per-Class F1 + Support (single-label dimensions)

**actor_category** (macro-F1 incl-Unk=0.6279, excl-Unk=0.7737, acc=75.00%)

| Class | F1 | Precision | Recall | Support |
|---|---:|---:|---:|---:|
| External | 0.8545 | 0.7705 | 0.9592 | 49 |
| Unknown | 0.1905 | 0.4000 | 0.1250 | 16 |
| Internal | 0.8000 | 0.8000 | 0.8000 | 5 |
| Partner | 0.6667 | 1.0000 | 0.5000 | 2 |

**action_category** (macro-F1 incl-Unk=0.5172, excl-Unk=0.6465, acc=41.67%)

| Class | F1 | Precision | Recall | Support |
|---|---:|---:|---:|---:|
| Unknown | 0.0000 | 0.0000 | 0.0000 | 37 |
| Hacking | 0.5195 | 0.3571 | 0.9524 | 21 |
| Malware | 0.6667 | 0.8000 | 0.5714 | 7 |
| Misuse | 1.0000 | 1.0000 | 1.0000 | 4 |
| Error | 0.4000 | 0.2857 | 0.6667 | 3 |

**asset_category** (macro-F1 incl-Unk=0.2654, excl-Unk=0.3539, acc=63.89%)

| Class | F1 | Precision | Recall | Support |
|---|---:|---:|---:|---:|
| Server | 0.7759 | 0.6429 | 0.9783 | 46 |
| Unknown | 0.0000 | 0.0000 | 0.0000 | 19 |
| User Device | 0.2857 | 0.5000 | 0.2000 | 5 |
| Person | 0.0000 | 0.0000 | 0.0000 | 2 |

**attr_conf_present** (macro-F1 incl-Unk=0.6491, excl-Unk=0.9737, acc=90.28%)

| Class | F1 | Precision | Recall | Support |
|---|---:|---:|---:|---:|
| Yes | 0.9474 | 0.9000 | 1.0000 | 63 |
| Unknown | 0.0000 | 0.0000 | 0.0000 | 7 |
| No | 1.0000 | 1.0000 | 1.0000 | 2 |

**attr_integrity_present** (macro-F1 incl-Unk=0.5621, excl-Unk=0.7320, acc=81.94%)

| Class | F1 | Precision | Recall | Support |
|---|---:|---:|---:|---:|
| No | 0.8926 | 0.8060 | 1.0000 | 54 |
| Yes | 0.5714 | 1.0000 | 0.4000 | 10 |
| Unknown | 0.2222 | 1.0000 | 0.1250 | 8 |

**attr_avail_present** (macro-F1 incl-Unk=0.5489, excl-Unk=0.8233, acc=84.72%)

| Class | F1 | Precision | Recall | Support |
|---|---:|---:|---:|---:|
| No | 0.9194 | 0.8507 | 1.0000 | 57 |
| Unknown | 0.0000 | 0.0000 | 0.0000 | 8 |
| Yes | 0.7273 | 1.0000 | 0.5714 | 7 |

**attr_conf_disclosure** (macro-F1 incl-Unk=0.3227, excl-Unk=0.4033, acc=30.56%)

| Class | F1 | Precision | Recall | Support |
|---|---:|---:|---:|---:|
| Yes | 0.2712 | 1.0000 | 0.1569 | 51 |
| Potentially | 0.3421 | 0.2063 | 1.0000 | 13 |
|  | 0.0000 | 0.0000 | 0.0000 | 4 |
| Unknown | 0.0000 | 0.0000 | 0.0000 | 3 |
| No | 1.0000 | 1.0000 | 1.0000 | 1 |

### B2 — Rare-Class Stress Subset

Minority sectors: ['education_healthcare', 'telco']  
Rare action_variety values (count < 3): ['Defacement', 'Destroy data', 'Disable controls', 'Other', 'SQL injection (SQLi)', 'Spyware/Keylogger', 'Use of stolen creds']

| Subset | n | Mean F1 |
|---|---:|---:|
| Stress (minority sector + rare action) | 15 | 0.7022 |
| Majority | 57 | 0.6794 |

Δ(majority−stress) = -0.0228  
> B2 does not directly test H3 degradation as it compares subgroups within baseline, not baseline vs perturbed scenario.

### B3 — Sector Breakdown

| Sector | n | Mean F1 |
|---|---:|---:|
| government | 53 | 0.6712 |
| financial | 7 | 0.7739 |
| unknown | 5 | 0.6178 |
| education_healthcare | 4 | 0.6944 |
| telco | 3 | 0.8000 |

> government sector = 53/72 records (73.6%); macro-F1 is heavily weighted toward government incidents (KPU, PDNS, BSSN, PDN). Other sectors are too small for reliable per-sector inference (n<8).

## 4. Statistical Tests

**Bonferroni correction:** 150 McNemar comparisons, α_adj = 0.00033, reject raw (α=0.05): 3, reject Bonferroni: 0.

### McNemar Test per Dimension (selected scenarios)

Rows = VERIS dimensions (binarised: F1≥0.5 = correct). b = baseline-correct/scenario-wrong, c = baseline-wrong/scenario-correct. Significant at Bonferroni-corrected α indicates a dimension significantly changed between baseline and scenario.

| Dimension | A1 p | A2 p | A3 p | A4 p | C1_headline p | C1_25pct p | C1_50pct p | C2_actor p | C2_action p | C2_asset p |
|---|---|---|---|---|---|---|---|---|---|---|
| actor_category | 0.4795 | 1.0000 | 1.0000 | 1.0000 | 0.1213 | 0.0265 | 0.6831 | 1.0000 | 1.0000 | 1.0000 |
| action_category | 0.4795 | 1.0000 | 1.0000 | 0.4795 | 0.0455 | 0.0736 | 1.0000 | 1.0000 | 0.4795 | 1.0000 |
| asset_category | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4795 | 1.0000 | 1.0000 | 0.4795 |
| attr_conf_present | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| attr_integrity_present | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.2207 | 0.6171 | 0.4795 | 1.0000 | 1.0000 | 0.4795 |
| attr_avail_present | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| attr_conf_disclosure | 0.4795 | 0.2482 | 0.4795 | 0.1336 | 0.7518 | 1.0000 | 0.2482 | 1.0000 | 1.0000 | 1.0000 |
| actor_variety | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3827 | 0.4533 | 1.0000 | 0.6171 | 0.5465 | 0.4795 |
| actor_motive | 0.6171 | 1.0000 | 1.0000 | 1.0000 | 0.0159 | 0.2888 | 0.6831 | 0.6171 | 1.0000 | 1.0000 |
| action_variety | 1.0000 | 1.0000 | 0.4497 | 0.6056 | 0.2864 | 0.2386 | 0.6276 | 0.7518 | 0.1489 | 0.3865 |
| action_vector | 0.3865 | 0.5791 | 0.2888 | 1.0000 | 1.0000 | 1.0000 | 0.7003 | 1.0000 | 0.0614 | 1.0000 |
| asset_variety | 0.4795 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4795 | 1.0000 | 0.4795 | 1.0000 |
| attr_conf_data_variety | 1.0000 | 0.3711 | 1.0000 | 1.0000 | 0.6171 | 0.2207 | 1.0000 | 0.4795 | 0.4795 | 1.0000 |
| attr_integrity_variety | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4795 | 1.0000 | 1.0000 |
| attr_avail_variety | 0.4795 | 1.0000 | 1.0000 | 0.4795 | 1.0000 | 0.4795 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

\* = significant after Bonferroni correction.

## 5. H3 Verdicts

**Aggregate:** SUPPORTED (10/10 scenarios: CI upper < 0.15)

| Scenario | ΔF1 CI upper | H3 |
|---|---:|---|
| A1 — Informal register (LLM) | 0.0081 | **SUPPORTED** |
| A2 — Code-switching (LLM) | 0.0180 | **SUPPORTED** |
| A3 — Noise injection (rule-based, 7%) | 0.0196 | **SUPPORTED** |
| A4 — Cross-lingual translation (LLM) | 0.0138 | **SUPPORTED** |
| C1a — Truncation: headline-only | 0.0701 | **SUPPORTED** |
| C1b — Truncation: 25% of text | 0.0612 | **SUPPORTED** |
| C1c — Truncation: 50% of text | 0.0217 | **SUPPORTED** |
| C2a — Sentence dropout: actor keywords | 0.0104 | **SUPPORTED** |
| C2b — Sentence dropout: action keywords | 0.0367 | **SUPPORTED** |
| C2c — Sentence dropout: asset keywords | 0.0133 | **SUPPORTED** |

*H3 SUPPORTED iff CI upper < 0.15.*

