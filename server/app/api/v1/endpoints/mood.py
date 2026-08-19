from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.graphs.recommendation_graph import build_mood_response, complete_recommendation_copy, run_recommendation_workflow
from app.schemas.home import HomeSummaryResponse
from app.schemas.mood import MoodRequest, MoodResponse
from app.services.current_user import (
    resolve_current_spotify_user,
)
from app.services.mood_service import (
    get_month_mood_records,
    get_month_recommendations,
    get_recent_mood_records,
    get_recent_recommendations,
    get_today_mood_record,
)
from app.services.mood_service import serialize_mood_record, serialize_recommendation

router = APIRouter(prefix="/mood", tags=["mood"])


@router.post("/recommend", response_model=MoodResponse)
def recommend_by_mood(
    payload: MoodRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MoodResponse:
    user = resolve_current_spotify_user(request, db)
    workflow_state = run_recommendation_workflow(
        db=db,
        request=request,
        response=response,
        user=user,
        payload=payload,
        defer_gemini_copy=True,
    )
    recommendation = workflow_state.get("recommendation")
    if recommendation is not None:
        background_tasks.add_task(complete_recommendation_copy, recommendation.id)
    return build_mood_response(workflow_state)


@router.get("/dashboard", response_model=HomeSummaryResponse)
def get_dashboard(request: Request, db: Session = Depends(get_db)) -> HomeSummaryResponse:
    user = resolve_current_spotify_user(request, db)
    today_mood = get_today_mood_record(db, user.id)
    recent_moods = get_recent_mood_records(db, user.id, limit=3)
    recent_recommendations = get_recent_recommendations(db, user.id, limit=3)

    serialized_recommendations = [serialize_recommendation(item) for item in recent_recommendations]

    return HomeSummaryResponse(
        today_mood=serialize_mood_record(today_mood) if today_mood else None,
        recent_moods=[serialize_mood_record(item) for item in recent_moods],
        latest_recommendation=serialized_recommendations[0] if serialized_recommendations else None,
        recent_recommendations=serialized_recommendations,
    )


@router.get("/history")
def get_mood_history(
    request: Request,
    year: int | None = Query(default=None, ge=1970, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> dict:
    user = resolve_current_spotify_user(request, db)
    now = datetime.now()
    target_year = year or now.year
    target_month = month or now.month

    mood_records = get_month_mood_records(db, user.id, target_year, target_month)
    recommendations = get_month_recommendations(db, user.id, target_year, target_month)

    recommendations_by_date: dict[str, object] = {}
    for recommendation in recommendations:
        date_key = recommendation.created_at.date().isoformat()
        if date_key not in recommendations_by_date:
            recommendations_by_date[date_key] = recommendation

    mood_counts: dict[str, int] = {}
    seen_dates: set[str] = set()
    records: list[dict] = []

    for mood_record in mood_records:
        date_key = mood_record.created_at.date().isoformat()
        if date_key in seen_dates:
            continue
        seen_dates.add(date_key)

        mood_counts[mood_record.mood] = mood_counts.get(mood_record.mood, 0) + 1
        recommendation = recommendations_by_date.get(date_key)
        recommendation_query = getattr(recommendation, "query", None)
        selected_vibes = list(getattr(recommendation, "selected_vibes", None) or [])
        records.append(
            {
                "date": date_key,
                "mood": mood_record.mood,
                "text": recommendation_query or mood_record.text,
                "vibes": selected_vibes,
                "tracks": getattr(recommendation, "tracks", None) or [],
            }
        )

    all_vibes = [vibe for record in records for vibe in record["vibes"]]
    top_vibe = max(set(all_vibes), key=all_vibes.count) if all_vibes else None

    top_mood = None
    if mood_counts:
        top_mood = max(mood_counts.items(), key=lambda item: item[1])[0]

    return {
        "summary": {
            "recordedDays": len(records),
            "topMood": top_mood,
            "topVibe": top_vibe,
            "moodCounts": mood_counts,
        },
        "records": records,
    }
