from typing import List, Optional
from openai import OpenAI
from ...config.settings import settings

_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client

def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    if not texts:
        return []
    client = _get_client()
    # OpenAI embeddings API supports batching
    use_model = model or settings.embedding_model or "text-embedding-3-small"
    resp = client.embeddings.create(input=texts, model=use_model)
    return [item.embedding for item in resp.data]


