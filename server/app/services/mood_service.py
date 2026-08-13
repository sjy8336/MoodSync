from __future__ import annotations
from datetime import datetime

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.mood_record import MoodRecord
from app.models.recommendation import Recommendation
from app.schemas.mood import MoodRecordCreate, MoodRecordRead
from app.schemas.recommendation import RecommendationCreate, RecommendationRead
from app.schemas.track import TrackSummary


def create_mood_record(db: Session, user_id: int, payload: MoodRecordCreate) -> MoodRecord:
    record = MoodRecord(
        user_id=user_id,
        mood=payload.mood,
        text=payload.text,
        source=payload.source,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_recommendation(db: Session, user_id: int, payload: RecommendationCreate) -> Recommendation:
    recommendation = Recommendation(
        user_id=user_id,
        mood=payload.mood,
        query=payload.query,
        message=payload.message,
        selected_vibes=payload.selected_vibes,
        context_snapshot=payload.context_snapshot,
        rag_context=payload.rag_context,
        llm_context=payload.llm_context,
        generation_profile=payload.generation_profile,
        tracks=[track.model_dump(mode="json", exclude_none=True) for track in payload.tracks],
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def get_today_mood_record(db: Session, user_id: int) -> MoodRecord | None:
    statement = (
        select(MoodRecord)
        .where(MoodRecord.user_id == user_id)
        .where(cast(MoodRecord.created_at, Date) == func.current_date())
        .order_by(MoodRecord.created_at.desc())
        .limit(1)
    )
    return db.scalar(statement)


def get_recent_mood_records(db: Session, user_id: int, limit: int = 3) -> list[MoodRecord]:
    statement = (
        select(MoodRecord)
        .where(MoodRecord.user_id == user_id)
        .order_by(MoodRecord.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_recent_recommendations(db: Session, user_id: int, limit: int = 3) -> list[Recommendation]:
    statement = (
        select(Recommendation)
        .where(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_month_mood_records(db: Session, user_id: int, year: int, month: int) -> list[MoodRecord]:
    if month == 12:
        next_month_start = datetime(year + 1, 1, 1)
    else:
        next_month_start = datetime(year, month + 1, 1)
    month_start = datetime(year, month, 1)

    statement = (
        select(MoodRecord)
        .where(MoodRecord.user_id == user_id)
        .where(MoodRecord.created_at >= month_start)
        .where(MoodRecord.created_at < next_month_start)
        .order_by(MoodRecord.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_month_recommendations(db: Session, user_id: int, year: int, month: int) -> list[Recommendation]:
    if month == 12:
        next_month_start = datetime(year + 1, 1, 1)
    else:
        next_month_start = datetime(year, month + 1, 1)
    month_start = datetime(year, month, 1)

    statement = (
        select(Recommendation)
        .where(Recommendation.user_id == user_id)
        .where(Recommendation.created_at >= month_start)
        .where(Recommendation.created_at < next_month_start)
        .order_by(Recommendation.created_at.desc())
    )
    return list(db.scalars(statement).all())


def serialize_mood_record(record: MoodRecord) -> MoodRecordRead:
    return MoodRecordRead(
        id=record.id,
        mood=record.mood,
        text=record.text,
        source=record.source,
        created_at=record.created_at,
    )


def serialize_recommendation(recommendation: Recommendation) -> RecommendationRead:
    tracks = [
        TrackSummary.model_validate(track)
        for track in (recommendation.tracks or [])
        if isinstance(track, dict)
    ]
    return RecommendationRead(
        id=recommendation.id,
        mood=recommendation.mood,
        query=recommendation.query,
        message=recommendation.message,
        selected_vibes=recommendation.selected_vibes or [],
        context_snapshot=recommendation.context_snapshot or {},
        rag_context=recommendation.rag_context,
        llm_context=recommendation.llm_context,
        generation_profile=recommendation.generation_profile or {},
        tracks=tracks,
        created_at=recommendation.created_at,
    )
