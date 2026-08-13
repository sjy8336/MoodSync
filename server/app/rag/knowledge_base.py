from __future__ import annotations

import json
from functools import lru_cache
from math import sqrt
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


def _gemini_embed_text(text: str) -> list[float]:
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
    for chunk in _knowledge_base():
        vector = tuple(_gemini_embed_text(_prepare_document_text(chunk)))
        if vector:
            vectors.append((chunk, vector))
    return tuple(vectors)


@lru_cache(maxsize=128)
def retrieve_recommendation_context(query: str, limit: int = 4) -> RetrievedKnowledge:
    normalized_query = " ".join(query.split())
    query_vector = _gemini_embed_text(_prepare_query_text(normalized_query))
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

