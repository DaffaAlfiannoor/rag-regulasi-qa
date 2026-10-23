"""Inti pipeline RAG: baca PDF -> chunk per pasal -> embedding -> Chroma -> retrieve -> jawab."""
import hashlib
import os
import re
from functools import lru_cache
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

load_dotenv()

EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")
DEFAULT_COLLECTION = os.getenv("COLLECTION", "regulasi")

NOT_FOUND = "Informasi tidak ditemukan dalam dokumen."

# Judul pasal berdiri sendiri di satu baris, misalnya "Pasal 12" atau "Pasal 12A".
PASAL_RE = re.compile(r"(?m)^\s*Pasal\s+(\d+[A-Z]?)\s*$")

SYSTEM_PROMPT = f"""Kamu adalah asisten tanya-jawab untuk dokumen regulasi berbahasa Indonesia.
Aturan:
1. Jawab HANYA berdasarkan konteks yang diberikan. Jangan memakai pengetahuan di luar konteks.
2. Sebutkan pasal rujukan di akhir kalimat terkait, dengan format (Pasal X).
3. Jika konteks tidak memuat jawabannya, jawab persis: "{NOT_FOUND}"
4. Jawab ringkas dalam bahasa Indonesia. Ini bukan nasihat hukum."""


# ---------- Embedding ----------
@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed_passages(texts):
    # Model E5 mewajibkan prefix "passage: " untuk dokumen dan "query: " untuk pertanyaan.
    model = get_embedder()
    vecs = model.encode(
        [f"passage: {t}" for t in texts],
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 50,
    )
    return vecs.tolist()


def embed_query(question):
    model = get_embedder()
    return model.encode([f"query: {question}"], normalize_embeddings=True)[0].tolist()


# ---------- Load & chunk ----------
def load_pdf_text(path):
    reader = PdfReader(str(path))
    pages = [(p.extract_text() or "") for p in reader.pages]
    text = "\n".join(pages).replace("\x00", "")
    return re.sub(r"\n{3,}", "\n\n", text)


def split_by_pasal(text):
    """Return list of (label_pasal_or_None, body_without_heading)."""
    matches = list(PASAL_RE.finditer(text))
    if len(matches) < 5:  # format tidak terdeteksi -> fallback tanpa label pasal
        return [(None, text)]
    parts = []
    pre = text[: matches[0].start()].strip()
    if pre:
        parts.append(("PEMBUKAAN", pre))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if body:
            parts.append((m.group(1).upper(), body))
    return parts


def chunk_document(text, source, chunk_size=1000, overlap=150):
    overlap = min(overlap, chunk_size // 2)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for pasal, body in split_by_pasal(text):
        for idx, piece in enumerate(splitter.split_text(body)):
            if pasal and pasal != "PEMBUKAAN":
                content = f"Pasal {pasal}\n{piece}"  # heading ditempel ke setiap chunk
            else:
                content = piece
            uid = hashlib.sha1(f"{source}|{pasal}|{idx}|{content[:50]}".encode()).hexdigest()
            chunks.append(
                {
                    "id": uid,
                    "text": content,
                    "meta": {"source": source, "pasal": pasal or "", "chunk_idx": idx},
                }
            )
    return chunks


# ---------- Index & retrieve ----------
def _client():
    return chromadb.PersistentClient(path=CHROMA_DIR)


def build_index(pdf_paths, collection=DEFAULT_COLLECTION, chunk_size=1000, overlap=150, reset=True):
    client = _client()
    if reset:
        try:
            client.delete_collection(collection)
        except Exception:
            pass
    col = client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})
    chunks = []
    for p in pdf_paths:
        p = Path(p)
        chunks += chunk_document(load_pdf_text(p), p.name, chunk_size, overlap)
    if not chunks:
        raise ValueError("Tidak ada teks yang berhasil diekstrak dari PDF.")
    batch = 128
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        col.add(
            ids=[c["id"] for c in part],
            documents=[c["text"] for c in part],
            embeddings=embed_passages([c["text"] for c in part]),
            metadatas=[c["meta"] for c in part],
        )
    return len(chunks)


def retrieve(question, collection=DEFAULT_COLLECTION, k=4):
    col = _client().get_collection(collection)
    res = col.query(
        query_embeddings=[embed_query(question)],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append(
            {
                "text": doc,
                "pasal": meta.get("pasal") or None,
                "source": meta.get("source"),
                "distance": float(dist),  # cosine distance: makin kecil makin mirip
            }
        )
    return hits


# ---------- Generation ----------
def _format_context(hits):
    blocks = []
    for h in hits:
        label = f"Pasal {h['pasal']}" if h["pasal"] else h["source"]
        blocks.append(f"[{label}]\n{h['text']}")
    return "\n\n---\n\n".join(blocks)


def answer(question, collection=DEFAULT_COLLECTION, k=4):
    hits = retrieve(question, collection, k)
    if not os.getenv("ANTHROPIC_API_KEY"):
        # Mode tanpa LLM: tampilkan potongan teratas apa adanya (berguna untuk tes retrieval).
        top = hits[0]["text"] if hits else NOT_FOUND
        return {"answer": f"[mode tanpa LLM] {top}", "sources": hits, "mode": "extractive"}

    import anthropic

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=LLM_MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Konteks:\n{_format_context(hits)}\n\nPertanyaan: {question}",
            }
        ],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    return {"answer": text, "sources": hits, "mode": "llm"}
