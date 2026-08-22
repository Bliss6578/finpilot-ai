"""Case-based symbolic operation routing learned from the FinQA corpus."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any


INDEX_PATH = Path(__file__).resolve().parents[1] / "data" / "finqa_reasoning_index.json"
TOKEN_RE = re.compile(r"[a-z][a-z0-9_-]+")
STOPWORDS = {"what", "was", "were", "the", "this", "that", "for", "from", "with", "and", "how", "much", "does", "did", "are", "in", "of", "to", "is", "my"}


@lru_cache(maxsize=1)
def load_finqa_index() -> dict[str, Any] | None:
    if not INDEX_PATH.exists():
        return None
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _tokens(value: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(value.casefold()) if token not in STOPWORDS}


def route_reasoning(question: str) -> dict[str, Any] | None:
    """Return a symbolic reasoning scaffold, never an answer or dataset value."""
    artifact = load_finqa_index()
    query = _tokens(question)
    if not artifact or not query:
        return None
    best: dict[str, Any] | None = None
    best_score = 0.0
    for pattern in artifact.get("patterns", []):
        candidate = _tokens(pattern["question"])
        if not candidate:
            continue
        score = len(query & candidate) / len(query | candidate)
        if score > best_score:
            best, best_score = pattern, score
    if not best or best_score < 0.18:
        return None
    return {
        "operations": best["operations"],
        "similarity": round(best_score, 3),
        "source": artifact["model_name"],
        "policy": "operation_hint_only",
    }
