from pydantic import BaseModel, Field


class TrackSummary(BaseModel):
    track_id: str = Field(description="Spotify track ID")
    name: str = Field(description="Track title")
    artist_name: str = Field(description="Primary artist name")
    display_title: str | None = Field(default=None, description="Curated title preserved for the UI")
    spotify_search_title: str | None = Field(default=None, description="Title variant used for Spotify enrichment")
    spotify_track_name: str | None = Field(default=None, description="Title returned by Spotify")
    canonical_recording_identity: str | None = Field(default=None, description="Spotify recording identity used for enrichment")
    recording_match_confidence: float | None = Field(default=None, description="Confidence that the Spotify result matches title and artist")
    instrumentation_source: str | None = Field(default=None, description="Source of recording-level instrumentation facts")
    album_name: str | None = Field(default=None, description="Album title")
    album_image_url: str | None = Field(default=None, description="Album cover image URL")
    spotify_url: str | None = Field(default=None, description="Spotify track URL")
    preview_url: str | None = Field(default=None, description="Spotify preview URL")
    duration_ms: int | None = Field(default=None, description="Track duration in milliseconds")
    reason_facts: dict[str, object] = Field(
        default_factory=dict,
        description="Verified metadata that can be used when explaining this recommendation",
    )
    reason: str | None = Field(default=None, description="Why the track was recommended")
