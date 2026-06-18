#!/usr/bin/env bash
# RQ3 full pipeline driver.
# Run from /workspace/Thesis-gpu.
# Logs to rq3/rq3_run_all.log (tee to stdout).
# Idempotent: existing predictions are skipped via --resume.
#
# Estimated time:
#   Rule-based perturbations (A3, C*): instant
#   LLM perturbations (A1, A2, A4): ~30-40 min each
#   Extractions (all 10 scenarios × 72 records): ~30-40 min each
#   Analysis + stats: instant
#   TOTAL: ~8-12 hours (run overnight)

set -euo pipefail
LOG="rq3/rq3_run_all.log"
PY=python3

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== RQ3 PIPELINE START ==="

# -------- Task 0: Baseline (fast) --------
log "Task 0: Baseline scoring"
$PY rq3_baseline.py 2>&1 | tee -a "$LOG"

# -------- Scenario B: Imbalance (fast, no LLM) --------
log "Scenario B: Class imbalance analysis"
$PY rq3_analyze_B.py 2>&1 | tee -a "$LOG"

# -------- Rule-based perturbations (fast) --------
log "Rule-based perturbations: A3, C1*, C2*"
$PY rq3_perturb_rulebased.py --all 2>&1 | tee -a "$LOG"

# -------- Extractions: rule-based scenarios --------
log "Extraction: A3 (noise)"
$PY rq3_extract_scenario.py --scenario A3 --resume 2>&1 | tee -a "$LOG"

log "Extraction: C1_headline"
$PY rq3_extract_scenario.py --scenario C1_headline 2>&1 | tee -a "$LOG"

log "Extraction: C1_25pct"
$PY rq3_extract_scenario.py --scenario C1_25pct 2>&1 | tee -a "$LOG"

log "Extraction: C1_50pct"
$PY rq3_extract_scenario.py --scenario C1_50pct 2>&1 | tee -a "$LOG"

log "Extraction: C2_actor"
$PY rq3_extract_scenario.py --scenario C2_actor 2>&1 | tee -a "$LOG"

log "Extraction: C2_action"
$PY rq3_extract_scenario.py --scenario C2_action 2>&1 | tee -a "$LOG"

log "Extraction: C2_asset"
$PY rq3_extract_scenario.py --scenario C2_asset 2>&1 | tee -a "$LOG"

# -------- LLM perturbations (slow: ~30-40 min each) --------
log "LLM perturbation: A1 (informal register)"
$PY rq3_perturb_llm.py --scenario A1 2>&1 | tee -a "$LOG"

log "Extraction: A1"
$PY rq3_extract_scenario.py --scenario A1 2>&1 | tee -a "$LOG"

log "LLM perturbation: A2 (code-switching)"
$PY rq3_perturb_llm.py --scenario A2 2>&1 | tee -a "$LOG"

log "Extraction: A2"
$PY rq3_extract_scenario.py --scenario A2 2>&1 | tee -a "$LOG"

log "LLM perturbation: A4 (translation)"
$PY rq3_perturb_llm.py --scenario A4 2>&1 | tee -a "$LOG"

log "Extraction: A4"
$PY rq3_extract_scenario.py --scenario A4 2>&1 | tee -a "$LOG"

# -------- Score all available scenarios --------
log "Scoring all scenarios"
$PY rq3_score_scenario.py --all 2>&1 | tee -a "$LOG"

# -------- Statistical tests --------
log "Statistical analysis (paired bootstrap, McNemar, Bonferroni)"
$PY rq3_stats.py 2>&1 | tee -a "$LOG"

# -------- Summary report --------
log "Generating rq3_summary.md"
$PY rq3_summary_gen.py 2>&1 | tee -a "$LOG"

log "=== RQ3 PIPELINE COMPLETE ==="
log "Outputs:"
ls rq3/*.json rq3/*.md 2>/dev/null | while read f; do log "  $f"; done
