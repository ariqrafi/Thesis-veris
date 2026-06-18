# Evaluasi LLM Lokal untuk Ekstraksi Struktur Insiden VERIS A4 dari Laporan Insiden Siber Berbahasa Indonesia

Repositori kode dan data untuk skripsi/tesis yang mengevaluasi kemampuan model bahasa lokal (`qwen3.5:35b` via Ollama) dalam mengekstraksi struktur insiden VERIS A4 dari laporan insiden siber berbahasa Indonesia.

## Gambaran Umum

Penelitian ini menguji apakah LLM lokal dapat mengklasifikasikan laporan insiden siber ke dalam skema **VERIS (Vocabulary for Event Recording and Incident Sharing) A4** secara akurat, konsisten, dan robust — tanpa bergantung pada layanan cloud.

**Skema A4 yang diekstraksi (15 dimensi):**
- **Actor** — kategori, variety, motive
- **Action** — kategori, variety, vector
- **Asset** — kategori, variety
- **Attribute** — confidentiality, integrity, availability (presence + variety/disclosure)

## Pertanyaan Penelitian & Hasil

| RQ | Hipotesis | Verdict |
|---|---|---|
| **RQ1** — Akurasi ekstraksi A4 | H1: Macro-F1 ≥ 0.70 | **INCONCLUSIVE** (F1=0.684, CI [0.645, 0.719]) |
| **RQ2** — Schema compliance | H2a: Schema Violation Rate < 10% | **INCONCLUSIVE** (SVR=8.00%, CI [5.24%, 12.03%]) |
| **RQ2** — Reproducibility | H2b: Mean agreement ≥ 0.85 | **SUPPORTED** (agreement=1.000) |
| **RQ3** — Robustness (10 skenario) | H3: ΔF1 ≤ 0.15 di semua skenario | **SUPPORTED** (semua CI upper < 0.15) |

### Perkembangan RQ1 (tiga versi prompt)

| Versi | Konfigurasi | Overall Macro-F1 | Verdict |
|---|---|---:|---|
| v1 | Zero-shot baseline | 0.543 | NOT SUPPORTED |
| v2 | Perbaikan struktural prompt | 0.573 | NOT SUPPORTED |
| **v3** | **Few-shot 6 exemplar** | **0.684** | **INCONCLUSIVE** |

## Setup & Reproduksi

### Prasyarat

- Python 3.9+
- [Ollama](https://ollama.ai/) terinstall di mesin

### 1. Clone repo

```bash
git clone https://github.com/ariqrafi/Thesis.git
cd Thesis
```

### 2. Install dependensi Python

```bash
pip install -r requirements.txt
```

**Package yang dibutuhkan:**
| Package | Kegunaan |
|---|---|
| `flask` | Dashboard web (`webapp.py`) |
| `numpy` | Komputasi statistik scorer |
| `scipy` | Bootstrap CI, uji-t, proporsi |
| `statsmodels` | Fleiss' κ, Wilson CI, McNemar |

### 3. Siapkan Ollama & model

```bash
# Install Ollama (https://ollama.ai/download)
ollama serve

# Pull model (±20GB)
ollama pull qwen3.5:35b

# Verifikasi digest model (penting untuk reproduktibilitas)
ollama show qwen3.5:35b --modelfile | grep FROM
# Harus: 3460ffeede54
```

> **Catatan:** Ollama default berjalan di `http://localhost:11434`. Jika port berbeda, sesuaikan variabel `OLLAMA_URL` di tiap script extractor.

## Struktur Proyek

```
Thesis-gpu/
├── data/
│   ├── dataset_clean.jsonl         # Korpus lengkap 642 laporan insiden
│   ├── eval_set_100.jsonl          # Subset evaluasi 100 record
│   ├── gold_standard.json          # Anotasi gold 100 record (72 in-scope)
│   ├── fewshot_candidates.json     # Kandidat exemplar few-shot (FS-01..FS-08)
│   ├── fewshot_exemplars.json      # 6 exemplar final (FS-01,02,04,05,06,07)
│   ├── repro_subset_50.jsonl       # Subset 50 record untuk RQ2
│   └── repro_subset_leakage_check.json
│
├── veris_enums.py                  # Vocabulary VERIS 1.3.x (34 enum)
├── veris_fields.py                 # Mapping field → enum
├── score_core.py                   # Scorer Core-A4 (6 dimensi kategori)
│
├── extract_qwen.py                 # Extractor v1 (zero-shot)
├── extract_qwen_v2.py              # Extractor v2 (struktural)
├── extract_qwen_fewshot.py         # Extractor v3 (few-shot)
├── score_rq1.py                    # Scorer RQ1 (15 dimensi)
├── build_repro_subset.py           # Builder subset RQ2
│
├── rq2_run.py                      # Runner RQ2 (5 run × 3 temperatur)
├── rq2_analyze.py                  # Analisis schema compliance & reproducibility
├── rq2_lib.py                      # Library analisis RQ2
├── rq2_revalidate.py               # Revalidasi enum
├── rq2_summary.py                  # Ringkasan RQ2
│
├── rq3_perturb_rulebased.py        # Perturbasi rule-based (noise 7%)
├── rq3_perturb_llm.py              # Perturbasi berbasis LLM (A1/A2/A4)
├── rq3_extract_scenario.py         # Ekstraksi per skenario RQ3
├── rq3_baseline.py                 # Baseline RQ3
├── rq3_stats.py                    # Statistik RQ3
├── rq3_analyze_B.py                # Analisis skenario B (class imbalance)
├── rq3_score_scenario.py           # Scoring per skenario
├── rq3_summary_gen.py              # Generator ringkasan RQ3
├── rq3_lib.py                      # Library RQ3
├── rq3_run_all.sh                  # Script runner semua skenario RQ3
│
├── webapp.py                       # Dashboard Flask (port 16006)
│
├── rq1/                            # Hasil & laporan RQ1
├── rq2/                            # Hasil & laporan RQ2
└── rq3/                            # Hasil, perturbasi & prediksi RQ3
```

## Menjalankan Evaluasi

### RQ1 — Akurasi Ekstraksi

```bash
# v1: zero-shot
python extract_qwen.py

# v2: struktural
python extract_qwen_v2.py

# v3: few-shot (final)
python extract_qwen_fewshot.py

# Scoring
python score_rq1.py
```

### RQ2 — Konsistensi & Schema Compliance

```bash
python rq2_run.py        # jalankan 5 run × 3 temperatur
python rq2_analyze.py    # analisis hasil
python rq2_summary.py    # ringkasan
```

### RQ3 — Robustness

```bash
bash rq3_run_all.sh      # jalankan semua 10 skenario
python rq3_stats.py      # statistik & H3 verdict
```

### Dashboard Web

```bash
python webapp.py
# buka http://localhost:16006
```

## Konfigurasi Model

| Parameter | Nilai |
|---|---|
| Model | `qwen3.5:35b` |
| Model digest (di-pin) | `3460ffeede54` |
| Ollama | `0.30.8` |
| Temperature (RQ1/RQ3) | `0` |
| Seed | `42` |
| think | `False` |
| num_ctx | `32768` |
| Input max chars | `16000` |

## Dataset

- **642 laporan insiden siber Indonesia** dari berbagai sumber (media, regulator, vendor)
- **100 record eval** dengan anotasi gold teradjudikasi (72 in-scope A4)
- **Sektor:** government (dominan), financial, telco, education/healthcare
- **Bahasa:** Indonesia (dominan), Inggris, campuran

## Skenario Robustness (RQ3)

| Kode | Skenario | Metode |
|---|---|---|
| A1 | Informal register | LLM paraphrase |
| A2 | Code-switching (Indo-Inggris) | LLM |
| A3 | Noise injection 7% | Rule-based |
| A4 | Terjemahan ke Inggris | LLM |
| C1a | Truncation: headline only | Rule-based |
| C1b | Truncation: 25% teks | Rule-based |
| C1c | Truncation: 50% teks | Rule-based |
| C2a | Dropout kalimat kata kunci *actor* | Rule-based |
| C2b | Dropout kalimat kata kunci *action* | Rule-based |
| C2c | Dropout kalimat kata kunci *asset* | Rule-based |

## Teknologi

- **Model:** [Qwen3.5 35B](https://ollama.com/library/qwen3) via Ollama (lokal, tanpa cloud)
- **Skema:** [VERIS 1.3.x](http://veriscommunity.net/)
- **Backend dashboard:** Flask
- **Analisis:** Python (numpy, scipy)
