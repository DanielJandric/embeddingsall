from ...config.settings import settings

def split_text(text: str) -> list[str]:
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    chunks: list[str] = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        chunks.append(text[i:end])
        if end == len(text):
            break
        i = max(i + size - overlap, i + 1)
    return chunks


