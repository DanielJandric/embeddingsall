from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterable, List, Optional, Tuple

from psycopg import Connection, sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ...config.settings import settings
from ...data_pipeline.vector_store.pgvector_manager import build_vector_index_sql
from ...config.settings import settings

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
    _pool = ConnectionPool(dsn, min_size=1, max_size=10, kwargs={"autocommit": True, "prepare_threshold": 0})
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
        # Vector index (choose HNSW for dim <= 2000, otherwise IVFFLAT)
        index_type = "hnsw" if settings.embedding_dimension <= 2000 else "ivfflat"
        cur.execute(build_vector_index_sql(table="property_chunks", column="embedding", index_type=index_type))

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
        inserted = 0
        sql_insert = """
            INSERT INTO property_chunks (document_id, chunk_index, content, chunk_size, embedding, search_vector)
            VALUES (%s, %s, %s, %s, %s, to_tsvector('simple', %s));
        """
        # Avoid executemany to prevent prepared statement conflicts with PgBouncer
        for idx, (content, emb) in enumerate(zip(chunks, embeddings)):
            cur.execute(
                sql_insert,
                (document_id, idx, content, len(content), emb, content),
            )
            inserted += 1
        return inserted

def semantic_search(query_embedding: List[float], top_k: int = 10) -> List[dict]:
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        # Improve recall by raising ef_search for this session
        try:
            cur.execute("SET LOCAL hnsw.ef_search = %s;", (max(16, settings.hnsw_ef_search),))
        except Exception:
            pass
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

def hybrid_search(query_text: str, query_embedding: List[float], top_k: int = 10,
                  semantic_weight: float | None = None, fulltext_weight: float | None = None) -> List[dict]:
    sw = semantic_weight if semantic_weight is not None else settings.semantic_weight
    fw = fulltext_weight if fulltext_weight is not None else settings.fulltext_weight
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        try:
            cur.execute("SET LOCAL hnsw.ef_search = %s;", (max(16, settings.hnsw_ef_search),))
        except Exception:
            pass
        cur.execute(
            """
            WITH scored AS (
                SELECT
                    c.id, c.document_id, c.chunk_index, c.content,
                    (1 - (c.embedding <=> %s::vector)) AS sem_score,
                    ts_rank(c.search_vector, websearch_to_tsquery('simple', %s)) AS ft_score
                FROM property_chunks c
                WHERE c.embedding IS NOT NULL
            )
            SELECT *, (sem_score * %s + ft_score * %s) AS combined_score
            FROM scored
            ORDER BY combined_score DESC
            LIMIT %s;
            """,
            (query_embedding, query_text, sw, fw, top_k),
        )
        return list(cur.fetchall())


