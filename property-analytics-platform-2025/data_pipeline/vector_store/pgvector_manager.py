def build_hnsw_sql(table: str = "property_chunks", column: str = "embedding") -> str:
    return (
        f"CREATE INDEX IF NOT EXISTS {table}_{column}_hnsw "
        f"ON {table} USING hnsw ({column} vector_cosine_ops) "
        f"WITH (m = 16, ef_construction = 128);"
    )

def build_ivfflat_sql(table: str = "property_chunks", column: str = "embedding", lists: int = 100) -> str:
    return (
        f"CREATE INDEX IF NOT EXISTS {table}_{column}_ivf "
        f"ON {table} USING ivfflat ({column} vector_cosine_ops) "
        f"WITH (lists = {lists});"
    )

def build_vector_index_sql(
    table: str = "property_chunks",
    column: str = "embedding",
    index_type: str = "hnsw",
    lists: int = 100,
) -> str:
    if index_type.lower() == "hnsw":
        return build_hnsw_sql(table=table, column=column)
    if index_type.lower() == "ivfflat":
        return build_ivfflat_sql(table=table, column=column, lists=lists)
    raise ValueError(f"Unsupported index_type: {index_type}")


