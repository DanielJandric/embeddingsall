from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterable, List, Optional, Tuple

from psycopg import Connection, sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ...config.settings import settings
from ...data_pipeline.vector_store.pgvector_manager import build_hnsw_sql

_pool: Optional[ConnectionPool] = None

def get_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    dsn = settings.database_url
    if not dsn:
        # Try to assemble from Supabase variables if provided
        supa_url = settings.supabase_url
        supa_key = settings.supabase_service_key
        if supa_url and supa_key:
            # Fallback DSN not trivial to derive; require DATABASE_URL for production
            raise ValueError("DATABASE_URL not set. Please provide DATABASE_URL for PostgreSQL.")
        raise ValueError("DATABASE_URL is required")
    _pool = ConnectionPool(dsn, min_size=1, max_size=10, kwargs={"autocommit": True})
    return _pool

@contextmanager
def get_conn() -> Iterable[Connection]:
    pool = get_pool()
    with pool.connection() as conn:
        yield conn

def init_schema() -> None:
    """Create required extensions, tables, and indexes if not present."""
    with get_conn() as conn:
        cur = conn.cursor()
        # Extensions
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

        # Documents table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS property_documents (
                id BIGSERIAL PRIMARY KEY,
                file_name TEXT,
                full_text TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # Chunks table with pgvector embedding
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS property_chunks (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT REFERENCES property_documents(id) ON DELETE CASCADE,
                chunk_index INT,
                content TEXT,
                chunk_size INT NOT NULL,
                embedding vector(1536),
                search_vector tsvector,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # GIN index for full-text search
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_property_chunks_fts ON property_chunks USING GIN (search_vector);"
        )
        # HNSW vector index
        cur.execute(build_hnsw_sql(table="property_chunks", column="embedding"))

def insert_document(file_name: str, full_text: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "INSERT INTO property_documents (file_name, full_text) VALUES (%s, %s) RETURNING id;",
            (file_name, full_text),
        )
        doc_id = cur.fetchone()["id"]
        return int(doc_id)

def insert_chunks(document_id: int, chunks: List[str], embeddings: List[List[float]]) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")
    with get_conn() as conn:
        cur = conn.cursor()
        rows = []
        for idx, (content, emb) in enumerate(zip(chunks, embeddings)):
            rows.append(
                (
                    document_id,
                    idx,
                    content,
                    len(content),
                    emb,
                    # Basic FTS vector (French + English)
                    # Use unaccent + french if available; keep simple here
                    None,
                )
            )
        # Insert rows; fill search_vector via to_tsvector on server side
        cur.executemany(
            """
            INSERT INTO property_chunks (document_id, chunk_index, content, chunk_size, embedding, search_vector)
            VALUES (%s, %s, %s, %s, %s, to_tsvector('simple', %s));
            """,
            [(d, i, c, s, emb, c) for (d, i, c, s, emb, _sv) in rows],
        )
        return len(rows)

def semantic_search(query_embedding: List[float], top_k: int = 10) -> List[dict]:
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            """
            SELECT c.id, c.document_id, c.chunk_index, c.content, (1 - (c.embedding <=> %s::vector)) AS similarity
            FROM property_chunks c
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
            """,
            (query_embedding, query_embedding, top_k),
        )
        return list(cur.fetchall())


