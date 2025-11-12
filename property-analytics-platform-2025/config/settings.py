from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    environment: str = Field(default="development")
    log_level: str = Field(default="info")

    # LLMs
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "OPENAI_EMBED_MODEL"),
    )
    embedding_dimension: int = Field(
        default=1536,
        validation_alias=AliasChoices("EMBEDDING_DIM", "OPENAI_EMBED_DIM", "EMBEDDING_DIMENSIONS"),
    )

    # Database / Vector
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    database_url: str | None = None

    # Performance
    chunk_size: int = 1500
    chunk_overlap: int = 300
    semantic_weight: float = 0.6
    fulltext_weight: float = 0.4
    hnsw_ef_search: int = 100

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()  # singleton for simplicity


