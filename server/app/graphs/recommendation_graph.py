from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import Any, TypedDict, cast

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.schemas.mood import MoodRecordCreate, MoodRequest, MoodResponse
from app.schemas.track import TrackSummary
from app.schemas.recommendation import RecommendationCreate
from app.services.analysis_service import analyze_mood_from_text
from app.services.current_user import get_spotify_access_token, sync_spotify_token_cookies
from app.services.favorite_service import build_user_preference_context
from app.services.gemini_service import GeminiServiceError, generate_recommendation_copy
from app.services.mood_service import (
    create_mood_record,
    create_recommendation,
    get_recent_mood_records,
    get_recent_recommendations,
    serialize_mood_record,
    serialize_recommendation,
)
from app.services.recommendation_knowledge_base import retrieve_recommendation_context
from app.services.spotify_service import _split_context, build_recommendation_message, build_track_reason, recommend_tracks

try:  # pragma: no cover - optional dependency path
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - fallback for local environments without langgraph
    START = "__start__"
    END = "__end__"
    StateGraph = None


class RecommendationWorkflowState(TypedDict, total=False):
    db: Session
    request: Request
    response: Response
    user: Any
    payload: MoodRequest
    free_text: str
    selected_vibes: list[str]
    input_text: str
    preference_context: str | None
    recent_mood_summary: str | None
    recent_recommendation_summary: str | None
    mood: str
    rag_context: str | None
    llm_context: str
    context_snapshot: dict[str, Any]
    generation_profile: dict[str, Any]
    access_token: str
    tracks: list[TrackSummary]
    recommendation_copy: dict[str, Any] | None
    message: str | None
    mood_record: Any
    recommendation: Any


def _is_generic_track_reason(reason: str) -> bool:
    lowered = reason.lower()
    generic_markers = [
        "특유의 분위기",
        "지금처럼",
        "무리 없이 다루는 데",
        "잘 맞아요",
        "같이 반영했고",
        "흐름을 이어가기",
        "과하지 않게",
        "부담이 적어요",
        "핵심 느낌이 먼저",
        "흐름의 온도",
        "버퍼 역할",
    ]
    score = sum(1 for marker in generic_markers if marker in lowered)
    return score >= 2 or len(reason.strip()) < 24


def _summarize_recent_moods(recent_moods: list[Any]) -> str | None:
    if not recent_moods:
        return None

    counts = Counter(getattr(item, "mood", "") for item in recent_moods if getattr(item, "mood", ""))
    if not counts:
        return None

    ordered = [f"{mood} x{count}" for mood, count in counts.most_common(4)]
    latest = getattr(recent_moods[0], "mood", "")
    latest_text = f"최근 기록의 가장 최신 무드는 {latest}." if latest else ""
    return " ".join(filter(None, [latest_text, f"최근 감정 분포: {', '.join(ordered)}."]))


def _summarize_recent_recommendations(recent_recommendations: list[Any]) -> str | None:
    if not recent_recommendations:
        return None

    parts: list[str] = []
    for item in recent_recommendations[:3]:
        mood = getattr(item, "mood", "")
        tracks = getattr(item, "tracks", []) or []
        first_track = ""
        if tracks and isinstance(tracks[0], dict):
            first_track = str(tracks[0].get("name") or "")
        if mood or first_track:
            parts.append(" / ".join(filter(None, [mood, first_track])))
    if not parts:
        return None
    return f"최근 추천 흐름: {', '.join(parts)}"


def _prepare_context(state: RecommendationWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    db = state["db"]
    user = state["user"]
    free_text, selected_vibes = _split_context(payload.text)
    input_text = free_text or payload.text or ""
    preference_context = build_user_preference_context(db, user.id)
    recent_moods = get_recent_mood_records(db, user.id, limit=6)
    recent_recommendations = get_recent_recommendations(db, user.id, limit=3)
    recent_mood_summary = _summarize_recent_moods(recent_moods)
    recent_recommendation_summary = _summarize_recent_recommendations(recent_recommendations)
    return {
        "free_text": free_text,
        "selected_vibes": selected_vibes,
        "input_text": input_text,
        "preference_context": preference_context,
        "recent_mood_summary": recent_mood_summary,
        "recent_recommendation_summary": recent_recommendation_summary,
    }


def _resolve_mood(state: RecommendationWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    input_text = state.get("input_text", "")
    mood = payload.mood or analyze_mood_from_text(input_text)
    return {"mood": mood}


def _retrieve_rag_context(state: RecommendationWorkflowState) -> dict[str, Any]:
    query_parts = [
        state.get("input_text", ""),
        state.get("preference_context") or "",
        state.get("recent_mood_summary") or "",
        state.get("recent_recommendation_summary") or "",
        " ".join(state.get("selected_vibes", [])),
        state.get("mood", ""),
    ]
    query = " ".join(part for part in query_parts if part).strip()
    retrieved = retrieve_recommendation_context(query)
    return {
        "rag_context": retrieved.text or None,
    }


def _compose_llm_context(state: RecommendationWorkflowState) -> dict[str, Any]:
    sections = [
        f"selected_mood: {state.get('mood') or ''}",
        f"user_text: {state.get('input_text') or ''}",
        f"selected_vibes: {', '.join(state.get('selected_vibes', []))}",
        f"favorite_context: {state.get('preference_context') or ''}",
        f"recent_moods: {state.get('recent_mood_summary') or ''}",
        f"recent_recommendations: {state.get('recent_recommendation_summary') or ''}",
        f"rag_context:\n{state.get('rag_context') or ''}",
    ]
    llm_context = "\n\n".join(section for section in sections if section and section.strip())
    return {
        "llm_context": llm_context,
        "context_snapshot": {
            "selected_mood": state.get("mood"),
            "user_text": state.get("input_text"),
            "selected_vibes": state.get("selected_vibes", []),
            "favorite_context": state.get("preference_context"),
            "recent_mood_summary": state.get("recent_mood_summary"),
            "recent_recommendation_summary": state.get("recent_recommendation_summary"),
            "rag_context": state.get("rag_context"),
        },
    }


def _load_tracks(state: RecommendationWorkflowState) -> dict[str, Any]:
    request = state["request"]
    response = state["response"]
    db = state["db"]
    user = state.get("user")
    is_demo_user = getattr(user, "auth_provider", None) == "demo"
    access_token = ""
    if not is_demo_user:
        access_token = get_spotify_access_token(request, db, allow_refresh=True, validate=True)
        sync_spotify_token_cookies(response, request)
    tracks = recommend_tracks(
        state.get("mood", "calm"),
        access_token=access_token or None,
        context_text=state.get("llm_context"),
    )
    return {
        "access_token": access_token,
        "tracks": tracks,
    }


def _compose_copy_and_track_reasons(state: RecommendationWorkflowState) -> dict[str, Any]:
    mood = state.get("mood", "calm")
    input_text = state.get("input_text", "")
    selected_vibes = state.get("selected_vibes", [])
    tracks = state.get("tracks", [])
    recommendation_copy = None
    try:
        recommendation_copy = generate_recommendation_copy(
            mood,
            state.get("llm_context"),
            [track.model_dump(mode="json") for track in tracks],
            selected_vibes=selected_vibes,
        )
    except GeminiServiceError:
        recommendation_copy = None

    message = (
        recommendation_copy.get("message")
        if recommendation_copy and recommendation_copy.get("message")
        else build_recommendation_message(mood, input_text, len(tracks), tracks)
    )
    reason_map = {
        str(item.get("track_id")): str(item.get("reason"))
        for item in (recommendation_copy.get("track_reasons") if recommendation_copy else [])
        if isinstance(item, dict) and item.get("track_id") and item.get("reason") and not _is_generic_track_reason(str(item.get("reason")))
    }
    enriched_tracks = [
        track.model_copy(
            update={
                "reason": reason_map.get(
                    track.track_id,
                    build_track_reason(track, mood, input_text, index),
                )
            }
        )
        for index, track in enumerate(tracks)
    ]
    return {
        "recommendation_copy": recommendation_copy,
        "message": message,
        "tracks": enriched_tracks,
        "generation_profile": {
            "llm_provider": "gemini",
            "demo_mode": getattr(state.get("user"), "auth_provider", None) == "demo",
            "has_rag_context": bool(state.get("rag_context")),
            "has_selected_vibes": bool(state.get("selected_vibes")),
            "track_count": len(enriched_tracks),
            "reason_source": "gemini" if recommendation_copy else "fallback",
        },
    }


def _persist_results(state: RecommendationWorkflowState) -> dict[str, Any]:
    db = state["db"]
    user = state["user"]
    payload = state["payload"]
    mood = state.get("mood", "calm")
    tracks = state.get("tracks", [])
    message = state.get("message")
    mood_record = create_mood_record(
        db,
        user.id,
        MoodRecordCreate(
            mood=mood,
            text=payload.text or None,
            source="manual" if payload.mood else "text",
        ),
    )
    recommendation = create_recommendation(
        db,
        user.id,
        RecommendationCreate(
            mood=mood,
            query=payload.text or None,
            message=message,
            selected_vibes=state.get("selected_vibes", []),
            context_snapshot=state.get("context_snapshot") or {},
            rag_context=state.get("rag_context"),
            llm_context=state.get("llm_context"),
            generation_profile=state.get("generation_profile") or {},
            tracks=tracks,
        ),
    )
    return {
        "mood_record": mood_record,
        "recommendation": recommendation,
    }


def _build_workflow():  # pragma: no cover - exercised via run_recommendation_workflow
    if StateGraph is None:
        return None

    workflow = StateGraph(RecommendationWorkflowState)
    workflow.add_node("prepare_context", _prepare_context)
    workflow.add_node("resolve_mood", _resolve_mood)
    workflow.add_node("retrieve_rag_context", _retrieve_rag_context)
    workflow.add_node("compose_llm_context", _compose_llm_context)
    workflow.add_node("load_tracks", _load_tracks)
    workflow.add_node("compose_copy", _compose_copy_and_track_reasons)
    workflow.add_node("persist_results", _persist_results)

    workflow.add_edge(START, "prepare_context")
    workflow.add_edge("prepare_context", "resolve_mood")
    workflow.add_edge("resolve_mood", "retrieve_rag_context")
    workflow.add_edge("retrieve_rag_context", "compose_llm_context")
    workflow.add_edge("compose_llm_context", "load_tracks")
    workflow.add_edge("load_tracks", "compose_copy")
    workflow.add_edge("compose_copy", "persist_results")
    workflow.add_edge("persist_results", END)
    return workflow.compile()


@lru_cache(maxsize=1)
def _compiled_workflow():
    return _build_workflow()


def run_recommendation_workflow(
    *,
    db: Session,
    request: Request,
    response: Response,
    user: Any,
    payload: MoodRequest,
) -> RecommendationWorkflowState:
    state: RecommendationWorkflowState = {
        "db": db,
        "request": request,
        "response": response,
        "user": user,
        "payload": payload,
    }

    graph = _compiled_workflow()
    if graph is not None:
        result = graph.invoke(state)
        return cast(RecommendationWorkflowState, result)

    state.update(_prepare_context(state))
    state.update(_resolve_mood(state))
    state.update(_retrieve_rag_context(state))
    state.update(_compose_llm_context(state))
    state.update(_load_tracks(state))
    state.update(_compose_copy_and_track_reasons(state))
    state.update(_persist_results(state))
    return state


def build_mood_response(state: RecommendationWorkflowState) -> MoodResponse:
    mood_record = state.get("mood_record")
    recommendation = state.get("recommendation")
    tracks = state.get("tracks", [])
    return MoodResponse(
        mood=state.get("mood", "calm"),
        tracks=tracks,
        mood_record=serialize_mood_record(mood_record) if mood_record else None,
        recommendation=serialize_recommendation(recommendation) if recommendation else None,
    )
