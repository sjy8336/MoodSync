"""Soft aesthetic presets for explicit MBTI wording in music requests.

These are product vocabulary defaults, not claims about personality or music taste.
They must never override the user's stated mood, activity, or hard constraints.
"""

from __future__ import annotations

import re
from typing import Any


MBTI_AESTHETIC_PRESETS: dict[str, dict[str, Any]] = {
    "INFP": {"tags": ["dreamy", "sentimental", "introspective", "warm", "soft", "atmospheric", "wistful", "late-night"], "weights": {"energy": 0.35, "emotionality": 0.9, "introspection": 0.9, "dreaminess": 0.9, "warmth": 0.7, "nostalgia": 0.7, "social_affinity": 0.25}},
    "INFJ": {"tags": ["atmospheric", "calm", "emotional", "cinematic", "introspective", "deep", "mysterious", "reflective"], "weights": {"energy": 0.35, "emotionality": 0.8, "introspection": 0.85, "cinematic": 0.7, "darkness": 0.55}},
    "INTP": {"tags": ["minimal", "atmospheric", "experimental", "calm", "detached", "futuristic", "cerebral", "late-night"], "weights": {"energy": 0.4, "introspection": 0.75, "novelty": 0.8, "minimalism": 0.85, "darkness": 0.45}},
    "INTJ": {"tags": ["dark", "focused", "cinematic", "sophisticated", "minimal", "intense", "atmospheric", "controlled"], "weights": {"energy": 0.55, "intensity": 0.7, "minimalism": 0.7, "cinematic": 0.75, "darkness": 0.7}},
    "ISFP": {"tags": ["emotional", "aesthetic", "soft", "dreamy", "warm", "sensual", "mellow", "intimate"], "weights": {"energy": 0.4, "emotionality": 0.85, "dreaminess": 0.75, "warmth": 0.75, "social_affinity": 0.35}},
    "ISFJ": {"tags": ["warm", "comforting", "nostalgic", "gentle", "familiar", "soft", "sentimental", "peaceful"], "weights": {"energy": 0.35, "warmth": 0.9, "nostalgia": 0.75, "emotionality": 0.65, "familiarity": 0.7}},
    "ISTP": {"tags": ["cool", "minimal", "rhythmic", "dark", "laid-back", "urban", "controlled", "sleek"], "weights": {"energy": 0.55, "minimalism": 0.75, "darkness": 0.6, "intensity": 0.55, "social_affinity": 0.35}},
    "ISTJ": {"tags": ["calm", "familiar", "steady", "classic", "clean", "restrained", "comfortable", "structured"], "weights": {"energy": 0.4, "familiarity": 0.8, "minimalism": 0.6, "intensity": 0.35, "warmth": 0.55}},
    "ENFP": {"tags": ["bright", "playful", "uplifting", "emotional", "adventurous", "energetic", "colorful", "refreshing"], "weights": {"energy": 0.8, "brightness": 0.9, "emotionality": 0.65, "novelty": 0.75, "social_affinity": 0.85}},
    "ENFJ": {"tags": ["uplifting", "warm", "emotional", "cinematic", "hopeful", "energetic", "communal", "inspiring"], "weights": {"energy": 0.7, "warmth": 0.8, "emotionality": 0.7, "cinematic": 0.65, "social_affinity": 0.9}},
    "ENTP": {"tags": ["energetic", "playful", "quirky", "experimental", "bold", "dynamic", "witty", "unpredictable"], "weights": {"energy": 0.78, "novelty": 0.9, "playfulness": 0.85, "intensity": 0.65, "social_affinity": 0.8}},
    "ENTJ": {"tags": ["powerful", "confident", "energetic", "intense", "polished", "driving", "bold", "motivational"], "weights": {"energy": 0.82, "intensity": 0.8, "brightness": 0.55, "social_affinity": 0.65}},
    "ESFP": {"tags": ["energetic", "fun", "danceable", "bright", "glamorous", "rhythmic", "exciting", "social"], "weights": {"energy": 0.9, "brightness": 0.85, "danceability": 0.9, "social_affinity": 0.95, "introspection": 0.25}},
    "ESFJ": {"tags": ["bright", "warm", "familiar", "upbeat", "romantic", "social", "cheerful", "accessible"], "weights": {"energy": 0.7, "warmth": 0.75, "familiarity": 0.8, "social_affinity": 0.9, "brightness": 0.8}},
    "ESTP": {"tags": ["high-energy", "bold", "rhythmic", "exciting", "confident", "dynamic", "sporty", "party-oriented"], "weights": {"energy": 0.92, "intensity": 0.8, "danceability": 0.75, "social_affinity": 0.85, "novelty": 0.6}},
    "ESTJ": {"tags": ["energetic", "confident", "structured", "driving", "bold", "familiar", "upbeat", "straightforward"], "weights": {"energy": 0.78, "intensity": 0.7, "familiarity": 0.65, "social_affinity": 0.65, "minimalism": 0.45}},
}

MBTI_ALIASES = {
    "인프피": "INFP", "인프제": "INFJ", "인팁": "INTP", "인티제": "INTJ",
    "잇프피": "ISFP", "잇프제": "ISFJ", "잇팁": "ISTP", "잇티제": "ISTJ",
    "엔프피": "ENFP", "엔프제": "ENFJ", "엔팁": "ENTP", "엔티제": "ENTJ",
    "엣프피": "ESFP", "엣프제": "ESFJ", "엣팁": "ESTP", "엣티제": "ESTJ",
}

_RANKING_TAGS = {
    "dreamy": "dreamy", "sentimental": "emotional", "emotional": "emotional", "warm": "warm", "soft": "soft",
    "calm": "calm", "late-night": "calm", "minimal": "calm", "atmospheric": "dreamy",
    "energetic": "high_energy", "high-energy": "high_energy", "bright": "upbeat", "uplifting": "upbeat",
    "playful": "upbeat", "danceable": "upbeat", "rhythmic": "driving", "driving": "driving",
}


def detect_mbti_aesthetic(text: str | None) -> dict[str, Any] | None:
    """Return a preset only when the user explicitly writes an MBTI expression."""
    if not isinstance(text, str) or not text.strip():
        return None

    normalized = text.upper()
    match = re.search(r"(?<![A-Z])([EI][NS][FT][PJ])(?![A-Z])", normalized)
    mbti = match.group(1) if match else next((value for alias, value in MBTI_ALIASES.items() if alias in text), None)
    if not mbti:
        return None

    preset = MBTI_AESTHETIC_PRESETS[mbti]
    semantic_tags = list(preset["tags"])
    ranking_tags = list(dict.fromkeys(_RANKING_TAGS[tag] for tag in semantic_tags if tag in _RANKING_TAGS))
    return {"mbti": mbti, "semantic_tags": semantic_tags, "ranking_tags": ranking_tags, "weights": dict(preset["weights"])}
