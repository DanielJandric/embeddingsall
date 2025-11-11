from ...config.settings import settings

def _is_noise(chunk: str) -> bool:
    if not chunk or len(chunk.strip()) < 50:
        return True
    letters = sum(ch.isalpha() for ch in chunk)
    ratio = letters / max(1, len(chunk))
    return ratio < 0.25  # drop highly non-alphabetic blobs

def split_text(text: str) -> list[str]:
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    chunks: list[str] = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        chunk = text[i:end]
        if not _is_noise(chunk):
            chunks.append(chunk)
        if end == len(text):
            break
        i = max(i + size - overlap, i + 1)
    return chunks


