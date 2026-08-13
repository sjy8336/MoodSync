from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecommendationPlaylist(Base):
    __tablename__ = "recommendation_playlists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), index=True)
    playlist_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    playlist_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    playlist_name: Mapped[str] = mapped_column(String(255))
    track_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_track_count: Mapped[int] = mapped_column(Integer, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
