# Baselines and prior-aware evaluation

Reference implementations of the three baselines reported in the ARTMAN 2026
paper, plus the scoring and diagnostic scripts used to produce its tables.

Every script resolves its inputs relative to the repository root, so they run
from a clean clone with no path editing:

```bash
pip install -r requirements.txt
python baselines/baselines.py
```

## Scripts

| Script | What it computes |
|---|---|
| `baselines.py` | B0a oracle majority-class, B0b leave-one-out majority-class, B1 stratified-random (200 draws), the framework for comparison, the empty-vs-empty-excluded variant of every figure, the per-dimension table, and the gold label skew that explains why a constant predictor is strong |
| `rulebased.py` | B2, a non-LLM Indonesian/English keyword lexicon mapped onto the VERIS A4 controlled vocabulary, with a fall-back to the training prior when no cue fires |
| `baseline_robustness.py` | Degradation of the constant predictor and of the framework across all ten RQ3 perturbation scenarios |
| `score.py` | Single-scenario scorer, used to verify that the RQ3 pipeline's stored scores are reproducible |
| `summary.py` | Per-dimension gold entropy, top-class share and framework-minus-majority delta; writes `perdim.json` |
| `metric_definitions.py` | The baseline comparison under five aggregate definitions for B0, v3, v2 and v1 (Table 4 of the paper), and the oracle-abstention counterfactual (0.6841 to 0.8726) |
| `incident_overlap.py` | Incident-level overlap between the six few-shot exemplars and the evaluation set (18 of 72 records), and the score of B0 and the pipeline on each side of it |

## Expected output

On the adjudicated gold standard (n = 72), macro-F1 as the per-record mean over
the fifteen dimensions with empty-vs-empty scored as 1:

| Predictor | macro-F1 | 95% CI |
|---|---:|---|
| B0a oracle majority-class | 0.7000 | [0.6528, 0.7460] |
| B0b leave-one-out majority-class | 0.7000 | [0.6528, 0.7460] |
| Framework, v3 few-shot | 0.6841 | [0.6443, 0.7233] |
| B2 rule-based lexicon | 0.5770 | [0.5391, 0.6126] |
| B1 stratified-random, 200 draws | 0.5517 | sd 0.0126 |

The framework beats the constant predictor on 10 of 15 dimensions and loses
overall. The constant predictor shows exactly zero degradation in all ten
perturbation scenarios, because its output does not depend on the input.

Confidence intervals come from 10,000 bootstrap resamples over records with a
fixed seed, so the figures above are byte-stable across runs.

Further expected values:

| Script | Expected |
|---|---|
| `metric_definitions.py` | B0 beats every configuration under three of five definitions; oracle abstention 0.8726 (+0.1884) |
| `incident_overlap.py` | pipeline 0.6883 on the 18 overlapping records and 0.6828 on the other 54; on those 54, B0 leads by 0.0470, 95% CI [0.0003, 0.0872] |
