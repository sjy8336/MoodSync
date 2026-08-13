from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FavoriteCreate(BaseModel):
    track_id: str = Field(min_length=1, description="Spotify track ID")
    track_name: str = Field(min_length=1, description="Track title")
    artist_name: str = Field(min_length=1, description="Primary artist name")
    album_name: str | None = Field(default=None, description="Album title")
    album_image_url: str | None = Field(default=None, description="Album cover image URL")
    spotify_url: str | None = Field(default=None, description="Spotify track URL")
    duration_ms: int | None = Field(default=None, ge=0, description="Track duration in milliseconds")
    mood: str | None = Field(default=None, description="Mood key used for the recommendation")
    reason: str | None = Field(default=None, description="Why the track was recommended")


class FavoriteRead(FavoriteCreate):
    id: int
    is_favorite: bool
    saved_at: datetime


class FavoriteListResponse(BaseModel):
    items: list[FavoriteRead]
    total: int


class FavoriteActionResponse(BaseModel):
    message: str
