from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.track import TrackSummary


class RecommendationCreate(BaseModel):
    mood: str = Field(description="Mood used for recommendation")
    query: str | None = Field(default=None, description="Original user query")
    message: str | None = Field(default=None, description="Human-friendly recommendation summary")
    selected_vibes: list[str] = Field(default_factory=list, description="Selected vibe tags")
    context_snapshot: dict = Field(default_factory=dict, description="Structured snapshot of inputs used for generation")
    rag_context: str | None = Field(default=None, description="Retrieved RAG context")
    llm_context: str | None = Field(default=None, description="Final context passed to the model")
    generation_profile: dict = Field(default_factory=dict, description="Model output metadata and strategy hints")
    tracks: list[TrackSummary] = Field(default_factory=list)


class RecommendationRead(RecommendationCreate):
    id: int
    created_at: datetime


class RecommendationListResponse(BaseModel):
    items: list[RecommendationRead]
    total: int
