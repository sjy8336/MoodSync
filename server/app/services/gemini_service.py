from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


GEMINI_ALLOWED_MOODS = {
    "happy",
    "excited",
    "sad",
    "lonely",
    "tired",
    "angry",
    "anxious",
    "focused",
    "calm",
}
GEMINI_REQUEST_TIMEOUT_SECONDS = 18

_USER_FACING_METADATA_LABELS = {
    "dreamy": "몽환적인 분위기",
    "soft": "부드러운 분위기",
    "warm": "따뜻한 분위기",
    "calm": "차분한 분위기",
    "comfort": "편안하고 위로되는 분위기",
    "emotional": "감정적인 분위기",
    "rnb": "R&B",
    "soul": "소울",
    "instrumental": "연주 중심 구성",
    "jazz": "재즈",
    "upbeat": "경쾌한 에너지",
    "high_energy": "높은 에너지",
    "driving": "추진력 있는 리듬",
    "love": "사랑 노래 분위기",
}

_RECOMMENDATION_ROLES = {
    "anxious": [
        ("생각의 속도를 늦추기", "결과를 계속 곱씹고 있을 때"),
        ("긴장을 느슨하게 풀기", "스스로를 너무 몰아붙이고 있을 때"),
        ("복잡한 생각 정리하기", "머릿속이 여러 생각으로 복잡할 때"),
        ("조용한 위로의 시간 만들기", "계획대로 되지 않아 지친 순간"),
        ("잠시 숨 고르기", "미래에 대한 걱정이 커질 때"),
        ("현실적인 고민에서 거리 두기", "잠깐 쉬어가며 마음을 정돈하고 싶을 때"),
    ],
    "focused": [
        ("집중 전 긴장 낮추기", "해야 할 일이 많아 마음이 급해질 때"),
        ("흐름을 부드럽게 이어가기", "한 가지 일에 오래 머물고 싶을 때"),
        ("산만한 생각 정리하기", "주변 자극 때문에 집중이 흔들릴 때"),
        ("차분한 작업 분위기 만들기", "조용히 페이스를 잡고 싶을 때"),
        ("잠깐의 리셋 만들기", "집중이 흐트러져 쉬어갈 때"),
        ("마무리까지 페이스 유지하기", "해야 할 일을 천천히 정리하고 싶을 때"),
    ],
    "happy": [
        ("기분 좋은 흐름 유지", "지금의 좋은 흐름을 그대로 이어가고 싶을 때"),
        ("적당한 활기 더하기", "너무 처지지 않게 가벼운 활기를 더하고 싶을 때"),
        ("공부 템포 유지", "해야 할 일을 같은 템포로 이어가고 싶을 때"),
        ("짧은 분위기 환기", "공부 흐름을 크게 바꾸지 않고 분위기를 잠깐 바꾸고 싶을 때"),
        ("지루함 방지", "집중이 조금 느슨해지는 구간에 기분을 환기하고 싶을 때"),
        ("몰입 상태 이어가기", "지금의 몰입을 무리 없이 이어가고 싶을 때"),
    ],
    "excited": [
        ("기분 좋은 흐름 유지", "지금의 좋은 흐름을 그대로 이어가고 싶을 때"),
        ("적당한 활기 더하기", "너무 처지지 않게 가벼운 활기를 더하고 싶을 때"),
        ("공부 템포 유지", "해야 할 일을 같은 템포로 이어가고 싶을 때"),
        ("짧은 분위기 환기", "공부 흐름을 크게 바꾸지 않고 분위기를 잠깐 바꾸고 싶을 때"),
        ("지루함 방지", "집중이 조금 느슨해지는 구간에 기분을 환기하고 싶을 때"),
        ("몰입 상태 이어가기", "지금의 몰입을 무리 없이 이어가고 싶을 때"),
    ],
}

_STUDY_FLOW_ROLES = [
    ("현재 공부 흐름 유지", "지금의 공부 흐름을 그대로 이어가고 싶을 때"),
    ("적당한 활기 더하기", "너무 처지지 않게 가벼운 활기를 더하고 싶을 때"),
    ("기분 좋은 텐션 유지", "기분 좋은 텐션을 과하지 않게 이어가고 싶을 때"),
    ("지루함 방지", "집중이 조금 느슨해지는 구간에 분위기를 환기하고 싶을 때"),
    ("공부 템포 유지", "해야 할 일을 같은 템포로 이어가고 싶을 때"),
    ("짧은 분위기 환기", "공부 흐름을 크게 바꾸지 않고 분위기를 잠깐 바꾸고 싶을 때"),
]

_SLEEP_ROLES = [
    ("잠들기 전 긴장 내려놓기", "잠들기 전 몸과 마음의 긴장을 조금 내려놓고 싶을 때"),
    ("생각의 속도 늦추기", "생각이 계속 이어져 쉽게 잠들기 어려운 순간"),
    ("조용히 쉬어가기", "자극적인 분위기보다 조용히 쉬어가고 싶은 밤"),
    ("수면 전 분위기 가라앉히기", "잠자리에 들기 전 하루를 차분히 마무리하고 싶을 때"),
    ("복잡한 생각에서 거리 두기", "여러 생각이 한꺼번에 떠오르는 순간"),
    ("편안한 잠자리 준비", "편안한 분위기 속에서 잠자리를 준비하고 싶을 때"),
]


def _build_listening_request_context(text: str | None, selected_vibes: list[str] | None) -> dict[str, object]:
    """Extract explicit goals and limits without adding another model call."""
    raw_text = text or ""
    lowered = raw_text.lower()
    is_studying = any(token in raw_text or token in lowered for token in ("공부", "과제", "작업", "집중", "몰입"))
    avoids_overstimulation = any(
        token in raw_text or token in lowered
        for token in ("소란", "시끄", "방해", "과하지", "너무 강", "자극")
    )
    is_going_well = any(token in raw_text or token in lowered for token in ("잘되고", "잘 되고", "순조", "흐름"))
    is_preparing_sleep = any(
        token in raw_text or token in lowered
        for token in ("수면", "잠들", "잠을", "잠 못", "잠자", "자고 싶", "잘 때")
    )
    instrumental_required = any(
        token in lowered
        for token in ("가사가 없는", "가사 없는", "가사없이", "가사 없이", "무가사", "연주곡", "보컬 없는", "보컬이 없는", "instrumental")
    )

    context: dict[str, object] = {
        "context": "공부 또는 작업" if is_studying else "",
        "current_state": [],
        "goal": [],
        "avoid": [],
        "priority": [],
        "hard_constraints": {"instrumental_required": instrumental_required},
    }
    if is_preparing_sleep:
        context["context"] = "수면 준비"
        context["current_state"] = ["수면 부족으로 피곤함", "생각이 많아 쉬기 어려움"]
        context["goal"] = ["잠들기 전 편안한 분위기", "생각을 잠시 내려놓기"]
        context["avoid"] = ["보컬 또는 가사", "수면에 방해되는 높은 자극"]
        context["priority"] = ["수면 전 안정", "낮은 자극", "연주곡" if instrumental_required else "차분한 분위기"]
    elif is_studying and is_going_well:
        context["current_state"] = ["이미 집중 흐름이 이어지고 있음", "기분 좋게 몰입 중"]
        context["goal"] = ["현재 공부 흐름 유지", "적당한 활기 유지"]
    elif is_studying:
        context["goal"] = ["공부 또는 작업 흐름 유지"]
    if avoids_overstimulation:
        context["avoid"] = ["지나치게 높은 자극", "집중을 깨는 소란스러움"]
    if is_studying and avoids_overstimulation:
        context["priority"] = ["몰입 유지", "과하지 않은 활기", "높은 에너지"]
    elif selected_vibes:
        context["priority"] = list(selected_vibes)
    return context


class GeminiServiceError(RuntimeError):
    pass


def is_gemini_configured() -> bool:
    return bool(settings.gemini_api_key)


def _gemini_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise GeminiServiceError("Gemini API key is not configured")

    base_url = settings.gemini_base_url.rstrip("/")
    url = f"{base_url}{path}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.gemini_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=GEMINI_REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        raise GeminiServiceError(f"Gemini request failed: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise GeminiServiceError(f"Gemini request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise GeminiServiceError(
            f"Gemini request timed out after {GEMINI_REQUEST_TIMEOUT_SECONDS} seconds"
        ) from exc
    except json.JSONDecodeError as exc:
        raise GeminiServiceError("Gemini returned a non-JSON API response") from exc


def _extract_message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _parse_json_content(content: str) -> dict[str, Any] | None:
    raw = content.strip()
    if not raw:
        return None

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        # Gemini can occasionally append a short explanation after a valid
        # structured object. Keep the object instead of discarding the copy.
        try:
            data, _ = json.JSONDecoder().raw_decode(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _normalize_metadata_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split()).strip()
    if not text or len(text) > 90 or re.search(r"_{2,}", text):
        return None
    if text.lower() in {"null", "none", "undefined", "unknown", "n/a", "-"}:
        return None
    for raw, label in _USER_FACING_METADATA_LABELS.items():
        text = re.sub(rf"\b{re.escape(raw)}\b", label, text, flags=re.IGNORECASE)
    return text


def _normalize_reason_facts(facts: object) -> dict[str, object]:
    """Expose only short, human-readable metadata to the copy-generation prompt."""
    if not isinstance(facts, dict):
        return {}

    normalized: dict[str, object] = {}
    for key in ("sound_profile", "listening_effect"):
        text = _normalize_metadata_text(facts.get(key))
        if text:
            normalized[key] = text

    for key in ("tags", "moods"):
        values = facts.get(key)
        if not isinstance(values, list):
            continue
        labels = [_normalize_metadata_text(value) for value in values]
        cleaned = list(dict.fromkeys(label for label in labels if label))
        if cleaned:
            normalized[key] = cleaned[:4]
    return normalized


def _build_music_feature_summary(facts: object) -> str | None:
    """Turn known tags into one Korean phrase instead of exposing a tag list."""
    if not isinstance(facts, dict):
        return None

    sound_profile = _normalize_metadata_text(facts.get("sound_profile"))
    if sound_profile:
        return sound_profile

    raw_tags: set[str] = set()
    for key in ("tags", "moods"):
        values = facts.get(key)
        if isinstance(values, list):
            raw_tags.update(
                str(tag).strip().lower()
                for tag in values
                if isinstance(tag, str) and _normalize_metadata_text(tag)
            )
    combinations = (
        (("dreamy", "calm"), "몽환적이고 차분하게 가라앉는 분위기"),
        (("soft", "warm"), "부드럽고 따뜻하게 이어지는 분위기"),
        (("comfort", "calm"), "편안하면서 차분한 분위기"),
        (("emotional", "soft"), "감정적이지만 부드럽게 이어지는 분위기"),
        (("rnb", "soul"), "차분한 소울·R&B 분위기"),
        (("upbeat", "high_energy"), "밝고 활기찬 분위기"),
    )
    for required_tags, summary in combinations:
        if set(required_tags).issubset(raw_tags):
            return summary

    labels = [_USER_FACING_METADATA_LABELS[tag] for tag in raw_tags if tag in _USER_FACING_METADATA_LABELS]
    if not labels:
        return None
    return " · ".join(sorted(labels)[:2])


def _recommendation_role(
    mood: str,
    index: int,
    context_text: str | None = None,
    selected_vibes: list[str] | None = None,
) -> dict[str, str]:
    request_context = _build_listening_request_context(context_text, selected_vibes)
    has_study_flow = bool(request_context["context"]) and bool(request_context["current_state"])
    is_sleep_context = request_context["context"] == "수면 준비"
    roles = (
        _SLEEP_ROLES
        if is_sleep_context
        else _STUDY_FLOW_ROLES
        if has_study_flow
        else _RECOMMENDATION_ROLES.get(mood, _RECOMMENDATION_ROLES["focused"])
    )
    focus, situation_angle = roles[index % len(roles)]
    return {"focus": focus, "situation_angle": situation_angle}


def _recommendation_copy_schema() -> dict[str, Any]:
    """Keep Gemini's OpenAI-compatible response constrained to the UI contract."""
    return {
        "name": "mood_sync_recommendation_copy",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "message": {"type": "string"},
                "track_reasons": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "track_id": {"type": "string"},
                            "reason": {"type": "string"},
                            "used_fact_keys": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["track_id", "reason", "used_fact_keys"],
                    },
                },
            },
            "required": ["message", "track_reasons"],
        },
    }


def analyze_mood_with_gemini(text: str) -> str | None:
    if not is_gemini_configured() or not text.strip():
        return None

    prompt = (
        "You classify Korean music mood requests into exactly one label.\n"
        "Return only JSON with the key mood.\n"
        f"Allowed moods: {', '.join(sorted(GEMINI_ALLOWED_MOODS))}.\n"
        "Choose the mood that best matches the user's current feeling and context.\n"
        "If the user gives a task context like studying, working, or a deadline, take that into account.\n"
        "Examples of task-focused context may still map to focused, anxious, tired, or calm depending on wording.\n"
    )
    response = _gemini_post(
        "/chat/completions",
        {
            "model": settings.gemini_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            "max_tokens": 80,
        },
    )
    data = _parse_json_content(_extract_message_content(response))
    mood = str(data.get("mood") or "").strip().lower() if data else ""
    return mood if mood in GEMINI_ALLOWED_MOODS else None


def generate_recommendation_copy(
    mood: str,
    context_text: str | None,
    tracks: list[dict[str, Any]],
    selected_vibes: list[str] | None = None,
    rag_guidance: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not is_gemini_configured() or not tracks:
        return None

    track_lines = []
    for index, track in enumerate(tracks):
        track_lines.append(
            {
                "track_id": str(track.get("track_id") or ""),
                "name": str(track.get("name") or ""),
                "artist_name": str(track.get("artist_name") or ""),
                "album_name": str(track.get("album_name") or ""),
                "verified_reason_facts": _normalize_reason_facts(track.get("reason_facts")),
                "music_feature": _build_music_feature_summary(track.get("reason_facts")),
                "recommendation_role": _recommendation_role(mood, index, context_text, selected_vibes),
            }
        )

    prompt = (
        "You write empathetic Korean copy for a mood-based music app.\n"
        "Return only JSON with keys message and track_reasons.\n"
        "The response must be one valid JSON object, never prose, Markdown, labels such as 'Track 1', or code fences.\n"
        'Expected shape: {"message":"...","track_reasons":[{"track_id":"...","reason":"...","used_fact_keys":["sound_profile"]}]}.\n'
        "message should be 2 short natural Korean sentences, warm and specific, not generic. Keep it under 140 Korean characters.\n"
        "Write the message as a music recommendation service, not as a person beside the user. Never say phrases like '곁을 지켜줄게요', '곁에 있을게요', or '다독여줄게요'.\n"
        "The user_text field is only the user's direct free text. selected_vibes is a separate list of chosen vibe tags.\n"
        "listening_request_context is application-extracted planning data with current_state, goal, avoid, context, and priority. Follow its priority order when selected_vibes conflict.\n"
        "Treat explicit limits such as 'too noisy', 'distracting', 'not too much', or 'too stimulating' as hard constraints. For studying, prefer maintaining the current flow and moderate energy over merely saying a track is exciting.\n"
        "When relevant, connect each reason to one distinct goal or avoid condition, such as keeping a study flow, adding modest energy, avoiding excessive stimulation, or preventing a sluggish mood. Do not repeat the same condition for all tracks.\n"
        "If verified metadata says high energy while the user wants less stimulation, do not claim that the track is not stimulating. Describe it only as a fit for a brief refresh or a moment when the user wants to raise the tempo.\n"
        "Do not say that music 'helps immersion' or 'helps concentration'. In the summary, describe only the listening context, such as '공부 흐름을 이어가면서 과하지 않은 활기를 더하기 좋은 음악들이에요'.\n"
        "Do not claim that music prevents distraction, maintains concentration, or improves study efficiency. Use listening-context wording such as '현재 공부 흐름을 이어가면서 듣기 좋아요' or '강한 자극보다 일정한 분위기로 이어 듣고 싶을 때 어울려요'.\n"
        "When user_text contains a concrete life context such as job searching, an interview, a breakup, or exhaustion, name that context naturally in message.\n"
        "For job-search anxiety, acknowledge the pressure or uncertainty of the job search and focus on settling the mind or regaining a steady pace.\n"
        "Do not describe anxiety as needing speed, driving rhythm, or productivity unless the user explicitly asks for focus, work tempo, or energy.\n"
        "Do not repeat the literal label '원하는 분위기' in the output.\n"
        "Do not quote user_text verbatim or wrap it in quotation marks.\n"
        "Paraphrase the user's intent instead of copying the exact sentence.\n"
        "track_reasons should be an array with the same length as the tracks list.\n"
        "Each track_reason item must be an object with track_id, reason, and used_fact_keys.\n"
        "Each reason should usually be 2 natural Korean sentences, specific to the track, and should reflect the user's text. Aim for 2-3 readable lines, not a strict character count.\n"
        "music_feature is an application-normalized phrase based only on verified metadata. Use it as the musical feature instead of listing individual tags.\n"
        "For every track, connect music_feature to a listening context in the first sentence, then naturally connect that context to the role's situation_angle in the second sentence.\n"
        "Use a different recommendation_role for each track, but never expose its focus label verbatim. The second sentences must not repeat and must use distinct role logic, not just synonyms for calming down.\n"
        "Preserve Korean particles and connectors: do not write compressed fragments such as '숨 고르기 어울려요', '정리하기 잘 맞아요', or '시간 만들기 좋아요'.\n"
        "recommendation_role is internal planning data only. Convert it into natural spoken Korean instead of inserting it literally: '생각의 속도 늦추기' becomes '생각의 속도를 조금 늦추고 싶을 때', and '잠시 숨 고르기' becomes '잠시 숨을 고르고 싶을 때'.\n"
        "Before returning, rewrite any phrase matching '[verb]+하기/기 + 좋아요/잘 맞아요/어울려요/적당해요/적합해요/필요할 때'. '듣기 좋아요' is the only allowed exception.\n"
        "Do not use generic listening fillers such as '음악을 들으며', '음악에 집중하며', or '감상을 즐기며'. Keep the first sentence about the verified feature and the second about the user's specific situation.\n"
        "Do not end reasons with '적절해요', '알맞아요', '괜찮아요', or '적합해요'. Do not invent role paraphrases such as '감상하기', '귀 기울이기', or '곱씹어 보기'.\n"
        "Also avoid '듣기 알맞습니다', '적당합니다', '집중의 끈을 단단히 붙잡다', '경쾌한 에너지와 높은 에너지', and '활기찬 분위기를 채워준다'.\n"
        "Never encourage dwelling on negative thoughts: avoid '걱정을 곱씹다', '불안을 곱씹다', '고민에 잠기다', and '걱정에 머물다'. Prefer '생각에서 잠시 거리를 두다', '감정을 천천히 정리하다', '긴장을 내려놓다', or '잠시 쉬어가다'.\n"
        "Describe musical features in natural Korean. Avoid data-description phrases such as '~로 이루어져 있어', '~을 지녀', or '~가 담겨 있어'. Prefer forms such as '~한 분위기가 자연스럽게 이어져요'.\n"
        "Avoid abstract AI-style phrases such as '분위기의 결', '편안한 결', '감성의 결', '온도를 낮추다', '느낌을 채워주다', '분위기가 머물다', or '감정을 품다'. Use plain everyday Korean instead.\n"
        "Before returning each reason, remove nearby repeated descriptors with the same root. For example, do not use '부드럽고 ... 부드러운' or '차분한 ... 차분하게' in one sentence.\n"
        "Also avoid repeating '듣기 좋', '조용', '차분', '편안', '조급', or '초조' across the two sentences of one reason.\n"
        "Do not use two '~때' clauses in one sentence. Combine them naturally, for example: '결과에 대한 생각이 계속 머릿속을 맴돌 때, 잠시 생각의 속도를 늦추며 듣기 좋아요.'\n"
        "Do not connect a purpose infinitive to an evaluation as in '~하기 위해 듣기 좋아요'. Write '잠시 긴장을 내려놓으며 듣기 좋아요' or '~고 싶을 때 잘 어울려요' instead.\n"
        "When using verbs such as '정리하며' or '가라앉히며', name what is being handled. For example, write '복잡한 마음을 천천히 정리하며 듣기 좋습니다', not just '차분히 정리하며 듣기 좋습니다'.\n"
        "Do not state that music resolves or gives comfort to the user, such as '위로를 받을 수 있어요'. Prefer a listening context like '조용히 쉬어가고 싶은 순간에 잘 어울려요'.\n"
        "The first sentence must be different for every track. Use each track's supplied music_feature rather than copying another track's opening.\n"
        "Before returning, compare the two sentences and remove a repeated core idea. For example, if the first sentence says the study flow should not change, the second must not repeat that same study-flow idea; use a distinct role such as a light refresh instead.\n"
        "Do not use abstract or mechanical phrases such as '에너지가 채워지는 느낌', '~할 때 적당해요', '~하기 알맞아요', or '분위기가 다가와요'.\n"
        "Also avoid '에너지가 분위기를 채워준다', '템포를 살려준다', '에너지가 조화롭게 흘러간다', '분위기를 조화롭게 만든다', and '~할 때 유용하다'. Use direct everyday Korean such as '밝고 경쾌한 분위기가 가볍게 이어지는 곡이에요' or '~하고 싶을 때 잘 어울려요'.\n"
        "Avoid generic reasons that could fit every song. State one supplied music_feature in the first sentence and connect it to the track's distinct recommendation_role in the second, without inventing music details.\n"
        "Do not say '머릿속의 결과'; say '결과에 대한 생각'. Do not say '편안하게 머물며 듣기'; prefer '부담 없이 듣기' or '편안하게 이어 듣기'.\n"
        "Do not use redundant phrases such as '진행되는 전개' or '이어지는 흐름'.\n"
        "Never add arrangement, progression, vocals, rhythm, instruments, lyrics, BPM, or production details unless they appear in verified_reason_facts. With only soft/warm-style metadata, describe only the supplied atmosphere naturally.\n"
        "Keep a natural sentence even if another track uses a similar safe expression; do not force awkward variation.\n"
        "The message is a recommendation summary, not an instruction. Do not tell the user to do something with endings like '보세요', '쉬어가세요', or '들어보세요'. Say that the service selected songs instead.\n"
        "In the summary, do not use overlapping anxiety words such as '초조' and '조급' together; choose one clear expression.\n"
        "Use only verified_reason_facts as factual grounding for musical claims.\n"
        "used_fact_keys must list the verified_reason_facts keys used in that reason, using only sound_profile, listening_effect, tags, or moods.\n"
        "Every reason must have exactly two sentences: (1) a verified musical feature, then (2) its listening benefit connected to the user's situation.\n"
        "If music_feature is missing, do not invent a musical feature. Keep that item's reason empty and used_fact_keys empty so the application can use its safe fallback template.\n"
        "Never expose internal metadata words such as tag, seed, seed genre, selection seed, or service classification.\n"
        "Never write raw internal English labels such as dreamy, soft, warm, calm, emotional, comfort, driving, or high_energy; translate their meaning into natural Korean.\n"
        "Do not promise emotional or psychological outcomes. Avoid phrases equivalent to 'removes anxiety', 'solves worries', 'heals', 'helps', 'loosens tension', 'brings relief', or 'leads the mind'.\n"
        "Use listening-context wording instead, such as '듣기 좋아요', '잠시 쉬어가고 싶을 때 어울려요', or '생각의 속도를 늦추고 싶을 때 잘 맞아요'.\n"
        "Do not invent poetic imagery or personal outcomes not present in verified_reason_facts, including a comforting hug, a bright future, or deep relief.\n"
        "Do not invent exact instruments, lyrics, song sections, production facts, album facts, BPM, or music theory details.\n"
        "Do not use playlist position, artist name alone, or abstract phrases such as '곡의 결', '흐름의 온도', '버퍼 역할', or '부담을 키우지 않는다' as evidence.\n"
        "Make every track_reason noticeably different.\n"
        "Use a different angle for each track when possible, such as melody, rhythm, vocal texture, arrangement, emotional role, or transition.\n"
        "Do not reuse the same opening or closing sentence pattern for multiple tracks.\n"
        "Do not use the track name or artist name as a sentence subject. The UI already displays them, and this avoids incorrect Korean particles after English titles.\n"
        "Avoid repeating the same sentence pattern across tracks.\n"
        "Avoid saying that you are an AI.\n"
    )
    user_payload = {
        "selected_mood": mood,
        "user_text": context_text or "",
        "selected_vibes": selected_vibes or [],
        "listening_request_context": _build_listening_request_context(context_text, selected_vibes),
        "retrieved_guidance": rag_guidance or {},
        "tracks": track_lines,
    }
    response = _gemini_post(
        "/chat/completions",
        {
            "model": settings.gemini_copy_model,
            "temperature": 0.3,
            "response_format": {
                "type": "json_schema",
                "json_schema": _recommendation_copy_schema(),
            },
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            # Leave enough room for six structured reasons and closing braces.
            # The prompt also caps each field so this does not inflate latency.
            "max_tokens": 1800,
        },
    )
    data = _parse_json_content(_extract_message_content(response))
    if not data:
        content = _extract_message_content(response)
        preview = " ".join(content.split())[:500] if content else "<empty content>"
        raise GeminiServiceError(f"Gemini returned invalid JSON: {preview}")

    message = str(data.get("message") or "").strip()
    reasons = data.get("track_reasons") or []
    if not isinstance(reasons, list):
        reasons = []

    normalized_reasons: list[dict[str, str]] = []
    for item in reasons:
        if not isinstance(item, dict):
            continue
        track_id = str(item.get("track_id") or "").strip()
        reason = str(item.get("reason") or "").strip()
        used_fact_keys = item.get("used_fact_keys") or []
        if not isinstance(used_fact_keys, list):
            used_fact_keys = []
        valid_fact_keys = {"sound_profile", "listening_effect", "tags", "moods"}
        used_fact_keys = [str(key) for key in used_fact_keys if str(key) in valid_fact_keys]
        if track_id and reason and used_fact_keys:
            normalized_reasons.append({"track_id": track_id, "reason": reason, "used_fact_keys": used_fact_keys})

    if not message and not normalized_reasons:
        raise GeminiServiceError("Gemini JSON did not contain a message or usable track_reasons")

    return {
        "message": message or None,
        "track_reasons": normalized_reasons,
    }


def generate_track_selection_profile(
    mood: str,
    context_text: str | None,
    rag_guidance: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not is_gemini_configured():
        return None

    prompt = (
        "You help select search hints for a mood-based Spotify recommender.\n"
        "Return only JSON with keys seed_genres, candidate_tracks, and search_terms.\n"
        "seed_genres should be a compact list of Spotify seed genres.\n"
        "candidate_tracks should be a list of objects with name, artist_name, and optional reason_hint.\n"
        "search_terms should be a list of short search queries, artist names, or song titles.\n"
        "Use retrieved_guidance as a constraint, not as a source of genres, artists, or song titles.\n"
        "Never suggest candidates that conflict with its avoid_tags or selection_rules unless the user explicitly requested that genre.\n"
        "Keep the result specific, practical, and not repetitive.\n"
        "Do not output any markdown.\n"
    )
    user_payload = {
        "selected_mood": mood,
        "context_text": context_text or "",
        "retrieved_guidance": rag_guidance or {},
    }
    response = _gemini_post(
        "/chat/completions",
        {
            "model": settings.gemini_model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "max_tokens": 900,
        },
    )
    data = _parse_json_content(_extract_message_content(response))
    if not data:
        return None

    seed_genres = data.get("seed_genres") or []
    candidate_tracks = data.get("candidate_tracks") or []
    search_terms = data.get("search_terms") or []

    normalized_candidates: list[dict[str, str]] = []
    if isinstance(candidate_tracks, list):
        for item in candidate_tracks:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            artist_name = str(item.get("artist_name") or "").strip()
            reason_hint = str(item.get("reason_hint") or "").strip()
            if name and artist_name:
                normalized_candidates.append(
                    {
                        "name": name,
                        "artist_name": artist_name,
                        "reason_hint": reason_hint,
                    }
                )

    normalized_seed_genres = [str(item).strip() for item in seed_genres if str(item).strip()] if isinstance(seed_genres, list) else []
    normalized_search_terms = [str(item).strip() for item in search_terms if str(item).strip()] if isinstance(search_terms, list) else []

    if not normalized_candidates and not normalized_seed_genres and not normalized_search_terms:
        return None

    return {
        "seed_genres": normalized_seed_genres,
        "candidate_tracks": normalized_candidates,
        "search_terms": normalized_search_terms,
    }
