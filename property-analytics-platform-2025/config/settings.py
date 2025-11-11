from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    environment: str = Field(default="development")
    log_level: str = Field(default="info")

    # LLMs
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Database / Vector
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    database_url: str | None = None

    # Performance
    chunk_size: int = 1500
    chunk_overlap: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()  # singleton for simplicity


