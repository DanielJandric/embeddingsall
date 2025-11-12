from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

from ...analytics_engine.core.db import init_schema, insert_document, insert_chunks, semantic_search, hybrid_search
from ...ai_engine.llm.embedding_client import embed_texts
from ...ai_engine.rag.chunking_v2 import split_text
from ...config.settings import settings

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
    mode: str = "hybrid"  # "semantic" or "hybrid"
    semantic_weight: float | None = None
    fulltext_weight: float | None = None
    rerank: bool = False
    rerank_top_k: int | None = None
    rerank_model: str | None = None

@router.post("/search")
async def search(body: SearchRequest):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Empty query")
    qv = embed_texts([body.query])[0]
    if body.mode == "semantic":
        rows = semantic_search(qv, top_k=body.top_k)
    else:
        rows = hybrid_search(
            query_text=body.query,
            query_embedding=qv,
            top_k=body.top_k,
            semantic_weight=body.semantic_weight if body.semantic_weight is not None else settings.semantic_weight,
            fulltext_weight=body.fulltext_weight if body.fulltext_weight is not None else settings.fulltext_weight,
        )
    # Optional reranking with LLM (uses larger model quality)
    if body.rerank and rows:
        from ...ai_engine.rag.reranker import rerank_with_openai
        # Convert rows (list[dict]) to expected format: ensure 'content' key exists
        candidates = []
        for r in rows:
            # SQL may use 'content' column name; ensure presence
            content = r.get("content") or r.get("chunk_content") or r.get("text") or ""
            rr = dict(r)
            rr["content"] = content
            candidates.append(rr)
        top_k = body.rerank_top_k if body.rerank_top_k is not None else body.top_k
        rows = rerank_with_openai(
            query=body.query,
            candidates=candidates,
            content_key="content",
            top_k=top_k,
            model=body.rerank_model,
        )
    return {"results": rows}

@router.post("/reindex-all")
async def reindex_all(limit: int = 0, offset: int = 0):
    """
    Re-chunk & re-embed all documents in property_documents.
    If limit>0, process only first N docs.
    """
    from ...analytics_engine.core.db import get_conn
    cnt = 0
    with get_conn() as conn:
        cur = conn.cursor()
        if limit and limit > 0:
            cur.execute(
                "SELECT id, file_name, full_text FROM property_documents ORDER BY id ASC LIMIT %s OFFSET %s;",
                (limit, max(0, offset)),
            )
        else:
            cur.execute("SELECT id, file_name, full_text FROM property_documents ORDER BY id ASC;")
        rows = cur.fetchall()
        for (doc_id, file_name, full_text) in rows:
            # Delete existing chunks
            cur.execute("DELETE FROM property_chunks WHERE document_id = %s;", (doc_id,))
            # Recreate
            chunks = split_text(full_text or "")
            vectors = embed_texts(chunks) if chunks else []
            if chunks:
                insert_chunks(doc_id, chunks, vectors)
                cnt += 1
    return {"reindexed_documents": cnt}


@router.post("/import-from-existing")
async def import_from_existing(limit: int = 100, offset: int = 0):
    """
    Import documents from existing Supabase table `documents_full` into `property_documents`,
    mapping (file_name, full_content -> file_name, full_text). Skips duplicates by file_name.
    """
    from ...analytics_engine.core.db import get_conn
    imported = 0
    with get_conn() as conn:
        cur = conn.cursor()
        # Ensure source table exists and is compatible
        try:
            # Fetch at most `limit` rows at the SQL level to avoid huge transfers
            cur.execute(
                "SELECT id, file_name, full_content FROM documents_full ORDER BY id ASC LIMIT %s OFFSET %s;",
                (max(1, limit), max(0, offset)),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"documents_full not accessible: {e}")
        rows = cur.fetchall()
        for (_src_id, file_name, full_content) in rows:
            # Skip empty content
            if not full_content:
                continue
            # Avoid duplicate by file_name
            cur.execute("SELECT id FROM property_documents WHERE file_name = %s;", (file_name,))
            exists = cur.fetchone()
            if exists:
                continue
            cur.execute(
                "INSERT INTO property_documents (file_name, full_text) VALUES (%s, %s);",
                (file_name, full_content),
            )
            imported += 1
    return {"imported_documents": imported}

