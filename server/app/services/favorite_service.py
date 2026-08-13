from __future__ import annotations

from datetime import datetime, timezone
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.favorite import Favorite
from app.schemas.favorite import FavoriteCreate, FavoriteRead


def _serialize_favorite(favorite: Favorite) -> FavoriteRead:
    return FavoriteRead(
        id=favorite.id,
        track_id=favorite.track_id,
        track_name=favorite.track_name,
        artist_name=favorite.artist_name,
        album_name=favorite.album_name,
        album_image_url=favorite.album_image_url,
        spotify_url=favorite.spotify_url,
        duration_ms=favorite.duration_ms,
        mood=favorite.mood,
        reason=favorite.reason,
        is_favorite=favorite.is_favorite,
        saved_at=favorite.created_at,
    )


def list_favorites(db: Session, user_id: int) -> list[FavoriteRead]:
    statement = (
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .where(Favorite.is_favorite.is_(True))
        .order_by(Favorite.created_at.desc())
    )
    return [_serialize_favorite(item) for item in db.scalars(statement).all()]


def build_user_preference_context(db: Session, user_id: int, limit: int = 8) -> str | None:
    favorites = list_favorites(db, user_id)
    if not favorites:
        return None

    top_artists = [artist for artist, _ in Counter(item.artist_name for item in favorites).most_common(3)]
    top_moods = [mood for mood, _ in Counter(item.mood for item in favorites if item.mood).most_common(3)]
    top_albums = [album for album, _ in Counter(item.album_name for item in favorites if item.album_name).most_common(2)]

    parts: list[str] = []
    if top_artists:
        parts.append(f"자주 좋아한 아티스트: {', '.join(top_artists[:limit])}")
    if top_albums:
        parts.append(f"자주 저장한 앨범 결: {', '.join(top_albums[:2])}")
    if top_moods:
        parts.append(f"좋아요한 감정 경향: {', '.join(top_moods[:limit])}")

    if not parts:
        return None

    return " | ".join(parts)


def upsert_favorite(db: Session, user_id: int, payload: FavoriteCreate) -> FavoriteRead:
    favorite = db.scalar(
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .where(Favorite.track_id == payload.track_id)
    )
    now = datetime.now(timezone.utc)

    if favorite is None:
        favorite = Favorite(
            user_id=user_id,
            track_id=payload.track_id,
            track_name=payload.track_name,
            artist_name=payload.artist_name,
            album_name=payload.album_name,
            album_image_url=payload.album_image_url,
            spotify_url=payload.spotify_url,
            duration_ms=payload.duration_ms,
            mood=payload.mood,
            reason=payload.reason,
            is_favorite=True,
            created_at=now,
        )
        db.add(favorite)
    else:
        favorite.track_name = payload.track_name
        favorite.artist_name = payload.artist_name
        favorite.album_name = payload.album_name
        favorite.album_image_url = payload.album_image_url
        favorite.spotify_url = payload.spotify_url
        favorite.duration_ms = payload.duration_ms
        favorite.mood = payload.mood
        favorite.reason = payload.reason
        favorite.is_favorite = True
        favorite.created_at = now

    db.commit()
    db.refresh(favorite)
    return _serialize_favorite(favorite)


def remove_favorite(db: Session, user_id: int, track_id: str) -> None:
    favorite = db.scalar(
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .where(Favorite.track_id == track_id)
    )
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite track not found")

    favorite.is_favorite = False
    db.commit()
