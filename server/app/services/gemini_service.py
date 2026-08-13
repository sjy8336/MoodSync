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
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        raise GeminiServiceError(f"Gemini request failed: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise GeminiServiceError(f"Gemini request failed: {exc.reason}") from exc


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
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
    return None


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
) -> dict[str, Any] | None:
    if not is_gemini_configured() or not tracks:
        return None

    track_lines = []
    for track in tracks:
        track_lines.append(
            {
                "track_id": str(track.get("track_id") or ""),
                "name": str(track.get("name") or ""),
                "artist_name": str(track.get("artist_name") or ""),
                "album_name": str(track.get("album_name") or ""),
                "reason_hint": str(track.get("reason") or ""),
            }
        )

    prompt = (
        "You write empathetic Korean copy for a mood-based music app.\n"
        "Return only JSON with keys message and track_reasons.\n"
        "message should be 2-3 natural Korean sentences, warm and specific, not generic.\n"
        "The user_text field is only the user's direct free text. selected_vibes is a separate list of chosen vibe tags.\n"
        "Do not repeat the literal label '원하는 분위기' in the output.\n"
        "Do not quote user_text verbatim or wrap it in quotation marks.\n"
        "Paraphrase the user's intent instead of copying the exact sentence.\n"
        "track_reasons should be an array with the same length as the tracks list.\n"
        "Each track_reason item must be an object with track_id and reason.\n"
        "Each reason should be 1-2 Korean sentences, specific to the track, and should reflect the user's text.\n"
        "Use the supplied reason_hint as factual grounding when it is useful.\n"
        "Do not invent exact instruments, lyrics, song sections, production facts, or album facts that are not supplied.\n"
        "A useful reason must connect one observable musical point (rhythm, vocal presence, arrangement, energy, or supplied hint) to a listening benefit.\n"
        "Make every track_reason noticeably different.\n"
        "Use a different angle for each track when possible, such as melody, rhythm, vocal texture, arrangement, emotional role, or transition.\n"
        "Do not reuse the same opening or closing sentence pattern for multiple tracks.\n"
        "Mention one concrete detail from the track name, artist name, or album name when possible.\n"
        "Avoid repeating the same sentence pattern across tracks.\n"
        "Avoid saying that you are an AI.\n"
    )
    user_payload = {
        "selected_mood": mood,
        "user_text": context_text or "",
        "selected_vibes": selected_vibes or [],
        "tracks": track_lines,
    }
    response = _gemini_post(
        "/chat/completions",
        {
            "model": settings.gemini_model,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "max_tokens": 800,
        },
    )
    data = _parse_json_content(_extract_message_content(response))
    if not data:
        return None

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
        if track_id and reason:
            normalized_reasons.append({"track_id": track_id, "reason": reason})

    if not message and not normalized_reasons:
        return None

    return {
        "message": message or None,
        "track_reasons": normalized_reasons,
    }


def generate_track_selection_profile(
    mood: str,
    context_text: str | None,
) -> dict[str, Any] | None:
    if not is_gemini_configured():
        return None

    prompt = (
        "You help select search hints for a mood-based Spotify recommender.\n"
        "Return only JSON with keys seed_genres, candidate_tracks, and search_terms.\n"
        "seed_genres should be a compact list of Spotify seed genres.\n"
        "candidate_tracks should be a list of objects with name, artist_name, and optional reason_hint.\n"
        "search_terms should be a list of short search queries, artist names, or song titles.\n"
        "Prefer hints that fit the user's mood, favorites, recent listening style, and the retrieved recommendation guidance.\n"
        "Keep the result specific, practical, and not repetitive.\n"
        "Do not output any markdown.\n"
    )
    user_payload = {
        "selected_mood": mood,
        "context_text": context_text or "",
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
