# Regulasi Q&A Assistant (RAG)

Asisten tanya-jawab dokumen regulasi berbahasa Indonesia berbasis **Retrieval-Augmented Generation (RAG)**. Sistem ini membaca dokumen PDF, memecahnya berdasarkan struktur `Pasal`, menyimpan embedding-nya di ChromaDB, lalu mengambil potongan dokumen yang paling relevan untuk menjawab pertanyaan pengguna.

Jawaban dari LLM dibatasi oleh konteks dokumen yang ditemukan dan diarahkan untuk menyertakan sitasi pasal. Jika konteks tidak memuat jawaban, sistem diarahkan untuk mengembalikan:

```text
Informasi tidak ditemukan dalam dokumen.
```

> **Penting:** Proyek ini adalah alat bantu pencarian informasi, bukan nasihat hukum.

## Fitur

- Ekstraksi teks dari PDF menggunakan `pypdf`.
- Pemotongan dokumen berdasarkan judul pasal, misalnya `Pasal 12` atau `Pasal 12A`.
- Pemotongan lanjutan untuk pasal yang terlalu panjang menggunakan LangChain text splitter.
- Embedding multilingual menggunakan `intfloat/multilingual-e5-small`.
- Penyimpanan dan pencarian vector menggunakan ChromaDB dengan cosine distance.
- Jawaban berbasis konteks menggunakan Anthropic Claude.
- Mode tanpa LLM untuk menguji retrieval tanpa API key.
- Interface terminal melalui `ask.py`.
- REST API menggunakan FastAPI.
- UI web menggunakan Streamlit.
- Evaluasi retrieval menggunakan Hit Rate@k dan MRR@k.
- Deployment menggunakan Docker Compose.

## Arsitektur

```text
                  Proses indexing

PDF regulasi ──► ekstraksi teks ──► split per Pasal ──► chunking
                                                        │
                                                        ▼
                                             embedding E5 multilingual
                                                        │
                                                        ▼
                                                    ChromaDB

                  Proses menjawab pertanyaan

Pertanyaan ──► embedding query ──► pencarian chunk relevan ──► konteks
                                                               │
                                                               ▼
                                                     Anthropic Claude
                                                               │
                                                               ▼
                                               jawaban + sumber Pasal
```

## Struktur proyek

| File/folder | Fungsi |
|---|---|
| `rag_core.py` | Logika utama ekstraksi, chunking, embedding, indexing, retrieval, dan generation. |
| `ingest.py` | Membangun index ChromaDB dari PDF di folder `data/`. |
| `ask.py` | Mengajukan pertanyaan melalui terminal. |
| `evaluate.py` | Membandingkan konfigurasi chunk size dan nilai `k`. |
| `api.py` | Backend FastAPI dengan endpoint `/health` dan `/ask`. |
| `app.py` | Antarmuka web Streamlit. |
| `eval/eval_set.csv` | Dataset pertanyaan evaluasi. Saat ini perlu diisi dengan pertanyaan nyata. |
| `Dockerfile` | Image Python untuk menjalankan aplikasi. |
| `docker-compose.yml` | Menjalankan service API dan UI. |
| `requirements.txt` | Daftar dependensi Python. |
| `chroma_db/` | Index vector lokal yang dibuat setelah ingest; tidak di-commit. |
| `results/` | Hasil evaluasi; tidak di-commit. |

## Persyaratan

- Python 3.10 atau lebih baru; proyek ini telah diuji pada Python 3.11.
- Git, opsional.
- Docker Desktop, opsional.
- Koneksi internet saat pertama kali mengunduh model embedding.
- API key Anthropic jika ingin menggunakan jawaban generatif dari Claude.

## Instalasi

### Menggunakan Conda

Buat atau gunakan environment Python 3.11:

```powershell
conda activate py311-ml
```

Jika `conda activate` belum bekerja di PowerShell, gunakan `conda run` pada setiap perintah:

```powershell
conda run --no-capture-output -n py311-ml python --version
```

Pasang dependensi:

```powershell
python -m pip install -r requirements.txt
```

Atau tanpa aktivasi environment:

```powershell
conda run -n py311-ml python -m pip install -r requirements.txt
```

Verifikasi dependensi utama:

```powershell
python -c "import chromadb, sentence_transformers, fastapi, streamlit; print('Dependensi OK')"
```

### Konfigurasi environment

Buat file `.env` di root proyek. Repository ini mengabaikan `.env` melalui `.gitignore`, sehingga API key tidak ikut di-commit.

Contoh isi `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-api-key-anda
LLM_MODEL=claude-haiku-5-5
EMBED_MODEL=intfloat/multilingual-e5-small
CHROMA_DIR=chroma_db
COLLECTION=regulasi
```

`ANTHROPIC_API_KEY` harus berupa API key Anthropic yang valid. Jika tidak diisi, pipeline tetap dapat menjalankan retrieval dalam mode tanpa LLM.

Jangan membagikan atau meng-commit file `.env`.

## Menyiapkan dokumen

1. Buat folder `data/` jika belum ada.
2. Letakkan satu atau lebih PDF regulasi di dalamnya.
3. Gunakan PDF yang teksnya dapat diseleksi, bukan PDF scan gambar tanpa OCR.

Contoh:

```text
data/
└── uu_pelindungan_data_pribadi.pdf
```

Sistem mengenali pasal jika judulnya berdiri sendiri pada satu baris, misalnya:

```text
Pasal 12
```

Jika format PDF berbeda, sistem menggunakan fallback tanpa label pasal. Retrieval masih dapat berjalan, tetapi evaluasi berbasis nomor pasal dan sitasi pasal tidak akan optimal.

## Membangun index

Jalankan dari root proyek:

```powershell
python -u .\ingest.py
```

Jika environment belum aktif:

```powershell
conda run --no-capture-output -n py311-ml python -u .\ingest.py
```

Output yang diharapkan:

```text
Selesai: N chunk dari 1 file masuk ke collection 'regulasi'.
```

Index disimpan di folder `chroma_db/`. Ukuran chunk dan overlap dapat diatur:

```powershell
python -u .\ingest.py --chunk-size 1000 --overlap 150
```

Untuk memilih PDF atau collection tertentu:

```powershell
python -u .\ingest.py --pdf data\uu_pdp.pdf --collection regulasi
```

Index utama akan di-reset dan dibangun ulang setiap kali `ingest.py` dijalankan secara default.

## Mengajukan pertanyaan melalui terminal

```powershell
python -u .\ask.py "Apa saja hak subjek data pribadi?" --k 4
```

Parameter `--k` menentukan jumlah chunk konteks yang diambil dari ChromaDB.

Contoh output akan memuat:

- jawaban atau potongan teks teratas,
- mode `llm` atau `extractive`,
- daftar sumber pasal,
- cosine distance setiap hasil.

Jika API key belum tersedia, output akan menunjukkan `mode extractive` dan awalan `[mode tanpa LLM]`. Ini berarti sistem hanya menampilkan chunk paling relevan tanpa membuat ringkasan oleh Claude.

## Menjalankan API

Jalankan FastAPI dengan Uvicorn:

```powershell
python -m uvicorn api:app --reload
```

Atau menggunakan environment Conda secara langsung:

```powershell
conda run --no-capture-output -n py311-ml python -m uvicorn api:app --reload
```

Endpoint yang tersedia:

### `GET /health`

Memeriksa status aplikasi dan menampilkan model embedding serta model LLM yang dikonfigurasi.

### `POST /ask`

Request:

```json
{
  "question": "Pasal berapa yang menjelaskan pengendali wajib memusnahkan data pribadi?",
  "k": 4
}
```

Contoh menggunakan PowerShell:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:8000/ask `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"Apa saja hak subjek data pribadi?","k":4}'
```

Dokumentasi interaktif tersedia di:

```text
http://localhost:8000/docs
```

## Menjalankan UI Streamlit

Jika API berjalan di `http://localhost:8000`, buka terminal kedua dan jalankan:

```powershell
$env:API_URL="http://localhost:8000"
streamlit run .\app.py
```

Tanpa aktivasi environment:

```powershell
$env:API_URL="http://localhost:8000"
conda run --no-capture-output -n py311-ml streamlit run .\app.py
```

Buka UI di:

```text
http://localhost:8501
```

UI menyediakan input pertanyaan, pengaturan jumlah chunk `k`, jawaban, dan daftar sumber yang digunakan.

Jika `API_URL` tidak diisi, `app.py` dapat menjalankan pipeline `rag_core` secara langsung. Untuk setup yang lebih rapi, gunakan API sebagai backend seperti pada contoh di atas.

## Evaluasi retrieval

Isi `eval/eval_set.csv` dengan pertanyaan yang dibuat berdasarkan dokumen asli. Formatnya:

```csv
question,gold_pasal,answerable
"Apa saja hak subjek data pribadi?","5;6",yes
"Pasal mana yang mengatur kewajiban pengendali?","20",yes
"Berapa harga minyak dunia tahun ini?",,no
```

Keterangan kolom:

- `question`: pertanyaan natural language.
- `gold_pasal`: nomor pasal yang memuat jawaban; pisahkan beberapa pasal dengan `;`.
- `answerable`: `yes` jika dokumen memuat jawabannya, `no` jika tidak.

Disarankan menggunakan 20–30 pertanyaan, termasuk 4–6 pertanyaan yang sengaja tidak dapat dijawab dari dokumen.

Jalankan perbandingan konfigurasi:

```powershell
python -u .\evaluate.py --chunk-sizes 500 1000 1500 --ks 1 3 5
```

Hasil disimpan di:

```text
results/retrieval_results.csv
```

Metrik yang dihitung:

- **Hit Rate@k:** persentase pertanyaan answerable yang menemukan pasal benar pada `k` hasil teratas.
- **MRR@k:** memperhitungkan peringkat hasil benar; pasal benar di peringkat lebih tinggi mendapat skor lebih baik.

Untuk menghasilkan jawaban LLM pada konfigurasi terbaik:

```powershell
python -u .\evaluate.py --with-llm
```

Hasil jawaban disimpan di:

```text
results/answers_for_grading.csv
```

Isi kolom `manual_grade` secara manual dengan `benar`, `sebagian`, atau `salah` setelah membandingkan jawaban dengan dokumen asli.

## Menjalankan dengan Docker

Pastikan index sudah dibuat sebelum menjalankan container:

```powershell
python -u .\ingest.py
docker compose up --build
```

Service yang tersedia:

| Service | URL |
|---|---|
| API | `http://localhost:8000` |
| Dokumentasi API | `http://localhost:8000/docs` |
| Streamlit UI | `http://localhost:8501` |

`docker-compose.yml` memasang folder lokal `chroma_db/` ke container API dan menggunakan volume cache untuk model Hugging Face.

## Troubleshooting

### `ModuleNotFoundError: No module named 'chromadb'`

Python yang digunakan kemungkinan bukan environment `py311-ml`. Verifikasi:

```powershell
python -c "import sys; print(sys.executable)"
```

Atau jalankan langsung dengan environment yang benar:

```powershell
conda run --no-capture-output -n py311-ml python -u .\ingest.py
```

### `Taruh minimal satu PDF di folder data/ dulu.`

Belum ada PDF di folder `data/`. Tambahkan minimal satu file `.pdf` lalu ulangi indexing.

### `Tidak ada teks yang berhasil diekstrak dari PDF.`

PDF kemungkinan berupa scan gambar atau teksnya tidak dapat diekstrak. Gunakan PDF dengan selectable text atau lakukan OCR terlebih dahulu.

### Semua hasil tidak memiliki nomor pasal

Judul pasal tidak cocok dengan pola yang digunakan sistem. Pastikan judul seperti `Pasal 12` berdiri sendiri pada satu baris. Jika tidak, regex `PASAL_RE` di `rag_core.py` perlu disesuaikan.

### `Collection ... does not exist`

Jalankan `ingest.py` terlebih dahulu, dan pastikan nama collection sama dengan nilai `COLLECTION` di `.env`.

### `anthropic.AuthenticationError: Invalid bearer token`

`ANTHROPIC_API_KEY` terbaca tetapi tidak valid. Periksa bahwa `.env` berisi API key Anthropic yang aktif, bukan placeholder atau token dari layanan lain. Setelah mengubah `.env`, jalankan ulang proses API atau perintah terminal.

### Jawaban selalu menggunakan mode tanpa LLM

`ANTHROPIC_API_KEY` belum terbaca. Pastikan file bernama `.env`, berada di root proyek, lalu cek tanpa menampilkan key:

```powershell
python -c "import os; print(bool(os.getenv('ANTHROPIC_API_KEY')))"
```

### Model Hugging Face lambat di awal

Model embedding diunduh dan dimuat saat pertama kali dipakai. Proses berikutnya biasanya lebih cepat karena model sudah berada di cache lokal.

## Keterbatasan

- Kualitas retrieval bergantung pada kualitas ekstraksi teks PDF.
- Dokumen scan memerlukan OCR terlebih dahulu.
- Deteksi pasal bergantung pada format judul pasal yang konsisten.
- Dataset evaluasi masih perlu dibuat dan diisi secara manual.
- Hasil evaluasi dengan 20–30 pertanyaan bersifat indikatif, bukan bukti statistik yang kuat.
- Pertanyaan yang jawabannya tersebar di banyak pasal dapat membutuhkan retrieval dan reasoning yang lebih baik.
- Belum tersedia reranker, hybrid search BM25, atau threshold similarity khusus untuk menolak pertanyaan yang tidak relevan.
- Mode tanpa LLM menampilkan chunk teratas dan belum melakukan penolakan semantik secara penuh.
- Jawaban tidak boleh diperlakukan sebagai nasihat atau keputusan hukum.

## Pengembangan lanjutan

Beberapa pengembangan yang dapat dilakukan:

- Menambahkan reranker berbasis cross-encoder.
- Menggabungkan vector search dengan BM25 melalui hybrid search.
- Menambahkan threshold cosine distance untuk meningkatkan perilaku abstain.
- Membandingkan beberapa model embedding bahasa Indonesia atau multilingual.
- Menambahkan dukungan metadata dokumen, tanggal, jenis regulasi, dan sumber resmi.
- Menambahkan pengujian otomatis untuk chunking, retrieval, dan endpoint API.
- Menyediakan OCR untuk dokumen regulasi berbentuk scan.

## Data dan keamanan

Dokumen PDF sumber tidak disertakan oleh repository ini. Gunakan dokumen dari sumber resmi dan perhatikan lisensi atau ketentuan redistribusinya.

Jangan commit file berikut:

- `.env` dan API key.
- PDF regulasi jika tidak memiliki izin redistribusi.
- `chroma_db/`.
- `results/` yang berisi hasil eksperimen lokal.

Aturan tersebut sudah dicantumkan di `.gitignore`.

## Lisensi dan disclaimer

Tambahkan lisensi proyek sesuai kebutuhan sebelum dipublikasikan. Proyek ini hanya untuk tujuan pembelajaran dan pencarian informasi. Selalu periksa dokumen regulasi asli dan konsultasikan kepada profesional hukum untuk keputusan yang memerlukan nasihat hukum.
