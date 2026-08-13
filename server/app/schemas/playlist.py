from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendationPlaylistCreateRequest(BaseModel):
    playlist_name: str | None = Field(default=None, description="Optional playlist title")
    public: bool = Field(default=False, description="Whether to create a public playlist")


class RecommendationPlaylistResponse(BaseModel):
    playlist_id: str = Field(description="Spotify playlist id")
    playlist_url: str | None = Field(default=None, description="Spotify playlist url")
    playlist_name: str = Field(description="Created playlist title")
    track_count: int = Field(description="Number of tracks added to the playlist")
    skipped_track_count: int = Field(description="Tracks that could not be resolved to Spotify URIs")
    message: str = Field(description="Human-friendly status message")
