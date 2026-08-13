from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.mood import MoodRecordRead
from app.schemas.recommendation import RecommendationRead


class HomeSummaryResponse(BaseModel):
    today_mood: MoodRecordRead | None = None
    recent_moods: list[MoodRecordRead] = Field(default_factory=list)
    latest_recommendation: RecommendationRead | None = None
    recent_recommendations: list[RecommendationRead] = Field(default_factory=list)
