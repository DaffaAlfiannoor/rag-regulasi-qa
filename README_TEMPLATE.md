# Regulasi Q&A Assistant (RAG)

A retrieval-augmented generation (RAG) assistant that answers questions about [nama dokumen] in Indonesian, with article-level citations and a "not found" fallback for questions the document does not cover.

## Features
- Article-aware chunking of legal PDFs (`Pasal` boundaries), with LangChain text splitters for long articles
- Multilingual embeddings from Hugging Face (`intfloat/multilingual-e5-small`) stored in ChromaDB
- LLM answers grounded only in retrieved context, with cited articles
- Evaluation harness: hit rate@k and MRR across chunk sizes and top-k, plus abstention checks
- FastAPI backend, Streamlit UI, Docker Compose deployment

## Architecture
[Tempel diagram atau jelaskan alur: PDF -> chunk -> embedding -> ChromaDB -> retrieve -> LLM -> answer + citations]

## Evaluation
Test set: [N] hand-written questions ([A] answerable, [U] unanswerable), each labeled with the gold article(s).

| Chunk size | k | Hit rate | MRR |
|---|---|---|---|
| [...] | [...] | [...] | [...] |

Findings:
- [Konfigurasi terbaik dan alasannya]
- [Jenis pertanyaan yang paling sering gagal]
- [Hasil abstain: benar pada pertanyaan tak terjawab, salah pada pertanyaan terjawab]

## Quickstart
```bash
pip install -r requirements.txt
cp .env.example .env            # add your API key
# put the PDF in data/
python ingest.py
python ask.py "your question"
uvicorn api:app --reload
streamlit run app.py
```

Docker: `python ingest.py && docker compose up --build`

## Limitations
- [Ukuran test set kecil, hasil indikatif]
- [Hanya satu dokumen; pertanyaan lintas-pasal masih lemah]
- Not legal advice.

## Data notice
The source document is not redistributed here. Get it from [tautan sumber resmi].
