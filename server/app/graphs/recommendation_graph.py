from __future__ import annotations

from collections import Counter
from functools import lru_cache
import logging
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
from app.services.gemini_service import (
    GeminiServiceError,
    _family_trip_reason_ingredient,
    _recommendation_role,
    generate_recommendation_copy,
)
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
    _enforce_korean_band_rock_selection,
    _is_korean_band_rock_track,
    _is_calm_jazz_instrument_request,
    _is_dream_pop_synth_request,
    _is_drive_request,
    _korean_band_rock_preference_strength,
    build_selection_debug,
    _split_context,
    build_recommendation_message,
    build_track_reason,
    ensure_recommendation_count,
    _track_history_key,
    recommend_tracks,
    validate_hard_constraints,
)

logger = logging.getLogger(__name__)

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
    recent_track_keys: set[str]
    mood: str
    rag_context: str | None
    selection_guidance: dict[str, Any]
    llm_context: str
    context_snapshot: dict[str, Any]
    generation_profile: dict[str, Any]
    selection_profile: dict[str, Any]
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
        "몸과 마음을 달래",
        "마음을 달래",
        "풀어보세요",
        "날려보세요",
        "날려보낼",
        "풀어낼",
        "털어낼",
        "전환해 보세요",
        "기분을 바꿔보세요",
        "풀 수 있도록",
        "곁에 머물",
        "마음을 안아",
        "감정을 보듬",
        "위로를 건네",
    )
    return any(marker in lowered for marker in outcome_markers)


def _has_unnatural_korean_fragment(reason: str) -> bool:
    fragments = (
        "숨 고르기 어울",
        "정리하기 잘 맞",
        "시간 만들기 좋",
        "머물기 적절",
        "쉬어가기 어울",
        "분위기이",
        "느낌이이",
        "곡이이",
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
        "가 담긴",
        "만들어줘",
        "만들어 줘",
        "대중성이 돋보",
        "골고루 담겨",
        "분위기 곡",
        "에너지 곡",
        "대중성 곡",
        "서로 다른 특징이 함께 느껴지는",
        "연주곡 · 재즈",
        "재즈 계열의 리듬, 연주곡",
        "감정적이지만",
        "감정적인 분위기",
        "감정적인 여운",
        "분위기 및",
        "사운드 및",
        "듣고 싶을 때 듣기 좋아요",
        "엠비언트",
        "대기감",
        "스페이시한 공간감",
        "깊이감을 더해",
        "여운을 더해",
        "겹겹이 쌓이",
        "아스라이",
        "스며드는",
        "곁에 머무",
        "깊이 번지",
        "감성을 품은",
        "귀를 두",
        "흐름에 머물",
        "감성적인 흐름",
        "분위기의 결",
        "사운드의 결",
    )
    return any(marker in reason for marker in markers)


def _uses_formal_recommendation_style(reason: str) -> bool:
    """Keep recommendation reasons in the app's conversational haeyo체."""
    return any(marker in reason for marker in ("입니다", "습니다", "합니다"))


def _has_incomplete_reason_sentence(reason: str) -> bool:
    cleaned = re.sub(r"\s+", " ", reason.strip()).strip('"\'')
    if not cleaned:
        return True

    # Gemini can return syntactically valid JSON while the final Korean
    # sentence is still cut off at the output limit. Check grammar, not only
    # JSON validity, so the track can use its local fallback reason.
    incomplete_endings = (
        "고 싶을",
        "할 때,",
        "하면서",
        "하며",
        "하고",
        "이고",
        "이며",
        "이",
        "가",
        "을",
        "를",
        "에",
    )
    if cleaned.endswith(incomplete_endings):
        return True

    return not bool(re.search(r"(?:요|이에요|해요|맞아요|어울려요|좋아요|됩니다|있어요)[.!?]?$", cleaned))


def _leaks_long_focus_context(reason: str, input_text: str) -> bool:
    lowered = input_text.lower()
    is_long_focus = any(token in input_text or token in lowered for token in ("오래 앉", "오랫동안", "장시간", "노트북 앞")) and any(
        token in input_text or token in lowered for token in ("몰입", "집중", "산만하지")
    )
    if _is_dream_pop_synth_request(input_text):
        return any(
            marker in reason
            for marker in ("공부", "작업", "해야 할 일", "집중이 느슨", "공부 흐름", "작업 흐름", "업무", "페이스 유지")
        )
    if not is_long_focus:
        return False
    return any(marker in reason for marker in ("잠시 쉬어가며", "해야 할 일", "공부 흐름", "집중이 흔들", "페이스를 잡"))


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
        "감성적으로 다가",
        "은은하게 번",
        "포근하게 이어",
        "마음에 스며",
        "깊은 결",
        "차분한 결",
        "음악의 결",
        "분위기의 결",
        "흐름이 담겨",
        "연주곡 흐름",
        "구성되어 있어",
        "깊이감을 더해",
        "포근하게 펼쳐",
        "자연스럽게 스며",
        "감정의 온도",
        "잠겨 머물",
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
        "자극 없이",
        "기분을 가볍게 더",
        "기분을 더하고 싶",
        "흥겨움을 더해",
        "에너지를 더해",
        "에너지 넘치는",
        "펼쳐지는 곡",
        "매력을 담은",
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


def _second_sentence_signature(reason: str) -> str:
    sentences = [sentence.strip() for sentence in re.findall(r"[^.!?]+[.!?]", reason) if sentence.strip()]
    return re.sub(r"\s+", " ", sentences[1]).strip() if len(sentences) > 1 else ""


def _has_two_sentence_reason_structure(reason: str) -> bool:
    """Reject copy that merges a track feature and listening role into one sentence."""
    sentences = [sentence.strip() for sentence in re.findall(r"[^.!?]+[.!?]", reason) if sentence.strip()]
    remainder = re.sub(r"[^.!?]+[.!?]", "", reason).strip()
    return len(sentences) == 2 and not remainder


def _has_malformed_reason_compound(reason: str) -> bool:
    """Catch feature/context noun chains that are hard to read even with two sentences."""
    markers = (
        "에너지가 느껴지는 여러 사람",
        "에너지를 지닌 여름 여행",
        "에너지를 전하는 가족 여행",
        "여름 여행 기분 좋은 곡",
        "곡이며 가족과",
    )
    return any(marker in reason for marker in markers)


def _repeats_family_trip_reason_logic(reason: str, input_text: str) -> bool:
    """Keep the feature sentence from restating the travel role sentence."""
    if not ("가족" in input_text and ("여행" in input_text or "차" in input_text)):
        return False
    sentences = [sentence.strip() for sentence in re.findall(r"[^.!?]+", reason) if sentence.strip()]
    if len(sentences) != 2:
        return False
    first, second = sentences
    return any(token in first and token in second for token in ("여름", "설렘", "차 안", "이동"))


def _leaks_dawn_sentimental_context(reason: str, input_text: str) -> bool:
    """Reject stale study/work fallback copy for a late-night aesthetic request."""
    text = input_text.lower()
    is_dawn_sentimental = any(token in input_text or token in text for token in ("새벽", "센치")) and any(
        token in input_text or token in text for token in ("몽환", "감성", "센치", "플레이리스트")
    )
    if not is_dawn_sentimental:
        return False
    return any(
        marker in reason
        for marker in (
            "해야 할 일",
            "공부",
            "업무",
            "작업",
            "집중",
            "페이스",
            "한 가지 일",
            "쉬어가며 듣기",
            "긴장을",
            "회복",
            "위로",
        )
    )


def _uses_unselected_family_energy_feature(
    reason: str,
    track: TrackSummary,
    index: int,
    input_text: str,
    mood: str,
) -> bool:
    """Do not accept an energy-led Gemini reason when code chose another feature."""
    role = _recommendation_role(mood, index, input_text, reason_facts=track.reason_facts)
    ingredient = _family_trip_reason_ingredient(track.reason_facts, role)
    if not ingredient or ingredient.get("feature_source") == "upbeat_moment":
        return False
    first_sentence = _first_sentence_signature(reason)
    return any(marker in first_sentence for marker in ("에너지", "경쾌", "활기찬"))


def _uses_unsupported_dream_sound_feature(reason: str, track: TrackSummary, input_text: str) -> bool:
    """Keep first-sentence genre claims tied to this track's supplied tags."""
    if not _is_dream_pop_synth_request(input_text):
        return False
    tags = {str(tag).lower() for tag in (track.reason_facts or {}).get("tags", []) if tag}
    first_sentence = _first_sentence_signature(reason)
    required_tags = {
        "앰비언트": {"ambient"},
        "엠비언트": {"ambient"},
        "일렉트로닉": {"electronic"},
        "신스": {"synth", "synth-pop"},
        "신스팝": {"synth-pop"},
        "드림 팝": {"dream-pop"},
        "슈게이즈": {"shoegaze"},
    }
    if any(label in first_sentence and not tags.intersection(required) for label, required in required_tags.items()):
        return True
    if "공간감" in first_sentence and "spacious" not in tags:
        return True
    if "몰입감" in first_sentence and "immersive" not in tags:
        return True
    return False


def _repeats_dream_feature_in_role(reason: str, input_text: str) -> bool:
    """Keep track facts and the listening role from restating the same trait."""
    if not _is_dream_pop_synth_request(input_text):
        return False
    first_sentence = _first_sentence_signature(reason)
    second_sentence = _second_sentence_signature(reason)
    return any(
        marker in first_sentence and marker in second_sentence
        for marker in ("몽환", "감성", "공간감", "차분", "신스팝", "앰비언트", "슈게이즈")
    )


def _is_feature_role_compatible(track: TrackSummary, mood: str, input_text: str, index: int) -> bool:
    """Reject a reason whose role contradicts verified track facts."""
    role = _recommendation_role(mood, index, input_text, reason_facts=track.reason_facts)
    focus = role.get("focus", "")
    facts = track.reason_facts or {}
    if "드라이브" in input_text or "차 타고" in input_text or "도로 위" in input_text:
        tags = {str(tag).lower() for tag in facts.get("tags", []) if tag}
        if "팝 분위기 더하기" in focus and not tags.intersection({"pop", "dance-pop", "synth-pop", "pop-punk"}):
            return False
        if "펑크 에너지 더하기" in focus and not tags.intersection({"punk", "pop-punk", "rock"}):
            return False
        if focus in {"공부 템포 유지", "현재 공부 흐름 유지", "몰입 상태 이어가기", "지루함 방지", "짧은 분위기 환기"}:
            return False
    if "장시간" not in input_text and "오래 앉" not in input_text and "오랫동안" not in input_text:
        return True
    if focus in {"가벼운 리듬 더하기", "단조로움 줄이기"} and facts.get("light_rhythm_fit") is not True:
        return False
    if focus == "낮은 자극으로 배경 유지" and facts.get("distraction_risk") == "high":
        return False
    if facts.get("feature_role_compatibility") is not None and float(facts["feature_role_compatibility"]) < 0.4:
        return False
    return True


def _is_safe_recommendation_message(
    message: object,
    input_text: str = "",
    selected_vibes: list[str] | None = None,
) -> bool:
    if not isinstance(message, str) or not message.strip():
        return False
    if _is_dream_pop_synth_request(input_text) and any(
        marker in message
        for marker in (
            "공부", "작업", "해야 할 일", "집중이 느슨", "공부 흐름", "작업 흐름", "업무", "페이스 유지",
            "몰입할 수 있도록", "깊이 빠져들", "빠져들게", "채워드릴", "들려드릴", "선사할",
        )
    ):
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
        "채워보세요",
        "즐겨보세요",
        "만끽해 보세요",
        "느껴보세요",
        "머물러 보세요",
        "몰입을 도와",
        "집중을 도와",
        "몸과 마음을 달래",
        "마음을 달래",
        "날려보낼",
        "풀어낼",
        "털어낼",
        "metadata",
        "확인되지 않은",
        "추정하지 않았",
        "검증된 곡",
        "검증을 통과",
        "ranking",
        "후보를",
        "방식으로 구성",
        "일부만 포함",
    )
    if any(marker in message for marker in disallowed_markers) or ("초조" in message and "조급" in message):
        return False
    if "잠겨" in message and "머물" in message:
        return False
    is_family_trip = "가족" in input_text and ("여행" in input_text or "차" in input_text)
    if is_family_trip and any(marker in message for marker in ("더해줄", "채웠습니다", "만끽해", "즐겨보세요")):
        return False
    is_drive_request = any(marker in input_text for marker in ("차 타고", "차 안", "드라이브", "도로 위"))
    if is_drive_request and any(
        marker in message
        for marker in ("텐션을 높여", "텐션을 올려", "기분을 끌어올려", "채워줄", "떠나보세요")
    ):
        return False

    # Explicitly selected moods must remain visible in dawn/sentimental summaries;
    # MBTI-derived aesthetic terms must not replace them.
    is_dawn_sentimental = any(token in input_text.lower() for token in ("새벽", "센치"))
    if is_dawn_sentimental and selected_vibes:
        vibe_terms = {
            "몽환적인": ("몽환",),
            "감성적인": ("감성", "서정"),
        }
        for vibe in selected_vibes:
            terms = vibe_terms.get(vibe)
            if terms and not any(term in message for term in terms):
                return False
    return True


def _apply_recommendation_copy(
    tracks: list[TrackSummary],
    recommendation_copy: dict[str, Any] | None,
    mood: str,
    input_text: str,
) -> tuple[list[TrackSummary], dict[str, str]]:
    copy_reasons = recommendation_copy.get("track_reasons") if recommendation_copy else []
    reason_map: dict[str, str] = {}
    used_first_sentences: set[str] = set()
    used_second_sentences: set[str] = set()
    for index, track in enumerate(tracks):
        for item in copy_reasons:
            if not isinstance(item, dict) or str(item.get("track_id")) != track.track_id:
                continue
            reason = str(item.get("reason") or "").strip()
            first_sentence = _first_sentence_signature(reason)
            second_sentence = _second_sentence_signature(reason)
            if (
                not reason
                or not first_sentence
                or first_sentence in used_first_sentences
                or second_sentence in used_second_sentences
                or _is_generic_track_reason(reason)
                or _exposes_internal_recommendation_metadata(reason)
                or _overstates_listening_effect(reason)
                or _has_unnatural_korean_fragment(reason)
                or _uses_disallowed_infinitive_pattern(reason)
                or _uses_unnatural_recommendation_language(reason)
                or _uses_formal_recommendation_style(reason)
                or _has_incomplete_reason_sentence(reason)
                or _leaks_long_focus_context(reason, input_text)
                or _uses_repetitive_or_abstract_language(reason)
                or _repeats_time_clause(reason)
                or not _has_two_sentence_reason_structure(reason)
                or _has_malformed_reason_compound(reason)
                or _repeats_family_trip_reason_logic(reason, input_text)
                or _leaks_dawn_sentimental_context(reason, input_text)
                or _uses_unselected_family_energy_feature(reason, track, index, input_text, mood)
                or _uses_unsupported_dream_sound_feature(reason, track, input_text)
                or _repeats_dream_feature_in_role(reason, input_text)
                or _mentions_unsupported_music_detail(reason, track)
                or not _is_feature_role_compatible(track, mood, input_text, index)
                or not _has_verified_grounding(item, track)
            ):
                continue
            reason_map[track.track_id] = reason
            used_first_sentences.add(first_sentence)
            used_second_sentences.add(second_sentence)
            break
    enriched_tracks: list[TrackSummary] = []
    fallback_first_sentences: set[str] = set(reason_map.values())
    fallback_first_sentences = {
        _first_sentence_signature(reason) for reason in fallback_first_sentences if reason
    }
    for index, track in enumerate(tracks):
        reason = reason_map.get(track.track_id)
        if reason is None:
            role = _recommendation_role(mood, index, input_text, reason_facts=track.reason_facts)
            reason = build_track_reason(track, mood, input_text, index, role)
            # For catalog-backed jazz fallback, prefer another supplied feature
            # when the first sentence was already used in this playlist. This
            # changes wording only; it never invents recording metadata.
            if (
                _is_calm_jazz_instrument_request(input_text)
                or _is_drive_request(input_text)
                or _is_dream_pop_synth_request(input_text)
            ):
                for feature_index in range(index + 1, index + 8):
                    if (
                        _first_sentence_signature(reason) not in fallback_first_sentences
                        and _second_sentence_signature(reason) not in used_second_sentences
                    ):
                        break
                    alternative_role = _recommendation_role(
                        mood,
                        feature_index,
                        input_text,
                        reason_facts=track.reason_facts,
                    )
                    alternative = build_track_reason(
                        track,
                        mood,
                        input_text,
                        index,
                        alternative_role,
                        reason_feature_index=feature_index,
                    )
                    if (
                        _first_sentence_signature(alternative) not in fallback_first_sentences
                        and _second_sentence_signature(alternative) not in used_second_sentences
                    ):
                        reason = alternative
                        break
            fallback_first_sentences.add(_first_sentence_signature(reason))
            used_second_sentences.add(_second_sentence_signature(reason))
        enriched_tracks.append(track.model_copy(update={"reason": reason}))
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
    recent_track_keys = {
        _track_history_key(track.get("name"), track.get("artist_name"))
        for recommendation in recent_recommendations
        for track in (getattr(recommendation, "tracks", []) or [])
        if isinstance(track, dict) and track.get("name") and track.get("artist_name")
    }
    return {
        "free_text": free_text,
        "selected_vibes": selected_vibes,
        "input_text": input_text,
        "preference_context": preference_context,
        "recent_mood_summary": recent_mood_summary,
        "recent_recommendation_summary": recent_recommendation_summary,
        "recent_track_keys": recent_track_keys,
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
        recent_track_keys=state.get("recent_track_keys") or set(),
    )
    retrieved_candidate_count = len(tracks)
    ranked_candidate_count = len(tracks)
    # Repeat the validation at the workflow boundary so later changes cannot
    # accidentally return an unverified track for an explicit hard request.
    selected_count_before_validation = len(tracks)
    tracks = validate_hard_constraints(tracks, state["payload"].text)
    tracks = _enforce_korean_band_rock_selection(tracks, state["payload"].text, 6)
    selected_count_after_validation = len(tracks)
    tracks = ensure_recommendation_count(
        tracks,
        state.get("mood", "calm"),
        state["payload"].text,
        access_token or None,
        target=6,
        selection_guidance=state.get("selection_guidance"),
        recent_track_keys=state.get("recent_track_keys") or set(),
    )
    korean_band_rock_preference = _korean_band_rock_preference_strength(state["payload"].text)
    exact_korean_band_rock_tracks = [track for track in tracks if _is_korean_band_rock_track(track)]
    recent_track_keys = state.get("recent_track_keys") or set()
    recent_overlap_count = sum(
        _track_history_key(track.name, track.artist_name) in recent_track_keys for track in tracks
    )
    selected_categories = [
        (track.reason_facts or {}).get("selection_category")
        for track in tracks
        if (track.reason_facts or {}).get("selection_category")
    ]
    track_facts = [track.reason_facts or {} for track in tracks]
    focus_coverage = {
        "low_stimulation_coverage": sum(bool(facts.get("low_stimulation_fit")) for facts in track_facts),
        "calm_coverage": sum(bool(facts.get("calm_fit")) for facts in track_facts),
        "mellow_coverage": sum(bool(facts.get("mellow_fit")) for facts in track_facts),
        "light_rhythm_coverage": sum(bool(facts.get("light_rhythm_fit")) for facts in track_facts),
        "higher_rhythm_count": sum(facts.get("rhythmic_intensity") == "high" for facts in track_facts),
        "relaxed_coverage": sum(bool(facts.get("relaxed_fit")) for facts in track_facts),
        "high_distraction_count": sum(facts.get("distraction_risk") == "high" for facts in track_facts),
        "prominent_vocal_count": sum("prominent_vocal" in set(facts.get("tags", [])) for facts in track_facts),
        "high_intensity_count": sum(
            bool(set(facts.get("tags", [])) & {"high_energy", "aggressive", "fast", "rhythmic_strong"})
            for facts in track_facts
        ),
    }
    calm_anchor_count = sum(
        bool(facts.get("low_stimulation_fit")) and not bool(facts.get("light_rhythm_fit"))
        for facts in track_facts
    )
    light_rhythm_track_count = sum(bool(facts.get("light_rhythm_fit")) for facts in track_facts)
    neutral_bridge_count = max(0, len(tracks) - calm_anchor_count - light_rhythm_track_count)
    return {
        "access_token": access_token,
        "tracks": tracks,
        "selection_profile": {
            **build_selection_debug(state["payload"].text, tracks),
            "korean_band_rock_preference": korean_band_rock_preference,
            "korean_band_rock_exact_count": len(exact_korean_band_rock_tracks),
            "non_matching_track_count": len(tracks) - len(exact_korean_band_rock_tracks),
            "selected_track_titles": [track.display_title or track.name for track in tracks],
            "target_count": 6,
            "recent_track_count": len(recent_track_keys),
            "recent_overlap_count": recent_overlap_count,
            "diversity_candidate_pool_multiplier": 3,
            "selected_categories": selected_categories,
            "focus_coverage": focus_coverage,
            "calm_anchor_count": calm_anchor_count,
            "light_rhythm_track_count": light_rhythm_track_count,
            "neutral_bridge_count": neutral_bridge_count,
            "retrieved_candidate_count": retrieved_candidate_count,
            "ranked_candidate_count": ranked_candidate_count,
            "selected_tracks_before_validation_count": selected_count_before_validation,
            "selected_tracks_after_validation_count": selected_count_after_validation,
            "refill_count": max(0, len(tracks) - selected_count_after_validation),
            "final_rendered_track_count": len(tracks),
        },
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
        if recommendation_copy
        and _is_safe_recommendation_message(
            recommendation_copy.get("message"), input_text, selected_vibes
        )
        else build_recommendation_message(mood, input_text, len(tracks), tracks)
    )
    enriched_tracks, reason_map = _apply_recommendation_copy(tracks, recommendation_copy, mood, input_text)
    parsed_reason_count = len(
        recommendation_copy.get("track_reasons", [])
        if isinstance(recommendation_copy, dict)
        else []
    )
    fallback_reason_count = len(enriched_tracks) - len(reason_map)
    logger.info(
        "[Mood Sync] recommendation reason pipeline input/parsed/accepted/stored/rendered counts: "
        "tracks=%s parsed=%s accepted=%s stored=%s rendered=%s fallback=%s",
        len(tracks),
        parsed_reason_count,
        len(reason_map),
        len(enriched_tracks),
        len(enriched_tracks),
        fallback_reason_count,
    )
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
            "tracks_sent_to_reason_generator": len(tracks),
            "gemini_copy_attempted": gemini_copy_attempted,
            "gemini_copy_succeeded": bool(recommendation_copy),
            "gemini_reason_count": len(reason_map),
            "parsed_reason_count": parsed_reason_count,
            "accepted_reason_count": len(reason_map),
            "stored_reason_count": len(enriched_tracks),
            "rendered_reason_count": len(enriched_tracks),
            "fallback_reason_used": fallback_reason_count > 0,
            "fallback_reason_count": fallback_reason_count,
            "final_track_count": len(enriched_tracks),
            "rendered_card_count": len(enriched_tracks),
            "gemini_copy_error": gemini_copy_error,
            "gemini_copy_pending": bool(state.get("defer_gemini_copy")),
            "reason_source": "gemini" if reason_map else "fallback",
            "selection_profile": state.get("selection_profile") or {},
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
        parsed_reason_count = len(
            recommendation_copy.get("track_reasons", [])
            if isinstance(recommendation_copy, dict)
            else []
        )
        fallback_reason_count = len(enriched_tracks) - len(reason_map)
        logger.info(
            "[Mood Sync] deferred recommendation reason pipeline input/parsed/accepted/stored/rendered counts: "
            "tracks=%s parsed=%s accepted=%s stored=%s rendered=%s fallback=%s",
            len(tracks),
            parsed_reason_count,
            len(reason_map),
            len(enriched_tracks),
            len(enriched_tracks),
            fallback_reason_count,
        )
        if recommendation_copy and _is_safe_recommendation_message(
            recommendation_copy.get("message"),
            input_text,
            selected_vibes or recommendation.selected_vibes or [],
        ):
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
                "parsed_reason_count": parsed_reason_count,
                "accepted_reason_count": len(reason_map),
                "stored_reason_count": len(enriched_tracks),
                "rendered_reason_count": len(enriched_tracks),
                "fallback_reason_count": fallback_reason_count,
                "final_track_count": len(enriched_tracks),
                "rendered_card_count": len(enriched_tracks),
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
