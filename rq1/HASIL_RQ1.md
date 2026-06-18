# HASIL RQ1 — Evaluasi Ekstraksi VERIS A4 oleh `qwen3.5:35b`

_Dokumen hasil lengkap + metodologi. Seed 42. Dibuat: 2026-06-14._

**RQ1:** Sejauh mana model bahasa lokal (`qwen3.5:35b`) mampu mengekstraksi
struktur insiden VERIS A4 (actor, action, asset, attribute) dari laporan
insiden berbahasa Indonesia secara akurat?

**H1:** Macro-F1 keseluruhan ekstraksi A4 ≥ 0.70.

**Ringkasan verdict:**

| Run | Overall macro-F1 | 95% CI | Verdict H1 |
|---|---:|---|---|
| v1 (baseline zero-shot) | 0.543 | [0.513, 0.571] | **NOT SUPPORTED** |
| v2 (perbaikan struktural prompt) | 0.573 | [0.545, 0.600] | **NOT SUPPORTED** |
| **v3 (few-shot 6 exemplar)** | **0.684** | **[0.645, 0.719]** | **INCONCLUSIVE** |

> Lintasan: v1 → v2 (+0.030, perbaikan struktur prompt tanpa menyentuh logika
> labeling) → v3 (+0.111, penambahan 6 exemplar few-shot leakage-safe). Pada v3
> CI menstraddle 0.70 sehingga H1 tidak dapat diterima maupun ditolak.

---

## BAGIAN I — METODOLOGI

### 1. Konfigurasi & Reproduktibilitas

| Parameter | Nilai |
|---|---|
| Model | `qwen3.5:35b` (lokal, Ollama) |
| Digest model (di-pin) | `3460ffeede54` |
| Ollama | `0.30.7` (v3 report mencatat `0.30.8`) |
| Endpoint | `localhost:11434` `/api/chat` |
| temperature | 0 |
| seed | 42 |
| think | False |
| num_ctx | default (v1/v2/v3 prompt aman, lihat §6); v2 extractor default `--num-ctx 32768` |
| Teks input | `full_content_clean` (truncate 16000 char) |
| Subset skor | 72 record (gold `in_scope==Yes` dari 100) |
| Gold standard | `gold_standard.json` (100 record teradjudikasi) — TIDAK diubah |

### 2. Dataset

- `eval_set_100.jsonl` — 100 laporan insiden (subset eval).
- `gold_standard.json` — anotasi gold teradjudikasi untuk 100 record. Hanya
  72 record bertanda `in_scope==Yes` yang diskor (28 di luar cakupan A4).
- `dataset_clean.jsonl` — korpus sumber 642 record. Mengeluarkan 100
  `content_hash` eval menyisakan **542 record leakage-safe** sebagai pool
  exemplar few-shot (lihat §10).

### 3. Skema VERIS A4 yang diekstraksi (15 dimensi yang diskor)

Vocabulary terkontrol VERIS 1.3.x ada di `veris_enums.py` (34 enum, verbatim
dari gold); pemetaan field→enum di `veris_fields.py` (dipakai bersama extractor
& scorer agar tidak drift).

**Single-label (7):** `actor_category`, `action_category`, `asset_category`,
`attr_conf_present`, `attr_integrity_present`, `attr_avail_present`,
`attr_conf_disclosure`.

**Multi-label (8):** `actor_variety`, `actor_motive`, `action_variety`,
`action_vector`, `asset_variety`, `attr_conf_data_variety`,
`attr_integrity_variety`, `attr_avail_variety`.

### 4. Definisi metrik

- **Single-label** (kategori): accuracy + per-class P/R/F1 → macro-F1
  (dilaporkan **incl** & **excl** kelas Unknown, karena Unknown sering dominan).
  CI accuracy via Wilson.
- **Multi-label** (variety/vector): set P/R/F1 per-record (macro-by-record) +
  micro (pooling).
- **Overall macro-F1 (headline)** = rata-rata per-record dari mean F1 atas 15
  dimensi. CI via bootstrap 1000 resample atas record. Uji-t satu sampel
  per-record macro-F1 vs 0.70.
- **Core-A4** = macro-F1 dirata-rata atas 6 dimensi kategori inti
  (`actor/action/asset_category` + 3 flag attribute-present); bootstrap incl &
  excl Unknown; verdict berdasar posisi CI terhadap 0.70.
- **Verdict H1:** SUPPORTED jika seluruh CI ≥ 0.70; NOT SUPPORTED jika seluruh
  CI < 0.70; INCONCLUSIVE jika CI menstraddle 0.70.

### 5. Keputusan metodologis kunci

- **Zero-shot (v1/v2):** prompt hanya berisi schema + vocabulary, TANPA contoh
  berlabel dari korpus (kontrol kebocoran data). Ilustrasi Server/Database pada
  v2 adalah penjelasan skema generik, bukan exemplar korpus.
- **Few-shot (v3):** 6 exemplar dari LUAR eval-100 (leakage-safe), dianotasi
  manual peneliti, disisipkan sebagai giliran user/assistant sebelum query asli.
  Prompt sistem & schema identik dengan v2.
- **`think:false`** dipilih untuk menghindari reasoning trace ~80s/panggilan;
  konsekuensinya Ollama TIDAK menegakkan grammar JSON-schema `format` → nilai di
  luar vocabulary bisa muncul. Schema-compliance jadi besaran terukur nyata
  (by-product RQ2), bukan dipaksa grammar.
- **Validasi di Python = sumber kebenaran.** Nilai off-vocabulary dihitung
  SALAH, tidak di-remap diam-diam.
- **Reproduktibilitas:** temperature 0, seed 42, digest model di-pin & dicatat
  di metrics.

### 6. num_ctx / truncation (dicek 2026-06-13)

TIDAK ada truncation pada default Ollama untuk prompt ini. Ukuran prompt 72
record: max 5029 tok (GS-052), mean 2909; record terpanjang dievaluasi penuh
pada default DAN identik dengan `num_ctx=32768`. v2 extractor default
`--num-ctx 32768` & menyimpan `_prompt_eval_count` per record. Untuk run
few-shot (yang menambah token exemplar, ~8.6k tok) dipakai num_ctx=32768.

---

## BAGIAN II — HASIL

### 7. Hasil Headline lintas versi

| Metrik | v1 | v2 | **v3** |
|---|---:|---:|---:|
| Overall macro-F1 (per-record) | 0.543 | 0.573 | **0.684** |
| — 95% bootstrap CI | [0.513, 0.571] | [0.545, 0.600] | [0.645, 0.719] |
| — t-test vs 0.70 | t=−10.54, p=3.6e-16 | t=−8.93, p=3.2e-13 | t=−0.79, p=0.434 |
| Macro-F1 rata atas 15 dim | 0.460 | 0.494 | 0.605 |
| Schema-violation rate | 2.0% | 0.1% | 0.2% |
| Record di-salvage JSON | 13 | 0 | 0 |
| **Verdict H1** | NOT SUPPORTED | NOT SUPPORTED | **INCONCLUSIVE** |

### 8. Core-A4 (6 dimensi kategori inti)

| Core-A4 | v1 | v2 | **v3** |
|---|---:|---:|---:|
| macro-F1 incl Unknown | 0.423 | 0.480 | 0.528 |
| — 95% CI | [0.367, 0.484] | [0.402, 0.552] | — |
| — Verdict | NOT SUP. | NOT SUP. | — |
| macro-F1 excl Unknown | 0.526 | 0.585 | **0.717** |
| — 95% CI | [0.460, 0.628] | [0.487, 0.691] | [0.620, 0.796] |
| — Verdict | NOT SUP. | NOT SUP. | **INCONCLUSIVE** |

### 9. Per-dimensi lengkap (15 dimensi) — macro-F1

Single-label = macro-F1 (incl Unknown); multi-label = macro-by-record F1.

| Dimensi | Tipe | v1 | v2 | v3 | Δ v2→v3 |
|---|---|---:|---:|---:|---:|
| actor_category | single | 0.527 | 0.573 | 0.628 | +0.055 |
| action_category | single | 0.475 | 0.484 | 0.517 | +0.033 |
| asset_category | single | 0.212 | 0.341 | 0.265 | −0.076 🔴 |
| attr_conf_present | single | 0.308 | 0.641 | 0.649 | +0.008 |
| attr_integrity_present | single | 0.361 | 0.353 | 0.562 | +0.209 🟢 |
| attr_avail_present | single | 0.654 | 0.489 | 0.549 | +0.060 |
| attr_conf_disclosure | single | 0.163 | 0.062 | 0.323 | +0.261 🟢 |
| actor_variety | multi | 0.234 | 0.400 | 0.553 | +0.153 🟢 |
| actor_motive | multi | 0.877 | 0.829 | 0.678 | −0.151 🔴 |
| action_variety | multi | 0.121 | 0.149 | 0.654 | +0.505 🟢 |
| action_vector | multi | 0.131 | 0.150 | 0.567 | +0.417 🟢 |
| asset_variety | multi | 0.368 | 0.579 | 0.580 | +0.001 |
| attr_conf_data_variety | multi | 0.705 | 0.719 | 0.766 | +0.047 |
| attr_integrity_variety | multi | 0.875 | 0.861 | 0.886 | +0.025 |
| attr_avail_variety | multi | 0.884 | 0.782 | 0.898 | +0.116 🟢 |

🟢 ≥ +0.10 🔴 ≤ −0.05

### 10. Detail single-label v3 (run final)

| Dimensi | Acc | Acc 95% CI (Wilson) | F1 incl Unk | F1 excl Unk | micro-F1 |
|---|---:|---|---:|---:|---:|
| actor_category | 75.0% | [63.9%, 83.6%] | 0.628 | 0.774 | 0.750 |
| action_category | 41.7% | [31.0%, 53.2%] | 0.517 | 0.647 | 0.417 |
| asset_category | 63.9% | [52.4%, 74.0%] | 0.265 | 0.354 | 0.639 |
| attr_conf_present | 90.3% | [81.3%, 95.2%] | 0.649 | 0.974 | 0.903 |
| attr_integrity_present | 81.9% | [71.5%, 89.1%] | 0.562 | 0.732 | 0.819 |
| attr_avail_present | 84.7% | [74.7%, 91.2%] | 0.549 | 0.823 | 0.847 |
| attr_conf_disclosure | 30.6% | [21.1%, 42.0%] | 0.323 | 0.403 | 0.306 |

### 11. Detail multi-label v3 (run final)

| Dimensi | macro-P | macro-R | macro-F1 | micro-F1 |
|---|---:|---:|---:|---:|
| actor_variety | 0.569 | 0.546 | 0.553 | 0.547 |
| actor_motive | 0.694 | 0.669 | 0.678 | 0.703 |
| action_variety | 0.667 | 0.649 | 0.654 | 0.636 |
| action_vector | 0.569 | 0.565 | 0.567 | 0.571 |
| asset_variety | 0.625 | 0.559 | 0.580 | 0.562 |
| attr_conf_data_variety | 0.812 | 0.754 | 0.766 | 0.742 |
| attr_integrity_variety | 0.889 | 0.884 | 0.886 | 0.455 |
| attr_avail_variety | 0.903 | 0.896 | 0.898 | 0.316 |

### 12. Per-sektor (v3)

| Sektor | n | macro-F1 |
|---|---:|---:|
| government | 53 | 0.671 |
| financial | 7 | 0.774 |
| telco | 3 | 0.800 |
| education_healthcare | 4 | 0.694 |
| unknown | 5 | 0.618 |

> ⚠️ telco (n=3) & education_healthcare (n=4) sangat kecil → indikatif saja.

---

## BAGIAN III — ANALISIS & CATATAN RUN

### 13. Kejadian saat run (untuk bagian Methods thesis)

- **v1 — salvage JSON:** 13/72 record gagal JSON karena model menulis field
  `rationale` (tak diskor, paling akhir) tanpa tanda kutik pembuka. Diatasi
  dengan `salvage_json()` deterministik: buang segmen mulai `"rationale"`, parse
  sisanya. TIDAK ada pemanggilan model ulang (raw tersimpan, model
  deterministik). Ditandai `_salvaged` per-record.
- **v1 — off-vocab asset_category:** model sering menaruh `Database` (sebuah
  *variety*) di slot `asset_category` (18× → 25% violation pada dimensi itu).
- **v2 — dua perubahan STRUKTURAL saja** pada SYSTEM_PROMPT: (a) aturan tegas
  pemisahan CATEGORY vs VARIETY untuk actor/action/asset + ilustrasi
  Server/Database; (b) `rationale` dihapus dari output wajib & dari `format`
  schema. Tidak menyentuh logika labeling. Hasil: salvage 0, off-vocab
  `asset_category` 0, schema-violation 2.0% → 0.1%, `asset_category` acc
  37.5% → 66.7%.
- **v3 — re-run karena exemplar cacat:** v3 pertama membiarkan
  `action_vector=[]` di mayoritas exemplar → model ikut under-predict (F1
  action_vector anjlok ke **0.042**, overall 0.650). Peneliti mengoreksi
  `fewshot_exemplars.json` (action_vector terisi di keenam exemplar; field
  confidentiality FS-01) → action_vector **0.567**, overall **0.684**. Run cacat
  diarsipkan di `_v3_old_flawed/`.
- **Lingkungan:** `numpy`/`scipy` belum terpasang → diinstal ke `/venv/main`;
  scorer dijalankan dengan `/venv/main/bin/python`. Extractor hanya pakai stdlib.

### 14. Few-shot: exemplar & pool

- 6 exemplar final: **FS-01, FS-02, FS-04, FS-05, FS-06, FS-07** dari
  `fewshot_exemplars.json` (kandidat di `fewshot_candidates.json`, FS-01..FS-08).
- Pool leakage-safe: 542 record (`dataset_clean.jsonl` minus 100 eval
  `content_hash`). Insiden tunggal bersih tersedia untuk Malware/ransomware
  (PDNS2 Brain Cipher), Hacking/data-sold (Tokopedia, KPU, BRI Life,
  universitas), DoS (bank sentral), Misuse/insider (Telkomsel/Denny Siregar).
  Insiden tunggal **Phishing** & **Misconfiguration** langka di luar eval
  (korpus didominasi "data dijual di dark web"). 7 record `vcdb` = insiden VERIS
  confidence tinggi. **cid TIDAK stabil** antar re-filtering — anchor pada
  `content_hash`.
- **Pelajaran few-shot (penting):** kualitas anotasi exemplar berpengaruh
  besar — label `[]` di sebuah field exemplar MENGAJARI model untuk
  under-predict field itu (terbukti pada action_vector 0.042 → 0.567 setelah
  dikoreksi). Trade-off: few-shot membiaskan `actor_motive` ke "Financial" (5/6
  exemplar bermotif Financial/Ideology) → regresi 0.829 → 0.678.

### 15. Kesimpulan

- **H1 (F1 ≥ 0.70):** TIDAK didukung pada v1 & v2 (seluruh CI < 0.70). Pada
  **v3 few-shot menjadi INCONCLUSIVE** — overall 0.684 (CI [0.645, 0.719]) dan
  Core-A4 excl-Unknown 0.717 (CI [0.620, 0.796]) keduanya menstraddle 0.70;
  bukti belum cukup untuk menerima maupun menolak.
- Lompatan terbesar few-shot terjadi pada dimensi yang dulu terlemah
  (`action_variety` +0.505, `action_vector` +0.417, `attr_conf_disclosure`
  +0.261).
- Perbaikan struktural v2 menaikkan kualitas output tanpa menyentuh logika
  labeling (schema-violation 2.0% → 0.1%, salvage 13 → 0).
- **Gap tersisa ke 0.70** didominasi `asset_category` (F1 0.265, ketuker dengan
  asset_variety), `attr_conf_disclosure` (acc 31%), `action_category` (acc 42%);
  few-shot juga memunculkan trade-off regresi `actor_motive`.

---

## Lampiran — File output

| Run | predictions | metrics | metrics core | report | errors |
|---|---|---|---|---|---|
| v1 | `predictions_seed42.json` | `metrics_seed42.json` | `metrics_core_seed42.json` | `report_seed42.md` | `errors_seed42.csv` |
| v2 | `predictions_v2_seed42.json` | `metrics_v2_seed42.json` | `metrics_core_v2_seed42.json` | `report_v2_seed42.md` | `errors_v2_seed42.csv` |
| v3 | `predictions_v3_fewshot_seed42.json` | `metrics_v3_seed42.json` | `metrics_core_v3_seed42.json` | `report_v3_seed42.md` + `report_v3_compare.md` | `errors_v3_seed42.csv` |

**Kode:** `veris_enums.py`, `veris_fields.py`, `extract_qwen.py` (v1),
`extract_qwen_v2.py` (v2), `extract_qwen_fewshot.py` (v3), `score_rq1.py`
(skor utama), `score_core.py` (Core-A4). Exemplar: `fewshot_candidates.json`,
`fewshot_exemplars.json`. Run cacat: `_v3_old_flawed/`.
