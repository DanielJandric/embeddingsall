from __future__ import annotations

from typing import List, Dict, Any
import json

from openai import OpenAI
from ..llm.embedding_client import _get_client  # reuse configured OpenAI client
from ...config.settings import settings


def rerank_with_openai(
    query: str,
    candidates: List[Dict[str, Any]],
    content_key: str = "content",
    top_k: int = 10,
    model: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Re-rank candidate passages using an LLM (OpenAI). Returns candidates with added 'rerank_score',
    sorted by that score (desc), truncated to top_k.
    """
    if not candidates:
        return []
    use_model = model or settings.rerank_model or "gpt-4o-mini"
    client: OpenAI = _get_client()

    # Prepare a compact list to limit token usage
    max_candidates = max(1, min(settings.rerank_max_candidates, len(candidates)))
    shortlist = candidates[:max_candidates]
    numbered = [
        {"i": i, "text": str(c.get(content_key, ""))[:2000]}  # trim per item
        for i, c in enumerate(shortlist)
    ]
    prompt = {
        "role": "system",
        "content": (
            "You are a retrieval re-ranker. Score each passage's relevance to the user query from 0 to 1.\n"
            "Return STRICT JSON: an array of objects [{\"i\": <index>, \"score\": <float>}], sorted by score desc. No extra text."
        ),
    }
    user = {
        "role": "user",
        "content": json.dumps(
            {
                "query": query,
                "passages": numbered,
                "instruction": "Score each passage for relevance in [0.0, 1.0]. Higher is better.",
            }
        ),
    }

    try:
        resp = client.chat.completions.create(
            model=use_model,
            messages=[prompt, user],
            temperature=0.0,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        # The response_format=json_object returns a JSON object; accept either top-level array or object with 'scores'
        data = json.loads(content)
        arr = data if isinstance(data, list) else data.get("scores") or data.get("result") or []
        scored = []
        for item in arr:
            try:
                idx = int(item.get("i"))
                score = float(item.get("score"))
                if 0 <= idx < len(shortlist):
                    copy = dict(shortlist[idx])
                    copy["rerank_score"] = score
                    scored.append(copy)
            except Exception:
                continue
        scored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return scored[:top_k]
    except Exception:
        # Fallback: return original order truncated
        return shortlist[:top_k]


