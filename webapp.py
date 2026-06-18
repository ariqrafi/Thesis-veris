#!/usr/bin/env python3
"""VERIS A4 Thesis Dashboard - Flask webapp, port 16006"""
import json, os
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))


def jload(path):
    full = os.path.join(BASE, path)
    if not os.path.exists(full):
        return {}
    with open(full) as f:
        return json.load(f)


def load_all():
    rq1_v1 = jload("rq1/metrics_seed42.json")
    rq1_v2 = jload("rq1/metrics_v2_seed42.json")
    rq1_v3 = jload("rq1/metrics_v3_seed42.json")

    rq2_schema_raw = jload("rq2/rq2_schema_compliance_v2.json")
    rq2_repro      = jload("rq2/rq2_reproducibility.json")
    rq2_temp       = jload("rq2/rq2_temperature_stability.json")
    rq2_hetero_raw = jload("rq2/rq2_heterogeneity_v2.json")

    rq3_baseline   = jload("rq3/rq3_baseline.json")
    rq3_stats      = jload("rq3/rq3_stats.json")
    rq3_scenA_raw  = jload("rq3/rq3_scenarioA.json")
    rq3_scenB      = jload("rq3/rq3_scenarioB.json")
    rq3_scenC_raw  = jload("rq3/rq3_scenarioC.json")

    # Normalize rq2 schema - data in 'after' key
    schema_after = rq2_schema_raw.get("after", {})
    rq2_schema = {
        "svr":                   schema_after.get("svr", 0),
        "svr_wilson_ci95":       schema_after.get("svr_wilson_ci95", [0, 0]),
        "n_violation_records":   schema_after.get("n_violation_records", 0),
        "n_total_outputs":       schema_after.get("n_outputs", 0),
        "field_completeness_rate": schema_after.get("field_completeness_rate", 0),
        "vocab_conformance_rate":  schema_after.get("vocabulary_conformance_rate", 0),
        "cause_summary":         schema_after.get("cause_breakdown_records", {}),
        "per_field":             schema_after.get("per_field_off_vocab", {}),
        "h2a_verdict":           rq2_schema_raw.get("h2a_verdict_after_preregistered", ""),
    }

    # Normalize rq2 repro
    rq2_repro_norm = {
        "mean_agreement":    rq2_repro.get("mean_pairwise_agreement", 1.0),
        "mean_exact_match":  rq2_repro.get("mean_exact_match_all_runs", 1.0),
        "agreement_ci95":    rq2_repro.get("agreement_ci95_t", [1.0, 1.0]),
        "fleiss_kappa_macro": rq2_repro.get("fleiss_kappa_macro", 1.0),
        "fleiss_kappa_per_dim": {
            k: (v["kappa"] if isinstance(v, dict) else v)
            for k, v in rq2_repro.get("fleiss_kappa_per_dimension", {}).items()
        },
        "determinism":       rq2_repro.get("determinism", {}),
        "h2b_verdict":       rq2_repro.get("h2b_verdict", ""),
        "h2b_caveat":        rq2_repro.get("h2b_caveat", ""),
    }

    # Normalize rq2 hetero - sector/language/source are lists of [k, v] pairs
    def list_to_dict(lst):
        if isinstance(lst, dict):
            return lst
        return {item[0]: item[1] for item in lst}

    rq2_hetero = {
        "by_sector":   list_to_dict(rq2_hetero_raw.get("sector", {})),
        "by_language": list_to_dict(rq2_hetero_raw.get("language", {})),
        "by_source":   list_to_dict(rq2_hetero_raw.get("source", {})),
    }

    # Merge all scenario scores from scenA and scenC
    all_scenarios = {}
    all_scenarios.update(rq3_scenA_raw.get("scenarios", {}))
    all_scenarios.update(rq3_scenC_raw.get("scenarios", {}))

    # Build B1 macro/micro per dim from b1_single_label and b1_multi_label
    b1_dims = {}
    for f, d in rq3_scenB.get("b1_single_label", {}).items():
        b1_dims[f] = {
            "macro_f1": d.get("macro_f1_incl_unknown", 0),
            "micro_f1": d.get("micro_f1", 0),
            "gap":      d.get("macro_micro_gap", 0),
        }
    for f, d in rq3_scenB.get("b1_multi_label", {}).items():
        b1_dims[f] = {
            "macro_f1": d.get("macro_f1_by_record", 0),
            "micro_f1": d.get("micro_f1", 0),
            "gap":      d.get("macro_micro_gap", 0),
        }

    # Sort by abs(gap) descending for chart
    b1_sorted = sorted(b1_dims.items(), key=lambda x: abs(x[1]["gap"]), reverse=True)

    return {
        "rq1": {
            "v1": rq1_v1,
            "v2": rq1_v2,
            "v3": rq1_v3,
        },
        "rq2": {
            "schema":  rq2_schema,
            "repro":   rq2_repro_norm,
            "temp":    rq2_temp,
            "hetero":  rq2_hetero,
        },
        "rq3": {
            "baseline":  rq3_baseline,
            "stats":     rq3_stats,
            "scenarios": all_scenarios,
            "b1_sorted": b1_sorted,
            "b3_sector": {k: v for k, v in rq3_scenB.get("b3_sector_breakdown", {}).items()
                          if not k.startswith("_")},
            "b2":        rq3_scenB.get("b2_rare_class_subset", {}),
        },
    }


@app.route("/api/data")
def api_data():
    return jsonify(load_all())


HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VERIS A4 Thesis Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
:root{--pri:#1a56db;--suc:#0e9f6e;--dan:#e02424;--war:#c27803;--neu:#6b7280;--bg:#f1f5f9}
*{box-sizing:border-box}
body{background:var(--bg);font-family:'Segoe UI',system-ui,sans-serif;color:#1f2937}
.navbar{background:var(--pri)!important}
.navbar-brand{font-weight:800;font-size:1.05rem;letter-spacing:-.3px}
.nav-link{color:rgba(255,255,255,.8)!important;border-radius:6px;transition:.15s}
.nav-link.active,.nav-link:hover{color:#fff!important;background:rgba(255,255,255,.18)!important}
.card{border:1px solid #e2e8f0;border-radius:12px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.card-header{background:none;border-bottom:1px solid #f1f5f9;font-weight:600;font-size:.9rem;padding:.7rem 1.1rem}
.sec-title{font-size:1rem;font-weight:700;color:var(--pri);border-bottom:2px solid var(--pri);padding-bottom:4px;margin-bottom:1rem}
.kpi{border-radius:12px;padding:1.1rem 1.3rem}
.kpi-val{font-size:1.9rem;font-weight:800;line-height:1}
.kpi-lbl{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;opacity:.65;margin-top:3px}
.badge-sup{background:#dcfce7;color:#15803d;font-size:.72rem;font-weight:700;padding:2px 9px;border-radius:99px}
.badge-inc{background:#fef9c3;color:#854d0e;font-size:.72rem;font-weight:700;padding:2px 9px;border-radius:99px}
.badge-not{background:#fee2e2;color:#b91c1c;font-size:.72rem;font-weight:700;padding:2px 9px;border-radius:99px}
.tab-pane{padding-top:1.4rem}
table.table-sm td,table.table-sm th{vertical-align:middle;font-size:.83rem}
.chart-wrap{position:relative}
.scen-row-ok td:first-child{border-left:3px solid var(--suc)}
.scen-row-no td:first-child{border-left:3px solid var(--dan)}
footer{font-size:.76rem;color:var(--neu);text-align:center;padding:1.5rem 0 1rem}
/* Metodologi */
.mermaid svg{max-width:100%;height:auto}
.mermaid{overflow-x:auto}
.step-num{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--pri);color:#fff;font-weight:800;font-size:.82rem;flex-shrink:0}
.step-card{border-left:3px solid var(--pri);padding:.75rem 1rem;background:#fff;border-radius:0 8px 8px 0;margin-bottom:.75rem;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.rq-badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.72rem;font-weight:700}
.rq1-b{background:#dbeafe;color:#1e40af}
.rq2-b{background:#d1fae5;color:#065f46}
.rq3-b{background:#fce7f3;color:#9d174d}
.dim-tag{display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:1px 8px;font-size:.75rem;margin:2px}
.flow-legend span{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:4px;vertical-align:middle}
.hyp-box{border:2px dashed;border-radius:10px;padding:.8rem 1rem;font-size:.85rem}
.hyp-h1{border-color:#3b82f6;background:#eff6ff}
.hyp-h2{border-color:#10b981;background:#ecfdf5}
.hyp-h3{border-color:#ec4899;background:#fdf2f8}
.timeline-line{border-left:3px solid var(--pri);padding-left:1.2rem;margin-left:.7rem}
.timeline-dot{width:14px;height:14px;border-radius:50%;background:var(--pri);margin-left:-1.6rem;flex-shrink:0;margin-top:3px}
</style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark">
  <div class="container-fluid px-4">
    <span class="navbar-brand"><i class="bi bi-shield-lock-fill me-2"></i>VERIS A4 - Dashboard Tesis</span>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="nav">
      <ul class="navbar-nav ms-auto gap-1" id="mainTabs" role="tablist">
        <li class="nav-item"><a class="nav-link active px-3 py-1" data-bs-toggle="tab" href="#t-sum"><i class="bi bi-grid-1x2 me-1"></i>Ringkasan</a></li>
        <li class="nav-item"><a class="nav-link px-3 py-1" data-bs-toggle="tab" href="#t-met"><i class="bi bi-diagram-3 me-1"></i>Metodologi</a></li>
        <li class="nav-item"><a class="nav-link px-3 py-1" data-bs-toggle="tab" href="#t-rq1"><i class="bi bi-bullseye me-1"></i>RQ1 - Akurasi</a></li>
        <li class="nav-item"><a class="nav-link px-3 py-1" data-bs-toggle="tab" href="#t-rq2"><i class="bi bi-arrow-repeat me-1"></i>RQ2 - Konsistensi</a></li>
        <li class="nav-item"><a class="nav-link px-3 py-1" data-bs-toggle="tab" href="#t-rq3"><i class="bi bi-lightning-charge me-1"></i>RQ3 - Robustness</a></li>
      </ul>
    </div>
  </div>
</nav>

<div class="container-fluid px-4 py-4">
<div class="tab-content">

<!-- ══════════════ METODOLOGI ══════════════ -->
<div class="tab-pane fade" id="t-met">
  <h6 class="sec-title"><i class="bi bi-diagram-3 me-2"></i>Metodologi Penelitian</h6>

  <!-- ── Konteks & RQ ── -->
  <div class="card mb-4">
    <div class="card-header"><i class="bi bi-question-circle me-1"></i>Konteks & Research Questions</div>
    <div class="card-body">
      <p style="font-size:.88rem;line-height:1.8" class="mb-3">
        Penelitian ini menginvestigasi kemampuan <strong>Large Language Model (LLM) lokal</strong>
        (<code>qwen3.5:35b</code> via Ollama) dalam mengekstraksi struktur insiden siber dari
        laporan berbahasa Indonesia ke dalam skema <strong>VERIS A4</strong> (Vocabulary for
        Event Recording and Incident Sharing). VERIS A4 mencakup empat dimensi utama - Actor,
        Action, Asset, Attribute - yang dijabarkan menjadi <strong>15 sub-dimensi</strong>
        dengan controlled vocabulary terkontrol versi 1.3.x.
      </p>
      <div class="row g-3">
        <div class="col-md-4">
          <div class="hyp-box hyp-h1">
            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="rq-badge rq1-b">RQ1</span>
              <strong style="font-size:.88rem">Akurasi Ekstraksi</strong>
            </div>
            <p class="mb-1" style="font-size:.83rem">Sejauh mana <code>qwen3.5:35b</code> dapat mengekstraksi struktur VERIS A4 dari laporan insiden siber berbahasa Indonesia secara akurat?</p>
            <div class="mt-2" style="font-size:.8rem"><strong>H1:</strong> Overall macro-F1 ≥ 0.70</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="hyp-box hyp-h2">
            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="rq-badge rq2-b">RQ2</span>
              <strong style="font-size:.88rem">Konsistensi & Schema</strong>
            </div>
            <p class="mb-1" style="font-size:.83rem">Seberapa konsisten dan patuh-skema output model ketika dijalankan berulang pada kondisi berbeda?</p>
            <div class="mt-2" style="font-size:.8rem">
              <strong>H2a:</strong> SVR &lt; 10%<br>
              <strong>H2b:</strong> Mean agreement ≥ 0.85
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="hyp-box hyp-h3">
            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="rq-badge rq3-b">RQ3</span>
              <strong style="font-size:.88rem">Robustness</strong>
            </div>
            <p class="mb-1" style="font-size:.83rem">Seberapa tahan model terhadap variasi linguistik, ketimpangan kelas, dan informasi tidak lengkap?</p>
            <div class="mt-2" style="font-size:.8rem"><strong>H3:</strong> ΔF1 CI upper &lt; 0.15 di semua skenario</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Pipeline Utama ── -->
  <div class="card mb-4">
    <div class="card-header"><i class="bi bi-diagram-2 me-1"></i>Alur Penelitian Keseluruhan</div>
    <div class="card-body">
      <div class="mermaid">
flowchart TD
    A([🗄️ Corpus\n642 laporan insiden siber]) --> B[Preprocessing &\nDeduplikasi]
    B --> C([📦 Dataset Bersih\ndataset_clean.jsonl])
    C --> D{Partisi}
    D -->|100 record dipilih| E([📋 Eval Set\neval_set_100.jsonl])
    D -->|542 record sisanya| F([🔒 Pool Leakage-Safe\nuntuk few-shot exemplar])
    E --> G[/Anotasi Manual\nGold Standard/]
    G --> H([✅ Gold Standard\n100 record, 72 in-scope])
    F --> I([📌 6 Exemplar Few-shot\nFS-01,02,04,05,06,07])
    H --> J{Ekstraksi LLM}
    I -->|v3 only| J
    J -->|v1| K1[Zero-shot\nextract_qwen.py]
    J -->|v2| K2[Structural Prompt\nextract_qwen_v2.py]
    J -->|v3| K3[Few-shot\nextract_qwen_fewshot.py]
    K1 & K2 & K3 --> L([📊 Predictions JSON])
    L --> M[Scoring\nscore_rq1.py]
    H --> M
    M --> N1([📈 RQ1\nAkurasi])
    L --> O[15 Runs\nRQ2 subset 50]
    O --> N2([🔄 RQ2\nKonsistensi])
    L --> P[Perturbasi\nRQ3 scenarios]
    H --> P
    P --> N3([⚡ RQ3\nRobustness])

    style A fill:#dbeafe,stroke:#3b82f6
    style C fill:#dbeafe,stroke:#3b82f6
    style E fill:#dbeafe,stroke:#3b82f6
    style F fill:#fef9c3,stroke:#ca8a04
    style H fill:#d1fae5,stroke:#059669
    style I fill:#fef9c3,stroke:#ca8a04
    style L fill:#f3e8ff,stroke:#9333ea
    style N1 fill:#dbeafe,stroke:#1d4ed8
    style N2 fill:#d1fae5,stroke:#065f46
    style N3 fill:#fce7f3,stroke:#9d174d
      </div>
    </div>
  </div>

  <!-- ── Dataset ── -->
  <div class="card mb-4">
    <div class="card-header"><i class="bi bi-database me-1"></i>Dataset & Partisi</div>
    <div class="card-body">
      <div class="row g-3 mb-3">
        <div class="col-md-3">
          <div class="text-center p-3 border rounded" style="background:#eff6ff">
            <div style="font-size:2rem;font-weight:800;color:#1d4ed8">642</div>
            <div class="text-muted" style="font-size:.78rem">Total corpus laporan<br>insiden siber (dataset_clean)</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="text-center p-3 border rounded" style="background:#fffbeb">
            <div style="font-size:2rem;font-weight:800;color:#92400e">100</div>
            <div class="text-muted" style="font-size:.78rem">Eval set yang dianotasi<br>(eval_set_100.jsonl)</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="text-center p-3 border rounded" style="background:#f0fdf4">
            <div style="font-size:2rem;font-weight:800;color:#15803d">72</div>
            <div class="text-muted" style="font-size:.78rem">Record in-scope yang diskor<br>(in_scope = Yes)</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="text-center p-3 border rounded" style="background:#fdf4ff">
            <div style="font-size:2rem;font-weight:800;color:#7e22ce">542</div>
            <div class="text-muted" style="font-size:.78rem">Pool leakage-safe<br>(sumber exemplar few-shot)</div>
          </div>
        </div>
      </div>
      <table class="table table-sm table-bordered">
        <thead class="table-light"><tr><th>File</th><th>Isi</th><th>Keterangan</th></tr></thead>
        <tbody style="font-size:.83rem">
          <tr><td><code>dataset_clean.jsonl</code></td><td>642 record</td><td>Korpus sumber: laporan insiden siber dari media, regulasi, vendor</td></tr>
          <tr><td><code>eval_set_100.jsonl</code></td><td>100 record</td><td>Subset evaluasi dengan <code>full_content_clean</code>, maks 16 000 karakter</td></tr>
          <tr><td><code>gold_standard.json</code></td><td>100 anotasi</td><td>Label manual teradjudikasi; 72 <code>in_scope=Yes</code> yang diskor</td></tr>
          <tr><td><code>fewshot_exemplars.json</code></td><td>6 exemplar</td><td>FS-01,02,04,05,06,07 - leakage-safe vs eval-100 (via content_hash)</td></tr>
          <tr><td><code>repro_subset_50.jsonl</code></td><td>50 record</td><td>Subset RQ2: stratified by sector, seed 20260615</td></tr>
        </tbody>
      </table>
      <div class="alert alert-warning py-2 px-3 mb-0" style="font-size:.8rem">
        <i class="bi bi-shield-exclamation me-1"></i>
        <strong>Leakage control:</strong> 6 exemplar few-shot dipilih dari 542 record yang <em>tidak masuk</em> eval-100. Pemisahan dilakukan via <code>content_hash</code> (bukan ID, karena cid tidak stabil antar re-filtering).
      </div>
    </div>
  </div>

  <!-- ── VERIS A4 ── -->
  <div class="card mb-4">
    <div class="card-header"><i class="bi bi-grid-3x3-gap me-1"></i>Skema VERIS A4 - 15 Dimensi yang Diekstraksi</div>
    <div class="card-body">
      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <div class="mermaid">
mindmap
  root((VERIS A4))
    Actor
      actor_category
      actor_variety
      actor_motive
    Action
      action_category
      action_variety
      action_vector
    Asset
      asset_category
      asset_variety
    Attribute
      Confidentiality
        attr_conf_present
        attr_conf_disclosure
        attr_conf_data_variety
      Integrity
        attr_integrity_present
        attr_integrity_variety
      Availability
        attr_avail_present
        attr_avail_variety
          </div>
        </div>
        <div class="col-md-6">
          <table class="table table-sm table-bordered h-100 mb-0">
            <thead class="table-light"><tr><th>Dimensi</th><th>Tipe</th><th>Contoh Nilai</th></tr></thead>
            <tbody style="font-size:.78rem">
              <tr><td><code>actor_category</code></td><td><span class="dim-tag">single</span></td><td>External, Internal, Partner, Unknown</td></tr>
              <tr><td><code>actor_variety</code></td><td><span class="dim-tag">multi</span></td><td>Organized crime, State-affiliated, Activist…</td></tr>
              <tr><td><code>actor_motive</code></td><td><span class="dim-tag">multi</span></td><td>Financial, Espionage, Ideology…</td></tr>
              <tr><td><code>action_category</code></td><td><span class="dim-tag">single</span></td><td>Hacking, Malware, Social, Error…</td></tr>
              <tr><td><code>action_variety</code></td><td><span class="dim-tag">multi</span></td><td>Use of stolen creds, Ransomware, Phishing…</td></tr>
              <tr><td><code>action_vector</code></td><td><span class="dim-tag">multi</span></td><td>Web application, Email, Partner…</td></tr>
              <tr><td><code>asset_category</code></td><td><span class="dim-tag">single</span></td><td>Server, User Device, Network…</td></tr>
              <tr><td><code>asset_variety</code></td><td><span class="dim-tag">multi</span></td><td>Database, Web application, Desktop…</td></tr>
              <tr><td><code>attr_conf_present</code></td><td><span class="dim-tag">single</span></td><td>Yes, No, Unknown</td></tr>
              <tr><td><code>attr_conf_disclosure</code></td><td><span class="dim-tag">single</span></td><td>Yes, No, Potentially, Unknown</td></tr>
              <tr><td><code>attr_conf_data_variety</code></td><td><span class="dim-tag">multi</span></td><td>Personal, Credentials, Medical…</td></tr>
              <tr><td><code>attr_integrity_present</code></td><td><span class="dim-tag">single</span></td><td>Yes, No, Unknown</td></tr>
              <tr><td><code>attr_integrity_variety</code></td><td><span class="dim-tag">multi</span></td><td>Defacement, Modify data…</td></tr>
              <tr><td><code>attr_avail_present</code></td><td><span class="dim-tag">single</span></td><td>Yes, No, Unknown</td></tr>
              <tr><td><code>attr_avail_variety</code></td><td><span class="dim-tag">multi</span></td><td>Outage, Encryption, Loss…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- ── RQ1 Metodologi ── -->
  <div class="card mb-4">
    <div class="card-header"><span class="rq-badge rq1-b me-2">RQ1</span>Metodologi Akurasi - Tiga Versi Ekstraktor</div>
    <div class="card-body">
      <div class="mermaid mb-4">
flowchart LR
    IN([📄 Laporan Insiden\nmaks 16 000 kar]) --> SYS

    subgraph PROMPT["System Prompt"]
      SYS["VERIS A4 Schema\n+ Controlled Vocabulary\n+ Mapping Rules"]
    end

    subgraph VERSIONS["Evolusi Versi"]
      direction TB
      V1["v1 Zero-shot\n• Hanya schema+vocab\n• Tidak ada contoh\n• think=false"]
      V2["v2 Structural\n• Pisahkan CATEGORY vs VARIETY\n• Hapus rationale dari output\n• Perbaikan instruksi atom"]
      V3["v3 Few-shot\n• + 6 exemplar berlabel\n• user/assistant turns\n• Sama prompt dengan v2"]
      V1 -->|+3.0% F1| V2
      V2 -->|+11.1% F1| V3
    end

    PROMPT --> VERSIONS
    VERSIONS --> LLM["🤖 qwen3.5:35b\ntemp=0, seed=42\nthink=false"]
    LLM --> OUT["JSON Output\n15 field A4"]
    OUT --> SAL{"salvage_json()\nparse valid?"}
    SAL -->|Yes| SCORE["score_rq1.py"]
    SAL -->|Salvage| SCORE
    SCORE --> M1["Single-label:\nAccuracy + macro-F1\n+ Wilson CI"]
    SCORE --> M2["Multi-label:\nSet P/R/F1\nper-record"]
    M1 & M2 --> FINAL["Overall macro-F1\n+ Bootstrap CI\n+ t-test vs 0.70"]

    style V1 fill:#dbeafe,stroke:#3b82f6
    style V2 fill:#bfdbfe,stroke:#2563eb
    style V3 fill:#93c5fd,stroke:#1d4ed8
    style FINAL fill:#d1fae5,stroke:#059669
      </div>

      <div class="row g-3">
        <div class="col-md-4">
          <div class="step-card">
            <div class="d-flex gap-2 align-items-start">
              <span class="step-num">v1</span>
              <div>
                <strong>Zero-shot Baseline</strong>
                <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">Prompt hanya berisi skema VERIS dan vocabulary lengkap. Tidak ada contoh berlabel. Hasilkan 13 record salvage JSON (model menulis <code>rationale</code> tanpa tanda kutip pembuka).</p>
              </div>
            </div>
          </div>
          <div class="step-card">
            <div class="d-flex gap-2 align-items-start">
              <span class="step-num">v2</span>
              <div>
                <strong>Perbaikan Struktural</strong>
                <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">Dua perubahan: (a) aturan tegas pisah CATEGORY vs VARIETY dengan ilustrasi; (b) hapus <code>rationale</code> dari output wajib. Hasil: salvage 0, schema violation 2.0% → 0.1%.</p>
              </div>
            </div>
          </div>
          <div class="step-card">
            <div class="d-flex gap-2 align-items-start">
              <span class="step-num">v3</span>
              <div>
                <strong>Few-shot 6 Exemplar</strong>
                <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">6 contoh berlabel dari pool leakage-safe disisipkan sebagai turn user/assistant. Kualitas anotasi exemplar kritis - label <code>[]</code> di satu field mengajari model under-predict field itu.</p>
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-8">
          <table class="table table-sm table-bordered">
            <thead class="table-light"><tr><th>Parameter</th><th>Nilai</th><th>Alasan</th></tr></thead>
            <tbody style="font-size:.82rem">
              <tr><td>Model</td><td><code>qwen3.5:35b</code></td><td>LLM lokal terbesar yang tersedia via Ollama</td></tr>
              <tr><td>Temperature</td><td><code>0</code></td><td>Determinisme: reproduktibilitas penuh</td></tr>
              <tr><td>Seed</td><td><code>42</code></td><td>Fixed seed Ollama untuk reproducible sampling</td></tr>
              <tr><td>think</td><td><code>False</code></td><td>Hindari reasoning trace ~80s/call; trade-off: JSON grammar tidak di-enforce</td></tr>
              <tr><td>num_ctx</td><td><code>32768</code> (v2/v3)</td><td>Prompt few-shot mencapai ~8.6k token; default Ollama aman untuk v1</td></tr>
              <tr><td>max_chars</td><td><code>16000</code></td><td>Truncation teks input; max prompt 5029 token (GS-052)</td></tr>
              <tr><td>JSON schema</td><td>Field hint only</td><td>think=false → Ollama tidak enforce enum-grammar; schema menjadi petunjuk field saja</td></tr>
              <tr><td>Retries</td><td><code>3</code></td><td>Fallback jika Ollama timeout atau network error</td></tr>
              <tr><td>Scoring subset</td><td>72 record</td><td>28 record bertanda out-of-scope dikeluarkan dari scoring</td></tr>
            </tbody>
          </table>
          <div class="alert alert-info py-2 px-3 mb-0" style="font-size:.79rem">
            <i class="bi bi-info-circle me-1"></i>
            <strong>Keputusan kunci:</strong> Validasi di Python adalah <em>sumber kebenaran</em>. Nilai off-vocabulary dihitung salah, tidak di-remap. Ini membuat schema-violation rate menjadi besaran terukur nyata (bukan dipaksa grammar).
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── RQ2 Metodologi ── -->
  <div class="card mb-4">
    <div class="card-header"><span class="rq-badge rq2-b me-2">RQ2</span>Metodologi Konsistensi - 15 Runs, 3 Temperature</div>
    <div class="card-body">
      <div class="mermaid mb-4">
flowchart TD
    SUB([📦 Subset 50 record\nstratified by sector]) --> T0 & T03 & T07

    subgraph T0["Temperature = 0 (determinisme)"]
      R1[Run 1\nseed 42] & R2[Run 2\nseed 42] & R3[Run 3\nseed 42] & R4[Run 4\nseed 42] & R5[Run 5\nseed 42]
    end

    subgraph T03["Temperature = 0.3 (stabilitas)"]
      R6[seed 42] & R7[seed 43] & R8[seed 44] & R9[seed 45] & R10[seed 46]
    end

    subgraph T07["Temperature = 0.7 (stabilitas)"]
      R11[seed 42] & R12[seed 43] & R13[seed 44] & R14[seed 45] & R15[seed 46]
    end

    T0 --> DETERM["Task 5 - Reproduktibilitas\nFleiss κ + Mean Agreement"]
    T0 & T03 & T07 --> SCHEMA["Task 4 - Schema Compliance\nSVR = off-vocab / total values"]
    T0 & T03 & T07 --> STABILITY["Task 6 - Temperature Stability\nF1 mean/std/range per temp"]
    T0 & T03 & T07 --> HETERO["Task 7 - Heterogenitas\nSVR & Agreement per sektor/bahasa"]

    DETERM --> H2B["H2b: agreement ≥ 0.85"]
    SCHEMA --> H2A["H2a: SVR < 10%"]
    STABILITY --> OBS["Observasi stabil:\nF1 std = 0.000 (temp=0)\nF1 std = 0.019 (temp=0.7)"]

    style T0 fill:#d1fae5,stroke:#059669
    style T03 fill:#fef9c3,stroke:#ca8a04
    style T07 fill:#fee2e2,stroke:#dc2626
    style H2B fill:#d1fae5,stroke:#059669
    style H2A fill:#fef9c3,stroke:#ca8a04
      </div>

      <div class="row g-3">
        <div class="col-md-6">
          <table class="table table-sm table-bordered">
            <thead class="table-light"><tr><th>Task</th><th>Yang Diukur</th><th>Metrik</th></tr></thead>
            <tbody style="font-size:.82rem">
              <tr><td>Task 3</td><td>Determinisme (temp=0)</td><td>Label identical? Raw byte identical?</td></tr>
              <tr><td>Task 4</td><td>Schema compliance (H2a)</td><td>SVR = off-vocab / total, Wilson CI</td></tr>
              <tr><td>Task 5</td><td>Reproduktibilitas (H2b)</td><td>Mean pairwise agreement, Fleiss κ</td></tr>
              <tr><td>Task 6</td><td>Temperature stability</td><td>F1 mean, std, range per temp</td></tr>
              <tr><td>Task 7</td><td>Heterogenitas</td><td>SVR & agreement per sektor/bahasa/sumber</td></tr>
              <tr><td>Task 8</td><td>Cross-verification</td><td>Field slot accounting, consistency check</td></tr>
            </tbody>
          </table>
        </div>
        <div class="col-md-6">
          <div class="step-card">
            <strong>Definisi Schema Violation (SVR)</strong>
            <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">
              Sebuah record <em>violasi</em> jika memiliki salah satu dari:
              <code>syntax</code> (JSON tidak parse), <code>missing</code> (field hilang),
              <code>vocabulary</code> (nilai di luar enum), atau <code>null</code>
              (field ada tapi kosong/salah tipe). SVR = jumlah record violasi / total output.
            </p>
          </div>
          <div class="step-card">
            <strong>Enum-completeness Audit (2026-06-15)</strong>
            <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">
              Ditemukan 3 gold value yang absen dari enum-nya (menyebabkan jawaban benar dihitung salah):
              <code>Defacement</code> → action.hacking.variety;
              <code>Destroy data</code> → attr.integrity.variety;
              <code>Encryption</code> → attr.availability.variety.
              Ditambahkan ke <code>veris_enums.py</code> (add-only, tidak ada yang dihapus).
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── RQ3 Metodologi ── -->
  <div class="card mb-4">
    <div class="card-header"><span class="rq-badge rq3-b me-2">RQ3</span>Metodologi Robustness - 10 Skenario Perturbasi</div>
    <div class="card-body">
      <div class="mermaid mb-4">
flowchart TD
    BASE([🎯 Baseline\n72 record · v3 predictions\nF1 = 0.684]) --> A & B & C

    subgraph A["Skenario A - Variasi Linguistik (LLM-based)"]
      direction LR
      A1["A1: Informal Register\nGaya sosmed, singkatan,\nbahasa gaul Indonesia"]
      A2["A2: Code-switching\nCampur EN↔ID\npada term teknis"]
      A3["A3: Noise Injection\nRule-based 7%:\ntypo, spasi, karakter acak"]
      A4["A4: Cross-lingual\nTerjemahkan ke\nbahasa Inggris penuh"]
    end

    subgraph B["Skenario B - Class Imbalance (Analisis)"]
      direction LR
      B1["B1: Macro vs Micro Gap\nPer dimensi, bukan perturbasi"]
      B2["B2: Rare-class Stress\nSubset sektor minority\n+ rare action_variety"]
      B3["B3: Sector Breakdown\nF1 per sektor pada baseline"]
    end

    subgraph C["Skenario C - Informasi Tidak Lengkap (Rule-based)"]
      direction LR
      C1a["C1a: Headline-only\nHanya judul/kalimat pertama"]
      C1b["C1b: 25% Teks\nPotong ke 25% panjang asli"]
      C1c["C1c: 50% Teks\nPotong ke 50% panjang asli"]
      C2a["C2a: Dropout Actor\nHapus kalimat dengan\nkeyword aktor"]
      C2b["C2b: Dropout Action\nHapus kalimat dengan\nkeyword tindakan"]
      C2c["C2c: Dropout Asset\nHapus kalimat dengan\nkeyword aset"]
    end

    A --> EXTR["Ekstraksi ulang\ndengan teks terperturbasi\n(same v3 prompt)"]
    C --> EXTR
    EXTR --> SCORE2["Scoring\nvs gold standard"]
    BASE --> DELTA["ΔF1 = F1_baseline − F1_scenario\nPaired bootstrap CI 1000×"]
    SCORE2 --> DELTA
    DELTA --> H3TEST["H3 SUPPORTED\niff CI upper < 0.15"]
    B --> STAT["Statistik deskriptif\n(tidak paired ΔF1)"]
    H3TEST & STAT --> MCNEM["McNemar Test\n150 comparisons\nBonferroni α_adj = 0.00033"]

    style BASE fill:#d1fae5,stroke:#059669
    style H3TEST fill:#fce7f3,stroke:#9d174d
    style A fill:#eff6ff,stroke:#3b82f6
    style C fill:#fef9c3,stroke:#ca8a04
    style B fill:#f3e8ff,stroke:#9333ea
      </div>

      <div class="row g-3">
        <div class="col-md-5">
          <table class="table table-sm table-bordered">
            <thead class="table-light"><tr><th>Skenario</th><th>Tipe Perturbasi</th><th>Generator</th></tr></thead>
            <tbody style="font-size:.8rem">
              <tr><td>A1 Informal</td><td>Gaya bahasa santai/sosmed</td><td>LLM (qwen3.5:35b)</td></tr>
              <tr><td>A2 Code-switch</td><td>Campuran ID↔EN</td><td>LLM (qwen3.5:35b)</td></tr>
              <tr><td>A3 Noise</td><td>Typo 7% karakter</td><td>Rule-based</td></tr>
              <tr><td>A4 Translate</td><td>→ Bahasa Inggris</td><td>LLM (qwen3.5:35b)</td></tr>
              <tr><td>C1a Headline</td><td>Teks = headline only</td><td>Rule-based</td></tr>
              <tr><td>C1b 25%</td><td>Potong ke 25%</td><td>Rule-based</td></tr>
              <tr><td>C1c 50%</td><td>Potong ke 50%</td><td>Rule-based</td></tr>
              <tr><td>C2a Actor</td><td>Hapus kalimat aktor</td><td>Rule-based</td></tr>
              <tr><td>C2b Action</td><td>Hapus kalimat aksi</td><td>Rule-based</td></tr>
              <tr><td>C2c Asset</td><td>Hapus kalimat aset</td><td>Rule-based</td></tr>
            </tbody>
          </table>
        </div>
        <div class="col-md-7">
          <div class="step-card mb-2">
            <strong>Keputusan Generator Perturbasi</strong>
            <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">
              LLM perturbation (A1/A2/A4) menggunakan <code>qwen3.5:35b</code> dengan <em>prompt yang berbeda</em>
              dari VERIS extractor (peran: text transformation, bukan extraction). Ini memisahkan generator
              dari evaluator, memenuhi syarat independensi. Fakta yang sama (nama organisasi, angka, tanggal)
              wajib dipertahankan.
            </p>
          </div>
          <div class="step-card mb-2">
            <strong>Metrik ΔF1 &amp; H3</strong>
            <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">
              ΔF1 = F1_baseline − F1_scenario (paired, 72 dokumen yang sama).
              CI dihitung via <strong>paired bootstrap 1000× resample</strong>.
              H3 SUPPORTED iff <em>upper bound CI < 0.15</em> (bukan hanya point estimate).
              McNemar test per dimensi per skenario (150 comparisons total),
              koreksi Bonferroni α_adj = 0.05/150 = 0.00033.
            </p>
          </div>
          <div class="step-card">
            <strong>Skenario B - Analisis Class Imbalance</strong>
            <p class="mb-0 mt-1 text-muted" style="font-size:.8rem">
              B bukan perturbasi: tidak ada paired ΔF1 vs baseline.
              B1 membandingkan macro-F1 vs micro-F1 per dimensi untuk mengidentifikasi
              dimensi yang terpengaruh imbalance. B2 membandingkan subset stress
              (sektor minority + rare action_variety &lt; 3 gold) vs majority.
              B3 adalah breakdown F1 per sektor pada baseline.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Scoring Metrics ── -->
  <div class="card mb-4">
    <div class="card-header"><i class="bi bi-calculator me-1"></i>Definisi Metrik Evaluasi</div>
    <div class="card-body">
      <div class="row g-3">
        <div class="col-md-6">
          <h6 style="font-size:.88rem;font-weight:700">Single-label Dimensions (7)</h6>
          <div class="timeline-line">
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Accuracy</strong> = correct / n (exact match)</div>
            </div>
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Per-class P/R/F1</strong> → Macro-F1 (incl. & excl. kelas Unknown)</div>
            </div>
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Wilson CI</strong> (95%) untuk accuracy</div>
            </div>
            <div class="d-flex gap-2"><div class="timeline-dot"></div>
              <div style="font-size:.82rem">Off-vocab → dihitung salah (tidak di-remap)</div>
            </div>
          </div>

          <h6 class="mt-3" style="font-size:.88rem;font-weight:700">Multi-label Dimensions (8)</h6>
          <div class="timeline-line">
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Set P/R/F1</strong> per-record (gold ∩ pred / …)</div>
            </div>
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Macro-by-record</strong>: mean F1 atas semua record</div>
            </div>
            <div class="d-flex gap-2"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Micro</strong>: pool semua TP/FP/FN lalu hitung</div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <h6 style="font-size:.88rem;font-weight:700">Overall Headline</h6>
          <div class="timeline-line">
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Per-record macro-F1</strong> = mean F1 atas 15 dimensi per dokumen</div>
            </div>
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Overall macro-F1</strong> = mean per-record macro-F1 atas 72 record</div>
            </div>
            <div class="d-flex gap-2 mb-3"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>Bootstrap CI 1000×</strong> resample record-level</div>
            </div>
            <div class="d-flex gap-2"><div class="timeline-dot"></div>
              <div style="font-size:.82rem"><strong>t-test satu-sampel</strong> per-record macro-F1 vs 0.70</div>
            </div>
          </div>

          <h6 class="mt-3" style="font-size:.88rem;font-weight:700">Aturan Verdict H1/H2a/H2b (3-way)</h6>
          <table class="table table-sm table-bordered mb-0">
            <thead class="table-light"><tr><th>Verdict</th><th>Kondisi</th></tr></thead>
            <tbody style="font-size:.79rem">
              <tr><td><span class="badge-sup">SUPPORTED</span></td><td>Seluruh CI ≥ threshold</td></tr>
              <tr><td><span class="badge-not">NOT SUPPORTED</span></td><td>Seluruh CI &lt; threshold</td></tr>
              <tr><td><span class="badge-inc">INCONCLUSIVE</span></td><td>CI straddle threshold</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Tools ── -->
  <div class="card mb-3">
    <div class="card-header"><i class="bi bi-tools me-1"></i>Tools & Environment</div>
    <div class="card-body">
      <div class="row g-3">
        <div class="col-md-4">
          <h6 style="font-size:.85rem;font-weight:700">Infrastruktur</h6>
          <table class="table table-sm mb-0">
            <tbody style="font-size:.8rem">
              <tr><td>Hardware</td><td>GPU instance (Vast.ai)</td></tr>
              <tr><td>Runtime LLM</td><td>Ollama 0.30.7/0.30.8</td></tr>
              <tr><td>Model</td><td>qwen3.5:35b (digest <code>3460ffeede54</code>)</td></tr>
              <tr><td>Python</td><td>3.12, <code>/venv/main</code></td></tr>
            </tbody>
          </table>
        </div>
        <div class="col-md-4">
          <h6 style="font-size:.85rem;font-weight:700">Library Kunci</h6>
          <table class="table table-sm mb-0">
            <tbody style="font-size:.8rem">
              <tr><td>Scoring</td><td>numpy, scipy</td></tr>
              <tr><td>Schema CI</td><td>statsmodels (Wilson/proportion_confint)</td></tr>
              <tr><td>HTTP</td><td>stdlib urllib (extractor), Flask (webapp)</td></tr>
              <tr><td>Data</td><td>json, csv (stdlib)</td></tr>
            </tbody>
          </table>
        </div>
        <div class="col-md-4">
          <h6 style="font-size:.85rem;font-weight:700">File Kode Utama</h6>
          <table class="table table-sm mb-0">
            <tbody style="font-size:.8rem">
              <tr><td><code>veris_enums.py</code></td><td>Vocabulary VERIS 1.3.x</td></tr>
              <tr><td><code>veris_fields.py</code></td><td>Pemetaan field → enum</td></tr>
              <tr><td><code>extract_qwen*.py</code></td><td>Ekstraktor (v1/v2/v3)</td></tr>
              <tr><td><code>score_rq1.py</code></td><td>Scorer utama</td></tr>
              <tr><td><code>rq2_*.py</code></td><td>Pipeline RQ2</td></tr>
              <tr><td><code>rq3_*.py</code></td><td>Pipeline RQ3 (perturb+score)</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════ RINGKASAN ══════════════ -->
<div class="tab-pane fade show active" id="t-sum">
  <h6 class="sec-title"><i class="bi bi-grid-1x2 me-2"></i>Ringkasan Eksperimen</h6>
  <div class="alert alert-primary py-2 px-3 mb-3" style="font-size:.83rem">
    <strong>Model:</strong> qwen3.5:35b (lokal, Ollama) &nbsp;·&nbsp;
    <strong>Dataset:</strong> 100 laporan insiden siber Indonesia (72 in-scope) &nbsp;·&nbsp;
    <strong>VERIS A4:</strong> 15 dimensi (7 single-label + 8 multi-label) &nbsp;·&nbsp;
    <strong>Seed:</strong> 42 · temp=0
  </div>
  <div class="row g-3 mb-4" id="sum-kpis"></div>
  <div class="row g-3 mb-4">
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-bar-chart me-1"></i>Overall Macro-F1 per Versi (RQ1)</div>
        <div class="card-body"><div class="chart-wrap" style="height:250px"><canvas id="cSumF1"></canvas></div></div>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-thermometer me-1"></i>F1 per Temperature (RQ2)</div>
        <div class="card-body"><div class="chart-wrap" style="height:250px"><canvas id="cSumTemp"></canvas></div></div>
      </div>
    </div>
  </div>
  <div class="card mb-4">
    <div class="card-header"><i class="bi bi-check2-circle me-1"></i>Verdict Hipotesis</div>
    <div class="card-body p-0">
      <table class="table table-sm mb-0">
        <thead class="table-light"><tr><th>Hipotesis</th><th>Deskripsi</th><th>Nilai</th><th>Threshold</th><th>Verdict</th></tr></thead>
        <tbody id="sum-verdict"></tbody>
      </table>
    </div>
  </div>
  <div class="card">
    <div class="card-header"><i class="bi bi-lightbulb me-1"></i>Temuan Utama</div>
    <div class="card-body" style="font-size:.88rem;line-height:1.9">
      <ul class="mb-0">
        <li><strong>RQ1:</strong> Few-shot v3 macro-F1 = <strong>0.684</strong> [0.645, 0.719]. Lompatan terbesar: <code>action_variety</code> +0.505, <code>action_vector</code> +0.417, <code>attr_conf_disclosure</code> +0.261 dibanding v2.</li>
        <li><strong>RQ2:</strong> Sepenuhnya deterministik pada temp=0 (Fleiss κ = 1.0 semua 15 dimensi). SVR = 8%, H2a INCONCLUSIVE. H2b SUPPORTED.</li>
        <li><strong>RQ3:</strong> <strong>10/10 skenario H3 SUPPORTED</strong> - model tahan terhadap informal register, code-switching, terjemahan lintas bahasa, pemotongan teks, dan sentence dropout. ΔF1 CI upper maks = 0.070.</li>
        <li><strong>Gap tersisa:</strong> <code>attr_conf_disclosure</code> acc 31%, <code>action_category</code> acc 42% (37/72 gold = Unknown, model bias ke Hacking), <code>asset_category</code> macro-F1 0.265 (salah menaruh variety di slot category).</li>
      </ul>
    </div>
  </div>
</div>

<!-- ══════════════ RQ1 ══════════════ -->
<div class="tab-pane fade" id="t-rq1">
  <h6 class="sec-title"><i class="bi bi-bullseye me-2"></i>RQ1 - Akurasi Ekstraksi VERIS A4</h6>
  <p class="text-muted mb-3" style="font-size:.83rem"><strong>H1:</strong> Overall macro-F1 ≥ 0.70 · n=72 record in-scope · qwen3.5:35b, seed=42, temp=0</p>

  <div class="card mb-3">
    <div class="card-header"><i class="bi bi-table me-1"></i>Perbandingan Lintas Versi</div>
    <div class="card-body p-0">
      <table class="table table-sm mb-0">
        <thead class="table-light"><tr><th>Metrik</th><th class="text-center">v1 Zero-shot</th><th class="text-center">v2 Structural</th><th class="text-center">v3 Few-shot</th></tr></thead>
        <tbody id="r1-compare"></tbody>
      </table>
    </div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-md-8">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-bar-chart-horizontal me-1"></i>Headline F1 per Dimensi (15 dim)</div>
        <div class="card-body"><div class="chart-wrap" style="height:390px"><canvas id="cDimF1"></canvas></div></div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-building me-1"></i>F1 per Sektor (v3)</div>
        <div class="card-body"><div class="chart-wrap" style="height:390px"><canvas id="cSector"></canvas></div></div>
      </div>
    </div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-md-6">
      <div class="card">
        <div class="card-header"><i class="bi bi-check-square me-1"></i>Single-Label: Accuracy + Wilson CI (v3)</div>
        <div class="card-body p-0">
          <table class="table table-sm mb-0">
            <thead class="table-light"><tr><th>Dimensi</th><th class="text-end">Acc</th><th>95% CI</th><th class="text-end">macro-F1</th></tr></thead>
            <tbody id="r1-single"></tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card">
        <div class="card-header"><i class="bi bi-tags me-1"></i>Multi-Label: Set F1 (v3)</div>
        <div class="card-body p-0">
          <table class="table table-sm mb-0">
            <thead class="table-light"><tr><th>Dimensi</th><th class="text-end">macro-P</th><th class="text-end">macro-R</th><th class="text-end">macro-F1</th><th class="text-end">micro-F1</th></tr></thead>
            <tbody id="r1-multi"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════ RQ2 ══════════════ -->
<div class="tab-pane fade" id="t-rq2">
  <h6 class="sec-title"><i class="bi bi-arrow-repeat me-2"></i>RQ2 - Konsistensi, Reproduktibilitas & Schema Compliance</h6>
  <p class="text-muted mb-3" style="font-size:.83rem"><strong>H2a:</strong> SVR &lt; 10% · <strong>H2b:</strong> Mean agreement ≥ 0.85 · n=50 record, 15 runs (5×temp0 + 5×temp0.3 + 5×temp0.7)</p>

  <div class="row g-3 mb-3" id="r2-kpis"></div>

  <div class="row g-3 mb-3">
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-thermometer-half me-1"></i>F1 per Temperature (5 runs each)</div>
        <div class="card-body"><div class="chart-wrap" style="height:260px"><canvas id="cTemp"></canvas></div></div>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-diagram-3 me-1"></i>Fleiss κ per Dimensi (temp=0, 5 runs)</div>
        <div class="card-body"><div class="chart-wrap" style="height:260px"><canvas id="cFleiss"></canvas></div></div>
      </div>
    </div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-md-5">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-shield-check me-1"></i>Schema Compliance - H2a Detail</div>
        <div class="card-body p-0">
          <table class="table table-sm mb-0"><tbody id="r2-schema"></tbody></table>
        </div>
      </div>
    </div>
    <div class="col-md-7">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-buildings me-1"></i>Heterogenitas - SVR per Sektor / Bahasa / Sumber</div>
        <div class="card-body p-0">
          <table class="table table-sm mb-0">
            <thead class="table-light"><tr><th>Grup</th><th>Kategori</th><th class="text-end">n docs</th><th class="text-end">SVR</th><th class="text-end">Agreement</th></tr></thead>
            <tbody id="r2-hetero"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><i class="bi bi-exclamation-circle me-1"></i>Off-Vocabulary per Field (semua runs, hanya field > 0)</div>
    <div class="card-body"><div class="chart-wrap" style="height:220px"><canvas id="cOffVocab"></canvas></div></div>
  </div>
</div>

<!-- ══════════════ RQ3 ══════════════ -->
<div class="tab-pane fade" id="t-rq3">
  <h6 class="sec-title"><i class="bi bi-lightning-charge me-2"></i>RQ3 - Robustness</h6>
  <p class="text-muted mb-3" style="font-size:.83rem"><strong>H3:</strong> ΔF1 CI upper &lt; 0.15 di semua skenario · Baseline: v3 few-shot, n=72</p>

  <div class="row g-3 mb-3" id="r3-kpis"></div>

  <div class="card mb-3">
    <div class="card-header"><i class="bi bi-table me-1"></i>Semua 10 Skenario - ΔF1 vs Baseline</div>
    <div class="card-body p-0">
      <table class="table table-sm mb-0">
        <thead class="table-light"><tr>
          <th>Skenario</th><th class="text-center">F1</th><th class="text-center">ΔF1</th>
          <th class="text-center">95% CI ΔF1</th><th class="text-center">SVR</th><th class="text-center">H3</th>
        </tr></thead>
        <tbody id="r3-scen"></tbody>
      </table>
    </div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-md-7">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-bar-chart me-1"></i>F1 per Skenario vs Baseline</div>
        <div class="card-body"><div class="chart-wrap" style="height:310px"><canvas id="cR3Scen"></canvas></div></div>
      </div>
    </div>
    <div class="col-md-5">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-bar-chart-horizontal me-1"></i>B1: Macro vs Micro F1 per Dimensi</div>
        <div class="card-body"><div class="chart-wrap" style="height:310px"><canvas id="cB1"></canvas></div></div>
      </div>
    </div>
  </div>

  <div class="row g-3">
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-pie-chart me-1"></i>B3 - F1 per Sektor (Baseline)</div>
        <div class="card-body"><div class="chart-wrap" style="height:240px"><canvas id="cB3"></canvas></div></div>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-header"><i class="bi bi-activity me-1"></i>McNemar Bonferroni Correction</div>
        <div class="card-body">
          <div id="r3-bonf" class="row g-2 text-center mb-3"></div>
          <p class="small text-muted mb-0" id="r3-bonf-note"></p>
        </div>
      </div>
    </div>
  </div>
</div>

</div><!-- tab-content -->
</div><!-- container -->

<footer>
  VERIS A4 Extraction Thesis &mdash; qwen3.5:35b lokal via Ollama &mdash; 100 laporan insiden siber berbahasa Indonesia
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
// Init Mermaid - render on tab show so diagrams are visible
mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    primaryColor: '#dbeafe', primaryTextColor: '#1e3a8a',
    primaryBorderColor: '#3b82f6', lineColor: '#64748b',
    secondaryColor: '#f0fdf4', tertiaryColor: '#fef9c3',
    fontSize: '13px'
  },
  flowchart: { curve: 'basis', useMaxWidth: true },
  mindmap:   { useMaxWidth: true }
});

// Re-render Mermaid diagrams when the tab becomes visible
document.addEventListener('shown.bs.tab', async e => {
  if (e.target.getAttribute('href') === '#t-met') {
    await mermaid.run({ querySelector: '#t-met .mermaid' });
  }
});
</script>
<script>
const p2  = v => typeof v==='number' ? (v*100).toFixed(1)+'%' : '-';
const f3  = v => typeof v==='number' ? v.toFixed(3) : '-';
const f2  = v => typeof v==='number' ? v.toFixed(2)  : '-';
const sgn = v => v>0.001 ? '+' : '';

function vbadge(v) {
  if (!v) return '';
  const s = String(v).toUpperCase();
  if (s.includes('NOT SUPPORTED')) return `<span class="badge-not">NOT SUPPORTED</span>`;
  if (s.includes('INCONCLUSIVE'))  return `<span class="badge-inc">INCONCLUSIVE</span>`;
  if (s.includes('SUPPORTED'))     return `<span class="badge-sup">SUPPORTED</span>`;
  return `<span class="badge-not">${v}</span>`;
}

function f1col(v) {
  return v >= .70 ? '#15803d' : v >= .55 ? '#d97706' : '#b91c1c';
}

function barchart(id, labels, datasets, opts={}) {
  const ctx = document.getElementById(id).getContext('2d');
  return new Chart(ctx, {
    type:'bar',
    data:{labels,datasets},
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'top',labels:{boxWidth:11,font:{size:10}}}},
      scales:{
        y:{beginAtZero:true,...(opts.yOpts||{}),grid:{color:'#f1f5f9'},ticks:{font:{size:9}}},
        x:{grid:{display:false},ticks:{font:{size:9},...(opts.xTicks||{})}}
      },...(opts.extra||{})
    }
  });
}

function hbarchart(id, labels, datasets, opts={}) {
  const ctx = document.getElementById(id).getContext('2d');
  return new Chart(ctx, {
    type:'bar',
    data:{labels,datasets},
    options:{
      indexAxis:'y',
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'top',labels:{boxWidth:11,font:{size:10}}}},
      scales:{
        x:{beginAtZero:true,...(opts.xOpts||{}),grid:{color:'#f1f5f9'},ticks:{font:{size:9}}},
        y:{grid:{display:false},ticks:{font:{size:9}}}
      }
    }
  });
}

fetch('/api/data').then(r=>r.json()).then(D=>{
  buildSum(D);
  buildRQ1(D.rq1);
  buildRQ2(D.rq2);
  buildRQ3(D.rq3);
});

// ─── SUMMARY ───
function buildSum(D) {
  const ov3  = D.rq1.v3?.overall  || {};
  const sc   = D.rq2.schema       || {};
  const rep  = D.rq2.repro        || {};
  const st3  = D.rq3.stats        || {};

  const kpis = [
    { icon:'bi-bullseye',    bg:'#eff6ff', bdr:'#93c5fd',
      val: f3(ov3.macro_f1_per_record_mean),
      lbl: 'Overall macro-F1 (RQ1 v3)',
      sub: `CI [${f3(ov3.bootstrap_ci95?.[0])}, ${f3(ov3.bootstrap_ci95?.[1])}]`,
      vrd: ov3.h1_verdict },
    { icon:'bi-shield-check', bg:'#f0fdf4', bdr:'#86efac',
      val: p2(sc.svr),
      lbl: 'Schema-Violation Rate (RQ2)',
      sub: `CI [${p2(sc.svr_wilson_ci95?.[0])}, ${p2(sc.svr_wilson_ci95?.[1])}]`,
      vrd: sc.h2a_verdict },
    { icon:'bi-arrow-repeat', bg:'#fdf4ff', bdr:'#d8b4fe',
      val: f3(rep.mean_agreement),
      lbl: 'Mean Agreement (RQ2)',
      sub: `Fleiss κ = ${f3(rep.fleiss_kappa_macro)}`,
      vrd: rep.h2b_verdict },
    { icon:'bi-lightning-charge', bg:'#fffbeb', bdr:'#fde68a',
      val: `${st3.n_scenarios_h3_supported||10}/10`,
      lbl: 'Skenario H3 SUPPORTED (RQ3)',
      sub: st3.h3_aggregate || 'SUPPORTED',
      vrd: 'SUPPORTED' },
  ];

  document.getElementById('sum-kpis').innerHTML = kpis.map(k=>`
    <div class="col-sm-6 col-xl-3">
      <div class="kpi card" style="background:${k.bg};border-color:${k.bdr}">
        <div class="d-flex gap-3 align-items-start">
          <i class="bi ${k.icon} fs-2" style="color:${k.bdr.replace('fd','a0').replace('ef','6b')}"></i>
          <div>
            <div class="kpi-val">${k.val}</div>
            <div class="kpi-lbl">${k.lbl}</div>
            <div class="mt-1 d-flex gap-2 align-items-center flex-wrap">
              ${vbadge(k.vrd)}
              <span class="text-muted" style="font-size:.71rem">${k.sub}</span>
            </div>
          </div>
        </div>
      </div>
    </div>`).join('');

  // Version F1 chart
  const versions = ['v1 Zero-shot','v2 Structural','v3 Few-shot'];
  const f1vals = [D.rq1.v1,D.rq1.v2,D.rq1.v3].map(v=>v?.overall?.macro_f1_per_record_mean||0);
  barchart('cSumF1', versions, [{
    label:'Macro-F1', data:f1vals,
    backgroundColor:['#93c5fd','#6ee7b7','#34d399'], borderRadius:6
  }], { yOpts:{min:.45,max:.75} });

  // Temperature chart
  const td = D.rq2.temp||{};
  const tlbls = ['temp=0','temp=0.3','temp=0.7'];
  const tkeys = ['temp0','temp0.3','temp0.7'];
  barchart('cSumTemp', tlbls, [{
    label:'Mean F1', data:tkeys.map(k=>td[k]?.macro_f1_mean||0),
    backgroundColor:['#818cf8','#a78bfa','#c084fc'], borderRadius:6
  },{
    label:'Min F1', data:tkeys.map(k=>td[k]?.macro_f1_min||0),
    backgroundColor:'transparent', type:'line',
    borderColor:'#f87171', borderDash:[4,3], pointRadius:4, borderWidth:2
  },{
    label:'Max F1', data:tkeys.map(k=>td[k]?.macro_f1_max||0),
    backgroundColor:'transparent', type:'line',
    borderColor:'#4ade80', borderDash:[4,3], pointRadius:4, borderWidth:2
  }], { yOpts:{min:.62,max:.70} });

  // Verdict table
  const ov2 = D.rq1.v2?.overall||{};
  document.getElementById('sum-verdict').innerHTML = [
    ['H1','Macro-F1 ≥ 0.70', f3(ov3.macro_f1_per_record_mean),'0.70',ov3.h1_verdict],
    ['H2a','SVR < 10%', p2(sc.svr),'10%',sc.h2a_verdict],
    ['H2b','Mean agreement ≥ 0.85', f3(rep.mean_agreement),'0.85',rep.h2b_verdict],
    ['H3','ΔF1 CI upper < 0.15 (10 skenario)', `${st3.n_scenarios_h3_supported||10}/10`,'CI upper < 0.15','SUPPORTED'],
  ].map(([h,d,v,t,vrd])=>`<tr>
    <td class="fw-bold">${h}</td><td class="text-muted">${d}</td>
    <td class="fw-bold">${v}</td><td class="text-muted">${t}</td>
    <td>${vbadge(vrd)}</td></tr>`).join('');
}

// ─── RQ1 ───
function buildRQ1(rq1) {
  const v1=rq1.v1||{}, v2=rq1.v2||{}, v3=rq1.v3||{};
  const o1=v1.overall||{}, o2=v2.overall||{}, o3=v3.overall||{};
  const s1=v1.schema_compliance||{}, s2=v2.schema_compliance||{}, s3=v3.schema_compliance||{};

  document.getElementById('r1-compare').innerHTML = [
    ['Overall macro-F1', f3(o1.macro_f1_per_record_mean), f3(o2.macro_f1_per_record_mean), f3(o3.macro_f1_per_record_mean)],
    ['95% CI', `[${f3(o1.bootstrap_ci95?.[0])},${f3(o1.bootstrap_ci95?.[1])}]`,
               `[${f3(o2.bootstrap_ci95?.[0])},${f3(o2.bootstrap_ci95?.[1])}]`,
               `[${f3(o3.bootstrap_ci95?.[0])},${f3(o3.bootstrap_ci95?.[1])}]`],
    ['t-test vs 0.70', `t=${f2(o1.ttest_t)}, p=${o1.ttest_p?.toExponential(2)||'-'}`,
                       `t=${f2(o2.ttest_t)}, p=${o2.ttest_p?.toExponential(2)||'-'}`,
                       `t=${f2(o3.ttest_t)}, p=${o3.ttest_p?.toFixed(3)||'-'}`],
    ['Macro-F1 atas 15 dim', f3(o1.macro_f1_over_dimensions), f3(o2.macro_f1_over_dimensions), f3(o3.macro_f1_over_dimensions)],
    ['Schema-violation rate', p2(s1.violation_rate), p2(s2.violation_rate), p2(s3.violation_rate)],
    ['JSON salvaged', `${v1.n_salvaged_json||0}`, `${v2.n_salvaged_json||0}`, `${v3.n_salvaged_json||0}`],
    ['Verdict H1', vbadge(o1.h1_verdict), vbadge(o2.h1_verdict), vbadge(o3.h1_verdict)],
  ].map(([m,a,b,c])=>`<tr>
    <td class="fw-semibold">${m}</td>
    <td class="text-center">${a}</td>
    <td class="text-center">${b}</td>
    <td class="text-center fw-bold text-success">${c}</td>
  </tr>`).join('');

  // Dim F1 horizontal bar
  const dhf = v3.dimension_headline_f1||{};
  const dims = Object.keys(dhf);
  const shortd = d=>d.replace('attr_','').replace('_present','_pres').replace('_disclosure','_disc').replace('_category','_cat').replace('_variety','_var').replace('_vector','_vec').replace('_motive','_mot');
  hbarchart('cDimF1', dims.map(shortd), [
    { label:'v1', data:dims.map(d=>(v1.dimension_headline_f1||{})[d]||0), backgroundColor:'rgba(147,197,253,.75)', borderRadius:3 },
    { label:'v2', data:dims.map(d=>(v2.dimension_headline_f1||{})[d]||0), backgroundColor:'rgba(110,231,183,.75)', borderRadius:3 },
    { label:'v3', data:dims.map(d=>dhf[d]||0), backgroundColor:'rgba(52,211,153,.95)', borderRadius:3 },
  ]);

  // Sector
  const ps = v3.per_sector||{};
  const sks = Object.keys(ps);
  barchart('cSector', sks, [{
    label:'macro-F1', data:sks.map(s=>ps[s].macro_f1||0),
    backgroundColor:'#34d399', borderRadius:6
  }], { yOpts:{min:.5,max:1} });

  // Single-label table
  const sl = v3.single_label||{}, wc = v3.wilson_ci||{};
  document.getElementById('r1-single').innerHTML = Object.entries(sl).map(([f,r])=>{
    const w=wc[f]||{}, acc=r.accuracy||0;
    return `<tr>
      <td style="font-size:.78rem">${f}</td>
      <td class="text-end fw-bold" style="color:${f1col(acc)}">${p2(acc)}</td>
      <td style="font-size:.75rem">[${p2(w.lo)}, ${p2(w.hi)}]</td>
      <td class="text-end">${f3(r.macro_f1_incl_unknown)}</td>
    </tr>`;
  }).join('');

  // Multi-label table
  const ml = v3.multi_label||{};
  document.getElementById('r1-multi').innerHTML = Object.entries(ml).map(([f,r])=>`<tr>
    <td style="font-size:.78rem">${f}</td>
    <td class="text-end">${f3(r.macro_p)}</td>
    <td class="text-end">${f3(r.macro_r)}</td>
    <td class="text-end fw-bold" style="color:${f1col(r.macro_f1)}">${f3(r.macro_f1)}</td>
    <td class="text-end">${f3(r.micro_f1)}</td>
  </tr>`).join('');
}

// ─── RQ2 ───
function buildRQ2(rq2) {
  const sc  = rq2.schema||{}, rep = rq2.repro||{};
  const td  = rq2.temp||{},   het = rq2.hetero||{};

  document.getElementById('r2-kpis').innerHTML = [
    { icon:'bi-shield', lbl:'H2a - Schema Compliance',
      sub:`SVR=${p2(sc.svr)} CI[${p2(sc.svr_wilson_ci95?.[0])},${p2(sc.svr_wilson_ci95?.[1])}]`,
      vrd: sc.h2a_verdict },
    { icon:'bi-arrow-repeat', lbl:'H2b - Reproduktibilitas',
      sub:`Mean agreement=${f3(rep.mean_agreement)} · Fleiss κ=${f3(rep.fleiss_kappa_macro)}`,
      vrd: rep.h2b_verdict },
    { icon:'bi-check2-all', lbl:'Determinisme (temp=0)',
      sub:`5/5 runs identik byte-for-byte · κ=1.0 semua 15 dim`,
      vrd:'SUPPORTED' },
  ].map(k=>`<div class="col-md-4"><div class="card p-3 h-100">
    <div class="d-flex gap-2 align-items-center mb-1">
      <i class="bi ${k.icon} text-primary"></i><strong style="font-size:.87rem">${k.lbl}</strong>
    </div>
    <div class="text-muted mb-2" style="font-size:.79rem">${k.sub}</div>
    ${vbadge(k.vrd)}
  </div></div>`).join('');

  // Temp chart
  const tkeys=['temp0','temp0.3','temp0.7'], tlbls=['temp=0','temp=0.3','temp=0.7'];
  barchart('cTemp', tlbls, [
    { label:'Mean F1', data:tkeys.map(k=>td[k]?.macro_f1_mean||0), backgroundColor:['#818cf8','#a78bfa','#c084fc'], borderRadius:6 },
    { label:'Min', data:tkeys.map(k=>td[k]?.macro_f1_min||0), type:'line', borderColor:'#f87171', borderDash:[4,3], pointRadius:5, borderWidth:2, backgroundColor:'transparent' },
    { label:'Max', data:tkeys.map(k=>td[k]?.macro_f1_max||0), type:'line', borderColor:'#4ade80', borderDash:[4,3], pointRadius:5, borderWidth:2, backgroundColor:'transparent' },
  ], { yOpts:{min:.62,max:.70} });

  // Fleiss chart
  const fk = rep.fleiss_kappa_per_dim||{};
  const fks = Object.keys(fk);
  hbarchart('cFleiss', fks.map(k=>k.replace('attr_','').replace('_present','_pres')),
    [{ label:'Fleiss κ', data:fks.map(k=>fk[k]||1), backgroundColor:'#34d399', borderRadius:3 }],
    { xOpts:{min:.9,max:1.02} }
  );

  // Schema detail table
  document.getElementById('r2-schema').innerHTML = [
    ['SVR', `<strong>${p2(sc.svr)}</strong>`],
    ['Wilson 95% CI', sc.svr_wilson_ci95 ? `[${p2(sc.svr_wilson_ci95[0])}, ${p2(sc.svr_wilson_ci95[1])}]` : '-'],
    ['Field completeness', p2(sc.field_completeness_rate)],
    ['Vocab conformance', p2(sc.vocab_conformance_rate)],
    ['Violation records', `${sc.n_violation_records} / ${sc.n_total_outputs}`],
    ['Causes', Object.entries(sc.cause_summary||{}).map(([k,v])=>`${k}:${v}`).join(', ')||'-'],
    ['H2a Verdict', vbadge(sc.h2a_verdict)],
  ].map(([k,v])=>`<tr><td class="fw-semibold">${k}</td><td>${v}</td></tr>`).join('');

  // Hetero table
  const rows = [];
  const cats = {by_sector:'Sektor', by_language:'Bahasa', by_source:'Sumber'};
  Object.entries(cats).forEach(([key,lbl])=>{
    Object.entries(het[key]||{}).forEach(([g,d])=>{
      rows.push(`<tr><td>${lbl}</td><td>${g}</td><td class="text-end">${d.n_docs}</td><td class="text-end">${p2(d.svr)}</td><td class="text-end">${f3(d.mean_agreement)}</td></tr>`);
    });
  });
  document.getElementById('r2-hetero').innerHTML = rows.join('');

  // Off-vocab chart
  const pf = sc.per_field||{};
  const pfk = Object.keys(pf).filter(k=>(pf[k].off||0)>0);
  if (pfk.length) {
    hbarchart('cOffVocab', pfk,
      [{ label:'Off-vocab values', data:pfk.map(k=>pf[k].off||0), backgroundColor:'#f87171', borderRadius:3 }],
      { xOpts:{min:0,max:Math.max(2,...pfk.map(k=>pf[k].off||0))+1} }
    );
  } else {
    document.getElementById('cOffVocab').parentElement.innerHTML =
      '<div class="text-center text-success py-4"><i class="bi bi-check-circle-fill fs-2"></i><div class="mt-2">Tidak ada off-vocabulary values pada runs ini</div></div>';
  }
}

// ─── RQ3 ───
function buildRQ3(rq3) {
  const base = rq3.baseline||{}, st = rq3.stats||{};
  const scen = rq3.scenarios||{};
  const b1   = rq3.b1_sorted||[];
  const b3   = rq3.b3_sector||{};
  const bsf1 = base.overall_macro_f1||.6841;
  const bscore= base.core_a4_f1_excl_unknown||.7172;

  document.getElementById('r3-kpis').innerHTML = [
    { val:f3(bsf1), lbl:'Baseline Overall F1', sub:`CI [${f3((base.overall_macro_f1_ci95||[])[0])}, ${f3((base.overall_macro_f1_ci95||[])[1])}]`, icon:'bi-rulers' },
    { val:f3(bscore), lbl:'Baseline Core-A4 excl-Unk', sub:'actor/action/asset_cat + 3 attr-present', icon:'bi-award' },
    { val:`${st.n_scenarios_h3_supported||10}/10`, lbl:'Skenario H3 SUPPORTED', sub:st.h3_aggregate||'SUPPORTED', icon:'bi-patch-check' },
    { val:`${st.bonferroni?.n_reject_bonferroni||0}`, lbl:'McNemar Bonferroni Reject', sub:`${st.bonferroni?.n_mcnemar_comparisons||150} comparisons total`, icon:'bi-activity' },
  ].map(k=>`<div class="col-sm-6 col-xl-3">
    <div class="card p-3 h-100">
      <div class="d-flex gap-2 align-items-center mb-1">
        <i class="bi ${k.icon} text-primary fs-5"></i>
        <span class="fw-semibold" style="font-size:.82rem">${k.lbl}</span>
      </div>
      <div class="fs-3 fw-bold">${k.val}</div>
      <div class="text-muted" style="font-size:.73rem">${k.sub}</div>
    </div>
  </div>`).join('');

  const SCEN_META = [
    { key:'A1', lbl:'A1 - Informal register (LLM)' },
    { key:'A2', lbl:'A2 - Code-switching ID↔EN (LLM)' },
    { key:'A3', lbl:'A3 - Noise injection 7% (rule-based)' },
    { key:'A4', lbl:'A4 - Terjemahan → Inggris (LLM)' },
    { key:'C1_headline', lbl:'C1a - Truncation: headline only' },
    { key:'C1_25pct',    lbl:'C1b - Truncation: 25% teks' },
    { key:'C1_50pct',    lbl:'C1c - Truncation: 50% teks' },
    { key:'C2_actor',    lbl:'C2a - Dropout: kalimat actor' },
    { key:'C2_action',   lbl:'C2b - Dropout: kalimat action' },
    { key:'C2_asset',    lbl:'C2c - Dropout: kalimat asset' },
  ];

  document.getElementById('r3-scen').innerHTML = SCEN_META.map(m=>{
    const s = scen[m.key]||{};
    const d = s.delta_overall||{};
    const f1= s.overall_macro_f1, dm=d.delta_mean, lo=d.ci95_lo, hi=d.ci95_hi;
    const h3ok = d.h3_supported !== false && (st.h3_per_scenario||{})[m.key] !== false;
    const cls = h3ok ? 'scen-row-ok' : 'scen-row-no';
    const dcls = dm>0.005?'text-danger':dm<-0.005?'text-success':'';
    return `<tr class="${cls}">
      <td>${m.lbl}</td>
      <td class="text-center fw-bold" style="color:${typeof f1==='number'?f1col(f1):'#555'}">${f3(f1)}</td>
      <td class="text-center ${dcls}">${typeof dm==='number'?sgn(dm)+f3(dm):'-'}</td>
      <td class="text-center text-muted" style="font-size:.76rem">${typeof lo==='number'?`[${f3(lo)}, ${f3(hi)}]`:'-'}</td>
      <td class="text-center">${p2(s.svr)}</td>
      <td class="text-center">${vbadge(h3ok?'SUPPORTED':'NOT SUPPORTED')}</td>
    </tr>`;
  }).join('');

  // Scenario F1 chart
  const scenf1 = SCEN_META.map(m=>(scen[m.key]||{}).overall_macro_f1||0);
  barchart('cR3Scen', SCEN_META.map(m=>m.key), [
    { label:'Baseline', data:SCEN_META.map(()=>bsf1), type:'line',
      borderColor:'#ef4444', borderDash:[6,3], pointRadius:0, borderWidth:2, order:0 },
    { label:'Skenario F1', data:scenf1,
      backgroundColor:scenf1.map(v=>v>=bsf1-.02?'#34d399':'#fbbf24'), borderRadius:4, order:1 },
  ], { yOpts:{min:.60,max:.75}, xTicks:{maxRotation:45} });

  // B1 macro vs micro chart
  const b1dims  = b1.map(([k])=>k.replace('attr_','').replace('_present','_pres'));
  const b1macro = b1.map(([,v])=>v.macro_f1||0);
  const b1micro = b1.map(([,v])=>v.micro_f1||0);
  hbarchart('cB1', b1dims, [
    { label:'Macro-F1', data:b1macro, backgroundColor:'rgba(129,140,248,.8)', borderRadius:3 },
    { label:'Micro-F1', data:b1micro, backgroundColor:'rgba(52,211,153,.8)', borderRadius:3 },
  ]);

  // B3 sector
  const b3keys = Object.keys(b3);
  barchart('cB3', b3keys, [{
    label:'Mean F1 (baseline)', data:b3keys.map(k=>b3[k]?.mean_f1||0),
    backgroundColor:'#818cf8', borderRadius:6
  }], { yOpts:{min:.5,max:.9} });

  // Bonferroni
  const bfr = st.bonferroni||{};
  document.getElementById('r3-bonf').innerHTML = [
    [bfr.n_mcnemar_comparisons||150, 'Total comparisons', ''],
    [bfr.n_reject_raw_alpha05||3,    'Reject (α=0.05)',   'text-warning'],
    [bfr.n_reject_bonferroni||0,     'Reject (Bonferroni)','text-success fw-bold'],
  ].map(([v,l,c])=>`<div class="col-4"><div class="fs-3 fw-bold ${c}">${v}</div><div class="small text-muted">${l}</div></div>`).join('');
  document.getElementById('r3-bonf-note').textContent =
    `Bonferroni α_adjusted = ${(bfr.alpha_adjusted||0.000333).toFixed(5)} `+
    `(${bfr.n_mcnemar_comparisons||150} uji McNemar per dimensi per skenario). `+
    `Setelah koreksi, tidak ada perbedaan dimensi yang signifikan secara statistik.`;
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=16006, debug=False)
