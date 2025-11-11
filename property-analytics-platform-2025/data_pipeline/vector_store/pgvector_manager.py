def build_hnsw_sql(table: str = "property_chunks", column: str = "embedding") -> str:
    return (
        f"CREATE INDEX IF NOT EXISTS {table}_{column}_hnsw "
        f"ON {table} USING hnsw ({column} vector_cosine_ops) "
        f"WITH (m = 16, ef_construction = 128);"
    )


