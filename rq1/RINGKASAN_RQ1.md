# Ringkasan Evaluasi RQ1 — Ekstraksi VERIS A4 (qwen3.5:35b)

_Diperbarui: 2026-06-14. Satu file konsolidasi untuk thesis RQ1: hasil run v1 (baseline), v2 (perbaikan struktural prompt), dan v3 (few-shot 6 exemplar), metrik headline + Core-A4, beserta catatan pembuatan/metodologi._

## 1. Konfigurasi & Reproduktibilitas

| Parameter | Nilai |
|---|---|
| Model | `qwen3.5:35b` (lokal, Ollama) |
| Digest model (pinned) | `3460ffeede54` |
| Ollama | `0.30.7` |
| temperature | 0 |
| seed | 42 |
| think | False |
| Teks input | `full_content_clean` (truncate 16000 char) |
| Subset skor | 72 record (gold `in_scope==Yes` dari 100) |
| Gold standard | `gold_standard.json` (100 record teradjudikasi) — TIDAK diubah |

> **Catatan grammar:** dengan `think:false`, Ollama TIDAK menegakkan grammar JSON-schema `format`, sehingga nilai di luar vocabulary bisa muncul. Vocabulary VERIS penuh ditaruh di prompt, model generate bebas, validasi dilakukan di Python → schema-violation rate menjadi besaran terukur nyata (bukan dipaksa grammar).

## 2. Hasil Headline — v1 vs v2

| Metrik | v1 (baseline) | v2 (perbaikan struktural) |
|---|---:|---:|
| Schema-violation rate (semua nilai) | 2.0% | 0.1% |
| — `asset_category` off-vocab | 18/72 | 0/72 |
| — Record di-salvage JSON | 13 | 0 |
| `asset_category` accuracy | 37.5% | 66.7% |
| `asset_category` macro-F1 (incl Unk) | 0.212 | 0.341 |
| **Overall macro-F1 (15 dim, per-record)** | **0.543** | **0.573** |
| — 95% bootstrap CI | [0.513, 0.571] | [0.545, 0.600] |
| — t-test vs 0.70 | t=-10.54, p=3.6e-16 | t=-8.93, p=3.2e-13 |
| — **Verdict H1 (≥0.70)** | NOT SUPPORTED | NOT SUPPORTED |

## 3. Metrik Sekunder — Core-A4 (level kategori, 6 dimensi)

Dibatasi pada 6 dimensi kategori single-label: `actor_category, action_category, asset_category, attr_conf_present, attr_integrity_present, attr_avail_present`.

| Core-A4 | v1 | v2 |
|---|---:|---:|
| macro-F1 (incl Unknown) | 0.423 | 0.480 |
| — 95% CI | [0.367, 0.484] | [0.402, 0.552] |
| — Verdict H1 | NOT SUPPORTED | NOT SUPPORTED |
| macro-F1 (excl Unknown) | 0.526 | 0.585 |
| — 95% CI | [0.460, 0.628] | [0.487, 0.691] |
| — Verdict H1 | NOT SUPPORTED | NOT SUPPORTED |

### Per-dimensi Core-A4 (macro-F1 incl / excl Unknown)

| Dimensi | v1 acc | v1 F1 incl | v1 F1 excl | v2 acc | v2 F1 incl | v2 F1 excl |
|---|---:|---:|---:|---:|---:|---:|
| actor_category | 69.4% | 0.527 | 0.507 | 79.2% | 0.573 | 0.537 |
| action_category | 40.3% | 0.475 | 0.593 | 40.3% | 0.484 | 0.605 |
| asset_category | 37.5% | 0.212 | 0.282 | 66.7% | 0.341 | 0.455 |
| attr_conf_present | 86.1% | 0.308 | 0.463 | 83.3% | 0.641 | 0.785 |
| attr_integrity_present | 59.7% | 0.361 | 0.465 | 59.7% | 0.353 | 0.530 |
| attr_avail_present | 81.9% | 0.654 | 0.847 | 65.3% | 0.489 | 0.600 |

## 4. Per-dimensi lengkap (15 dimensi) — headline F1 v1 vs v2

Single-label = macro-F1 (incl Unknown); multi-label = macro-by-record F1.

| Dimensi | Tipe | v1 F1 | v2 F1 |
|---|---|---:|---:|
| actor_category | single | 0.527 | 0.573 |
| action_category | single | 0.475 | 0.484 |
| asset_category | single | 0.212 | 0.341 |
| attr_conf_present | single | 0.308 | 0.641 |
| attr_integrity_present | single | 0.361 | 0.353 |
| attr_avail_present | single | 0.654 | 0.489 |
| attr_conf_disclosure | single | 0.163 | 0.062 |
| actor_variety | multi | 0.234 | 0.400 |
| actor_motive | multi | 0.877 | 0.829 |
| action_variety | multi | 0.121 | 0.149 |
| action_vector | multi | 0.131 | 0.150 |
| asset_variety | multi | 0.368 | 0.579 |
| attr_conf_data_variety | multi | 0.705 | 0.719 |
| attr_integrity_variety | multi | 0.875 | 0.861 |
| attr_avail_variety | multi | 0.884 | 0.782 |

## 5. Per-sektor (v2)

| Sektor | n | macro-F1 |
|---|---:|---:|
| government | 53 | 0.558 |
| financial | 7 | 0.669 |
| telco | 3 | 0.581 |
| education_healthcare | 4 | 0.622 |
| unknown | 5 | 0.549 |

> ⚠️ telco (n=3) & education_healthcare (n=4) sangat kecil → indikatif saja.

## 5c. Hasil v3 — Few-shot (Part B)

6 exemplar leakage-safe (FS-01, FS-02, FS-04, FS-05, FS-06, FS-07) dari korpus di LUAR eval-100, dianotasi manual peneliti, disisipkan sebagai giliran user/assistant sebelum query asli. Prompt sistem & schema sama dengan v2.

> **Catatan re-run (2026-06-14):** v3 pertama memakai exemplar cacat — `action_vector` dibiarkan kosong di mayoritas exemplar → model ikut under-predict (F1 action_vector anjlok ke 0.04, overall 0.650). Peneliti mengoreksi `fewshot_exemplars.json` (action_vector terisi di keenam exemplar; field confidentiality FS-01). Run cacat diarsipkan di `_v3_old_flawed/`. Angka di bawah = v3 terkoreksi.

| Metrik | v2 | v3 (cacat) | **v3 (terkoreksi)** |
|---|---:|---:|---:|
| Schema-violation rate | 0.1% | 0.1% | 0.2% |
| **Overall macro-F1 (15 dim)** | 0.573 | 0.650 | **0.684** |
| — 95% bootstrap CI | [0.545, 0.600] | [0.612, 0.683] | [0.645, 0.719] |
| Core-A4 macro-F1 incl Unknown | 0.480 | 0.526 | 0.528 |
| Core-A4 macro-F1 excl Unknown | 0.585 | 0.703 | **0.717** (CI [0.620, 0.796]) |
| **Verdict H1 (≥0.70)** | NOT SUPPORTED | NOT SUPPORTED | **INCONCLUSIVE** (overall & excl-Unk CI menstraddle 0.70) |

**Δ per-dimensi terbesar v2 → v3 terkoreksi:** `action_variety` +0.505, `action_vector` +0.417 (perbaikan exemplar berhasil), `attr_conf_disclosure` +0.261, `attr_integrity_present` +0.209, `actor_variety` +0.153, `attr_avail_variety` +0.116.
**Regresi:** `actor_motive` −0.151 (dulu dimensi terkuat; few-shot membiaskan ke "Financial" — 5/6 exemplar bermotif Financial/Ideology), `asset_category` −0.076 (masih ketuker dengan asset_variety).
**Masih lemah:** `asset_category` (F1 0.265, acc 64%), `attr_conf_disclosure` (acc 31%), `action_category` (acc 42%). Perbandingan lengkap: `report_v3_compare.md`.

## 6. Kesimpulan

- **H1 (F1 ≥ 0.70):** TIDAK didukung pada v1 & v2 (seluruh CI di bawah 0.70). Pada **v3 few-shot menjadi INCONCLUSIVE** — overall 0.684 (CI [0.645, 0.719]) dan Core-A4 excl-Unknown 0.717 (CI [0.620, 0.796]) keduanya menstraddle 0.70; bukti belum cukup untuk menerima maupun menolak.

- Lintasan perbaikan: v1 0.543 → v2 0.573 (perbaikan struktural prompt) → v3 0.684 (+6 exemplar few-shot). Lompatan terbesar pada dimensi yang dulu terlemah (`action_variety`, `action_vector`, `attr_conf_disclosure`).

- Perbaikan struktural v2 menaikkan kualitas tanpa menyentuh logika labeling: schema-violation 2.0% → 0.1%, salvage 13 → 0, `asset_category` acc 37.5% → 66.7%.

- **Pelajaran few-shot:** kualitas anotasi exemplar berpengaruh besar — label `[]` di sebuah field exemplar MENGAJARI model untuk under-predict field itu (terbukti pada action_vector 0.04 → 0.567 setelah dikoreksi).

- Gap tersisa ke 0.70 didominasi `asset_category`, `attr_conf_disclosure`, dan `action_category`; few-shot juga memunculkan trade-off (regresi `actor_motive`).

---

## 7. Catatan Pembuatan (Metodologi & Keputusan)

### 7.1 Pipeline & file

- `veris_enums.py` — vocabulary terkontrol VERIS 1.3.x A4 (34 enum, verbatim dari gold).
- `veris_fields.py` — pemetaan field→enum (dipakai bersama extractor & scorer agar tidak drift).
- `extract_qwen.py` (v1) / `extract_qwen_v2.py` (v2) / `extract_qwen_fewshot.py` (v3) — pemanggil Ollama `/api/chat`.
- `score_rq1.py` — skor utama (schema compliance + akurasi + statistik). Argumen `--tag`/`--preds` untuk v2/v3.
- `score_core.py` — metrik sekunder Core-A4 (6 dimensi kategori).
- Output v1: `predictions_seed42.json`, `metrics_seed42.json`, `metrics_core_seed42.json`, `report_seed42.md`, `errors_seed42.csv`.
- Output v2: `predictions_v2_seed42.json`, `metrics_v2_seed42.json`, `metrics_core_v2_seed42.json`, `report_v2_seed42.md`, `errors_v2_seed42.csv`.
- Output v3: `predictions_v3_fewshot_seed42.json`, `metrics_v3_seed42.json`, `metrics_core_v3_seed42.json`, `report_v3_seed42.md`, `errors_v3_seed42.csv`, `report_v3_compare.md`. Exemplar: `fewshot_candidates.json` + `fewshot_exemplars.json`. Run cacat: `_v3_old_flawed/`.

### 7.2 Keputusan metodologis

- **Zero-shot**: prompt hanya berisi schema + vocabulary, TANPA contoh berlabel dari korpus (kontrol kebocoran data). Ilustrasi Server/Database pada v2 adalah penjelasan skema generik, bukan exemplar korpus.
- **`think:false`** dipilih untuk menghindari reasoning trace ~80s/panggilan; konsekuensinya grammar tidak ditegakkan → schema compliance diukur nyata (by-product RQ2).
- **Validasi di Python = sumber kebenaran**; nilai off-vocabulary dihitung SALAH, tidak di-remap diam-diam.
- **Reproduktibilitas**: temperature 0, seed 42, digest model di-pin & dicatat di metrics.

### 7.3 Kejadian saat run (untuk bagian Methods)

- **v1**: 13/72 record gagal JSON karena model menulis field `rationale` (tak diskor, paling akhir) tanpa tanda kutik pembuka. Diatasi dengan `salvage_json()` deterministik: buang segmen mulai `"rationale"`, parse sisanya. TIDAK ada pemanggilan model ulang — raw tersimpan & model deterministik. Ditandai `_salvaged` per-record.
- **v1**: model sering menaruh `Database` (sebuah *variety*) di slot `asset_category` (18×) → terdeteksi sebagai schema violation.
- **v2 — dua perubahan STRUKTURAL saja** pada SYSTEM_PROMPT: (a) aturan tegas pemisahan CATEGORY vs VARIETY untuk actor/action/asset + ilustrasi Server/Database; (b) `rationale` dihapus dari output wajib & dari `format` schema. Tidak ada perubahan lain (tidak menyentuh logika labeling). Hasil: salvage 0, off-vocab `asset_category` 0.
- **Lingkungan**: `numpy`/`scipy` belum terpasang → diinstal ke `/venv/main`; scorer dijalankan dengan `/venv/main/bin/python`. Extractor hanya pakai stdlib.

### 7.4 Definisi metrik (ringkas)

- *Single-label* (kategori): accuracy + per-class P/R/F1 → macro-F1 (dilaporkan incl & excl kelas Unknown, karena Unknown ~dominan).
- *Multi-label* (variety/vector): set P/R/F1 per-record (macro-by-record) + micro (pooling).
- *Overall macro-F1 (headline)* = rata-rata per-record dari mean F1 atas 15 dimensi; CI via bootstrap 1000 resample atas record; uji-t satu sampel per-record macro-F1 vs 0.70.
- *Core-A4* = macro-F1 dirata-rata atas 6 dimensi kategori inti; bootstrap incl & excl Unknown; verdict berdasar posisi CI terhadap 0.70.
