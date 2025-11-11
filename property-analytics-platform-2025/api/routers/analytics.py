from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

from ...analytics_engine.core.db import init_schema, insert_document, insert_chunks, semantic_search
from ...ai_engine.llm.embedding_client import embed_texts
from ...ai_engine.rag.chunking_v2 import split_text

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"analytics": "ok"}

@router.post("/init-db")
async def init_db():
    try:
        init_schema()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UploadTextRequest(BaseModel):
    file_name: str = Field(..., description="Logical name for the document")
    text: str = Field(..., description="Raw text content")

@router.post("/upload-text")
async def upload_text(body: UploadTextRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    # Create doc
    doc_id = insert_document(body.file_name, body.text)
    # Chunk + embed
    chunks = split_text(body.text)
    vectors = embed_texts(chunks)
    n = insert_chunks(doc_id, chunks, vectors)
    return {"document_id": doc_id, "chunks": n}

class SearchRequest(BaseModel):
    query: str
    top_k: int = 8

@router.post("/search")
async def search(body: SearchRequest):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Empty query")
    qv = embed_texts([body.query])[0]
    rows = semantic_search(qv, top_k=body.top_k)
    return {"results": rows}


