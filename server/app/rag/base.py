from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    title: str
    content: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class RetrievedKnowledge:
    query: str
    chunks: tuple[KnowledgeChunk, ...]

    @property
    def text(self) -> str:
        return "\n\n".join(f"[{chunk.title}] {chunk.content}" for chunk in self.chunks)

