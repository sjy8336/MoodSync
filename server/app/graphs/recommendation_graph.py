from __future__ import annotations

from collections import Counter
from functools import lru_cache
import re
from typing import Any, TypedDict, cast

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.recommendation import Recommendation
from app.schemas.mood import MoodRecordCreate, MoodRequest, MoodResponse
from app.schemas.track import TrackSummary
from app.schemas.recommendation import RecommendationCreate
from app.services.analysis_service import analyze_mood_from_text
from app.services.current_user import get_spotify_access_token, sync_spotify_token_cookies
from app.services.favorite_service import build_user_preference_context
from app.services.gemini_service import GeminiServiceError, _recommendation_role, generate_recommendation_copy
from app.core.config import settings
from app.services.mood_service import (
    create_mood_record,
    create_recommendation,
    get_recent_mood_records,
    get_recent_recommendations,
    serialize_mood_record,
    serialize_recommendation,
)
from app.services.recommendation_knowledge_base import build_recommendation_guidance, retrieve_recommendation_context
from app.services.spotify_service import (
    _split_context,
    build_recommendation_message,
    build_track_reason,
    recommend_tracks,
    validate_hard_constraints,
)

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
    defer_gemini_copy: bool
    free_text: str
    selected_vibes: list[str]
    input_text: str
    preference_context: str | None
    recent_mood_summary: str | None
    recent_recommendation_summary: str | None
    mood: str
    rag_context: str | None
    selection_guidance: dict[str, Any]
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


def _has_verified_grounding(item: dict[str, Any], track: TrackSummary) -> bool:
    facts = track.reason_facts or {}
    used_fact_keys = item.get("used_fact_keys") or []
    return bool(used_fact_keys) and all(key in facts for key in used_fact_keys)


def _exposes_internal_recommendation_metadata(reason: str) -> bool:
    lowered = reason.lower()
    internal_markers = (
        "시드",
        "seed genre",
        "selection seed",
        "서비스에서",
        "서비스의 분류",
        "태그가",
        "태그로",
        "dreamy",
        "soft",
        "warm",
        "calm",
        "emotional",
        "comfort",
        "driving",
        "high_energy",
    )
    return any(marker in lowered for marker in internal_markers)


def _overstates_listening_effect(reason: str) -> bool:
    lowered = reason.lower()
    outcome_markers = (
        "불안을 없애",
        "고민을 해결",
        "마음을 치유",
        "걱정을 덜어",
        "도움을 줍니다",
        "도움을 줘요",
        "긴장을 느슨하게 풀어",
        "마음을 고요하게 이끌",
        "안도를 안겨",
        "기대하게 합니다",
        "위로가 절실",
        "포옹을 건네",
        "차분함을 되찾",
    )
    return any(marker in lowered for marker in outcome_markers)


def _has_unnatural_korean_fragment(reason: str) -> bool:
    fragments = (
        "숨 고르기 어울",
        "정리하기 잘 맞",
        "시간 만들기 좋",
        "머물기 적절",
        "쉬어가기 어울",
    )
    return any(fragment in reason for fragment in fragments)


def _uses_disallowed_infinitive_pattern(reason: str) -> bool:
    pattern = re.compile(r"[가-힣]+(?:하기|기)\s*(?:좋아요|잘 맞아요|어울려요|적당해요|적합해요|필요할 때)")
    return any(match.group(0) != "듣기 좋아요" for match in pattern.finditer(reason))


def _uses_unnatural_recommendation_language(reason: str) -> bool:
    markers = (
        "적절해요",
        "알맞아요",
        "괜찮아요",
        "적합해요",
        "감상하기",
        "귀 기울이기",
        "곱씹어 보기",
        "걱정을 곱씹",
        "불안을 곱씹",
        "고민에 잠기",
        "걱정에 머물",
        "로 이루어져",
        "을 지녀",
        "가 담겨 있어",
    )
    return any(marker in reason for marker in markers)


def _uses_repetitive_or_abstract_language(reason: str) -> bool:
    abstract_markers = (
        "분위기의 결",
        "편안한 결",
        "감성의 결",
        "온도를 낮추",
        "느낌을 채워",
        "분위기가 머물",
        "감정을 품",
        "음악이 곁을 지켜",
        "진행되는 전개",
        "이어지는 흐름",
        "머릿속의 결과",
        "편안하게 머물며 듣기",
        "경쾌한 에너지와 높은 에너지",
        "경쾌하게 이어",
        "집중력을 흐트러뜨리지",
        "집중력이 유지",
        "공부 효율",
        "책상 앞에 앉아 리듬을",
        "듣기 알맞",
        "적당합니다",
        "집중의 끈을 단단히 붙잡",
        "활기찬 분위기를 채워",
        "에너지가 채워지는 느낌",
        "적당해요",
        "알맞아요",
        "분위기가 다가와",
        "에너지가 분위기를 채워",
        "템포를 살려",
        "에너지가 조화롭게 흘러",
        "분위기를 조화롭게 만들",
        "유용해요",
        "하기 위해 듣기 좋",
        "기 위해 듣기 좋",
        "차분히 정리하며 듣기",
        "가라앉히며 듣기",
        "위로를 받을 수 있어",
    )
    repeated_descriptor_patterns = (
        r"부드.{0,24}부드",
        r"차분.{0,24}차분",
        r"따뜻.{0,24}따뜻",
        r"몽환.{0,24}몽환",
    )
    return any(marker in reason for marker in abstract_markers) or any(
        re.search(pattern, reason) for pattern in repeated_descriptor_patterns
    ) or any(reason.count(term) >= 2 for term in ("듣기 좋", "조용", "차분", "편안", "조급", "초조"))


def _mentions_unsupported_music_detail(reason: str, track: TrackSummary) -> bool:
    facts_text = str(track.reason_facts or {}).lower()
    detail_markers = ("신스 베이스", "드럼", "보컬", "후렴", "전개", "리듬", "악기", "bpm")
    return any(marker in reason.lower() and marker not in facts_text for marker in detail_markers)


def _repeats_time_clause(reason: str) -> bool:
    return bool(re.search(r"때[^.!?]{0,100}때", reason))


def _first_sentence_signature(reason: str) -> str:
    first_sentence = re.split(r"[.!?]", reason, maxsplit=1)[0]
    return re.sub(r"\s+", " ", first_sentence).strip()


def _is_safe_recommendation_message(message: object) -> bool:
    if not isinstance(message, str) or not message.strip():
        return False
    disallowed_markers = (
        "곁을 지켜",
        "곁에 있어",
        "다독여줄게",
        "함께할게",
        "제가 곁",
        "가라앉혀 보세요",
        "쉬어가세요",
        "호흡을 고르세요",
        "들어보세요",
        "몰입을 도와",
        "집중을 도와",
    )
    return not any(marker in message for marker in disallowed_markers) and not (
        "초조" in message and "조급" in message
    )


def _apply_recommendation_copy(
    tracks: list[TrackSummary],
    recommendation_copy: dict[str, Any] | None,
    mood: str,
    input_text: str,
) -> tuple[list[TrackSummary], dict[str, str]]:
    copy_reasons = recommendation_copy.get("track_reasons") if recommendation_copy else []
    reason_map: dict[str, str] = {}
    used_first_sentences: set[str] = set()
    for track in tracks:
        for item in copy_reasons:
            if not isinstance(item, dict) or str(item.get("track_id")) != track.track_id:
                continue
            reason = str(item.get("reason") or "").strip()
            first_sentence = _first_sentence_signature(reason)
            if (
                not reason
                or not first_sentence
                or first_sentence in used_first_sentences
                or _is_generic_track_reason(reason)
                or _exposes_internal_recommendation_metadata(reason)
                or _overstates_listening_effect(reason)
                or _has_unnatural_korean_fragment(reason)
                or _uses_disallowed_infinitive_pattern(reason)
                or _uses_unnatural_recommendation_language(reason)
                or _uses_repetitive_or_abstract_language(reason)
                or _repeats_time_clause(reason)
                or _mentions_unsupported_music_detail(reason, track)
                or not _has_verified_grounding(item, track)
            ):
                continue
            reason_map[track.track_id] = reason
            used_first_sentences.add(first_sentence)
            break
    enriched_tracks = [
        track.model_copy(
            update={
                "reason": reason_map.get(
                    track.track_id,
                    build_track_reason(track, mood, input_text, index, _recommendation_role(mood, index, input_text)),
                )
            }
        )
        for index, track in enumerate(tracks)
    ]
    return enriched_tracks, reason_map


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
        "selection_guidance": build_recommendation_guidance(
            retrieved,
            mood=state.get("mood", "calm"),
            selected_vibes=state.get("selected_vibes", []),
            user_text=state.get("input_text", ""),
        ),
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
        f"selection_guidance: {state.get('selection_guidance') or {}}",
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
            "selection_guidance": state.get("selection_guidance") or {},
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
        context_text=state["payload"].text,
        selection_guidance=state.get("selection_guidance"),
    )
    # Repeat the validation at the workflow boundary so later changes cannot
    # accidentally return an unverified track for an explicit hard request.
    tracks = validate_hard_constraints(tracks, state["payload"].text)
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
    gemini_copy_attempted = False
    gemini_copy_error = None
    if not state.get("defer_gemini_copy"):
        try:
            gemini_copy_attempted = True
            recommendation_copy = generate_recommendation_copy(
                mood,
                input_text,
                [track.model_dump(mode="json") for track in tracks],
                selected_vibes=selected_vibes,
                rag_guidance=state.get("selection_guidance"),
            )
            if recommendation_copy is None:
                gemini_copy_error = "Gemini returned an empty or invalid JSON recommendation response"
        except GeminiServiceError as exc:
            gemini_copy_error = str(exc)
            recommendation_copy = None

    message = (
        recommendation_copy.get("message")
        if recommendation_copy and _is_safe_recommendation_message(recommendation_copy.get("message"))
        else build_recommendation_message(mood, input_text, len(tracks), tracks)
    )
    enriched_tracks, reason_map = _apply_recommendation_copy(tracks, recommendation_copy, mood, input_text)
    return {
        "recommendation_copy": recommendation_copy,
        "message": message,
        "tracks": enriched_tracks,
        "generation_profile": {
            "llm_provider": "gemini",
            "gemini_copy_model": settings.gemini_copy_model,
            "demo_mode": getattr(state.get("user"), "auth_provider", None) == "demo",
            "has_rag_context": bool(state.get("rag_context")),
            "has_selected_vibes": bool(state.get("selected_vibes")),
            "track_count": len(enriched_tracks),
            "gemini_copy_attempted": gemini_copy_attempted,
            "gemini_copy_succeeded": bool(recommendation_copy),
            "gemini_reason_count": len(reason_map),
            "gemini_copy_error": gemini_copy_error,
            "gemini_copy_pending": bool(state.get("defer_gemini_copy")),
            "reason_source": "gemini" if reason_map else "fallback",
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


def complete_recommendation_copy(recommendation_id: int) -> None:
    """Generate Gemini copy after the immediate fallback response is already delivered."""
    db = SessionLocal()
    try:
        recommendation = db.get(Recommendation, recommendation_id)
        if recommendation is None:
            return

        tracks = [TrackSummary.model_validate(track) for track in (recommendation.tracks or []) if isinstance(track, dict)]
        free_text, selected_vibes = _split_context(recommendation.query)
        input_text = free_text or recommendation.query or ""
        snapshot = recommendation.context_snapshot or {}
        guidance = snapshot.get("selection_guidance") if isinstance(snapshot, dict) else None
        copy_error = None
        recommendation_copy = None
        try:
            recommendation_copy = generate_recommendation_copy(
                recommendation.mood,
                input_text,
                [track.model_dump(mode="json") for track in tracks],
                selected_vibes=selected_vibes or recommendation.selected_vibes or [],
                rag_guidance=guidance if isinstance(guidance, dict) else None,
            )
        except GeminiServiceError as exc:
            copy_error = str(exc)
        if recommendation_copy is None and copy_error is None:
            copy_error = "Gemini returned no usable recommendation copy"

        enriched_tracks, reason_map = _apply_recommendation_copy(tracks, recommendation_copy, recommendation.mood, input_text)
        if recommendation_copy and _is_safe_recommendation_message(recommendation_copy.get("message")):
            recommendation.message = str(recommendation_copy["message"])
        recommendation.tracks = [track.model_dump(mode="json", exclude_none=True) for track in enriched_tracks]
        profile = dict(recommendation.generation_profile or {})
        profile.update(
            {
                "gemini_copy_pending": False,
                "gemini_copy_model": settings.gemini_copy_model,
                "gemini_copy_attempted": True,
                "gemini_copy_succeeded": bool(recommendation_copy),
                "gemini_reason_count": len(reason_map),
                "gemini_copy_error": copy_error,
                "reason_source": "gemini" if reason_map else "fallback",
            }
        )
        recommendation.generation_profile = profile
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


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
    defer_gemini_copy: bool = False,
) -> RecommendationWorkflowState:
    state: RecommendationWorkflowState = {
        "db": db,
        "request": request,
        "response": response,
        "user": user,
        "payload": payload,
        "defer_gemini_copy": defer_gemini_copy,
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
