from __future__ import annotations

import json
import hashlib
from functools import lru_cache
from math import sqrt
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.rag.base import KnowledgeChunk, RetrievedKnowledge
from app.rag.genre_chunks import GENRE_CHUNKS
from app.rag.mood_chunks import MOOD_CHUNKS
from app.rag.workflow_chunks import WORKFLOW_CHUNKS


def _tokenize(text: str) -> set[str]:
    return {token for token in text.lower().split() if token}


@lru_cache(maxsize=1)
def _knowledge_base() -> tuple[KnowledgeChunk, ...]:
    return (*MOOD_CHUNKS, *GENRE_CHUNKS, *WORKFLOW_CHUNKS)


def _embedding_url() -> str:
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_embedding_model}:embedContent"
    )


def _prepare_query_text(query: str) -> str:
    cleaned = " ".join(query.split())
    return f"task: search result | query: {cleaned}"


def _prepare_document_text(chunk: KnowledgeChunk) -> str:
    title = chunk.title.strip() or "none"
    keywords = " ".join(chunk.keywords)
    return f"title: {title} | text: {chunk.content.strip()} | keywords: {keywords}"


_EMBEDDING_CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "rag_document_embeddings.json"


def _document_cache_key() -> str:
    documents = "\n".join(f"{chunk.id}:{_prepare_document_text(chunk)}" for chunk in _knowledge_base())
    return hashlib.sha256(f"{settings.gemini_embedding_model}\n{documents}".encode("utf-8")).hexdigest()


def _load_document_embedding_cache(cache_key: str) -> dict[str, list[float]]:
    try:
        cached = json.loads(_EMBEDDING_CACHE_PATH.read_text(encoding="utf-8"))
        if cached.get("cache_key") != cache_key:
            return {}
        vectors = cached.get("vectors") or {}
        return {
            str(chunk_id): [float(value) for value in values]
            for chunk_id, values in vectors.items()
            if isinstance(values, list) and all(isinstance(value, (int, float)) for value in values)
        }
    except (OSError, ValueError, TypeError):
        return {}


def _save_document_embedding_cache(cache_key: str, vectors: dict[str, list[float]]) -> None:
    try:
        _EMBEDDING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _EMBEDDING_CACHE_PATH.write_text(
            json.dumps({"cache_key": cache_key, "vectors": vectors}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def build_recommendation_guidance(
    retrieved: RetrievedKnowledge,
    *,
    mood: str,
    selected_vibes: list[str],
    user_text: str,
) -> dict[str, Any]:
    """Turn retrieved documents into a small, safe contract for recommendation steps."""
    chunk_ids = {chunk.id for chunk in retrieved.chunks}
    text = user_text.lower()
    vibes = set(selected_vibes)
    comfort_request = (
        mood in {"anxious", "sad", "lonely", "tired"}
        and bool(vibes & {"위로되는", "잔잔한", "따뜻한", "감성적인", "차분한"})
    ) or any(word in text for word in ("헤어", "이별", "불안", "위로", "포근", "따뜻", "다독"))
    focus_request = mood == "focused" or "몰입되는" in vibes or any(
        word in text for word in ("공부", "작업", "집중", "과제", "마감")
    )

    guidance: dict[str, Any] = {
        "source_chunk_ids": sorted(chunk_ids),
        "selection_rules": [],
        "copy_rules": [
            "곡의 검증된 메타데이터만 음악적 근거로 사용한다.",
            "사용자 상황과 연결하되, 곡 순번이나 일반적인 칭찬을 근거로 쓰지 않는다.",
        ],
        "preferred_tags": [],
        "avoid_tags": [],
        "audio_hints": {},
    }

    if comfort_request and {"comfort-mode", "comfort-breathing", "vibe-to-sound"} & chunk_ids:
        guidance["selection_rules"].append("따뜻하고 부드러운 후보를 우선하며, 거칠거나 급격히 고조되는 후보는 제외한다.")
        guidance["preferred_tags"] = ["soft", "warm", "calm", "comfort", "emotional", "love", "soul"]
        guidance["avoid_tags"] = ["punk", "pop-punk", "rock", "high_energy", "driving"]
        guidance["audio_hints"] = {
            "target_energy": 0.32,
            "target_acousticness": 0.7,
            "target_valence": 0.5,
        }

    if focus_request and "focus-flow" in chunk_ids:
        guidance["selection_rules"].append("리듬 변화가 과하지 않고 일정한 텐션을 유지하는 후보를 우선한다.")
        guidance["preferred_tags"] = list(dict.fromkeys([*guidance["preferred_tags"], "focused", "rhythmic"]))
        guidance["audio_hints"] = {**guidance["audio_hints"], "target_energy": 0.48}

    if "genre-preservation" in chunk_ids:
        guidance["selection_rules"].append("사용자가 직접 말한 장르 선호는 다른 일반 규칙보다 우선한다.")

    return guidance


def _gemini_embed_text(text: str, *, task_type: str) -> list[float]:
    if not settings.gemini_api_key:
        return []

    url = f"{_embedding_url()}?{urlencode({'key': settings.gemini_api_key})}"
    request = Request(
        url,
        data=json.dumps(
            {
                "model": f"models/{settings.gemini_embedding_model}",
                "content": {
                    "parts": [{"text": text}],
                },
                "taskType": task_type,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError):
        return []

    embeddings = data.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, dict):
            values = first.get("values")
            if isinstance(values, list):
                return [float(value) for value in values if isinstance(value, (int, float))]

    embedding = data.get("embedding")
    if isinstance(embedding, dict):
        values = embedding.get("values")
        if isinstance(values, list):
            return [float(value) for value in values if isinstance(value, (int, float))]

    return []


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


@lru_cache(maxsize=1)
def _document_embeddings() -> tuple[tuple[KnowledgeChunk, tuple[float, ...]], ...]:
    vectors: list[tuple[KnowledgeChunk, tuple[float, ...]]] = []
    cache_key = _document_cache_key()
    cached_vectors = _load_document_embedding_cache(cache_key)
    updated_vectors = dict(cached_vectors)
    for chunk in _knowledge_base():
        vector = tuple(cached_vectors.get(chunk.id) or _gemini_embed_text(
            _prepare_document_text(chunk), task_type="RETRIEVAL_DOCUMENT"
        ))
        if vector:
            vectors.append((chunk, vector))
            updated_vectors[chunk.id] = list(vector)
    if updated_vectors != cached_vectors:
        _save_document_embedding_cache(cache_key, updated_vectors)
    return tuple(vectors)


@lru_cache(maxsize=128)
def retrieve_recommendation_context(query: str, limit: int = 4) -> RetrievedKnowledge:
    normalized_query = " ".join(query.split())
    query_vector = _gemini_embed_text(_prepare_query_text(normalized_query), task_type="RETRIEVAL_QUERY")
    if query_vector:
        ranked = sorted(
            _document_embeddings(),
            key=lambda item: (-_cosine_similarity(query_vector, list(item[1])), item[0].title),
        )
        selected = tuple(
            chunk
            for chunk, vector in ranked[:limit]
            if _cosine_similarity(query_vector, list(vector)) > 0.15
        )
        if selected:
            return RetrievedKnowledge(query=query, chunks=selected)
        fallback = tuple(chunk for chunk, _ in ranked[: min(limit, len(ranked))])
        return RetrievedKnowledge(query=query, chunks=fallback)

    query_tokens = _tokenize(query)
    ranked = sorted(
        _knowledge_base(),
        key=lambda chunk: (
            -sum(1 for keyword in chunk.keywords if keyword.lower() in query_tokens or keyword.lower() in normalized_query.lower()),
            chunk.title,
        ),
    )
    selected = tuple(chunk for chunk in ranked[:limit] if chunk.keywords)
    return RetrievedKnowledge(query=query, chunks=selected)
