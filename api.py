"""FastAPI service.  Jalankan: uvicorn api:app --reload"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import rag_core as rc

app = FastAPI(title="Regulasi Q&A (RAG)")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    k: int = Field(4, ge=1, le=10)


@app.get("/health")
def health():
    return {"status": "ok", "embed_model": rc.EMBED_MODEL, "llm_model": rc.LLM_MODEL}


@app.post("/ask")
def ask(req: AskRequest):
    try:
        return rc.answer(req.question, rc.DEFAULT_COLLECTION, req.k)
    except Exception as e:  # collection belum dibuat, API key salah, dll.
        raise HTTPException(status_code=500, detail=str(e))
