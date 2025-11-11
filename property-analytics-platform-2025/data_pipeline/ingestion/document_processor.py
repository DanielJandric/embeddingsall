from pathlib import Path

def read_text(path: str | Path) -> str:
    p = Path(path)
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


