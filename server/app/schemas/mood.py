from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.track import TrackSummary
from app.schemas.recommendation import RecommendationRead


class MoodRequest(BaseModel):
    text: str = Field(default="", description="User message or diary text")
    mood: str | None = Field(default=None, description="Optional explicit mood")


class MoodResponse(BaseModel):
    mood: str
    tracks: list[TrackSummary]
    mood_record: MoodRecordRead | None = None
    recommendation: RecommendationRead | None = None


class MoodRecordCreate(BaseModel):
    mood: str = Field(description="Selected mood")
    text: str | None = Field(default=None, description="User note or diary text")
    source: str = Field(default="manual", description="Mood source")


class MoodRecordRead(MoodRecordCreate):
    id: int
    created_at: datetime
