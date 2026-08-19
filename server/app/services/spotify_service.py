from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.schemas.track import TrackSummary


SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_AVAILABLE_GENRES_URL = f"{SPOTIFY_API_BASE}/recommendations/available-genre-seeds"
SPOTIFY_RECOMMENDATIONS_URL = f"{SPOTIFY_API_BASE}/recommendations"
SPOTIFY_SEARCH_URL = f"{SPOTIFY_API_BASE}/search"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
VIBE_PATTERN = re.compile(r"\s*원하는\s*분위기\s*:\s*([^.]*)\.?\s*$")

_app_access_token: str | None = None
_app_access_token_expires_at = 0.0

# Spotify's track endpoint does not provide a reliable lyrics/vocals flag. These
# phrases therefore route the request to catalog tracks with verified metadata.
INSTRUMENTAL_REQUEST_TERMS = (
    "가사가 없는",
    "가사 없는",
    "가사없이",
    "가사 없이",
    "무가사",
    "연주곡",
    "보컬 없는",
    "보컬이 없는",
    "instrumental only",
    "instrumental",
)
SLEEP_REQUEST_TERMS = ("수면", "잠들", "잠을", "잠 못", "잠자", "자고 싶", "잘 때")

GENRE_FAMILY_HINTS: list[tuple[tuple[str, ...], str, list[str], dict[str, object]]] = [
    (("rnb", "r&b", "알앤비"), "R&B", ["r&b", "r-n-b", "soul", "neo-soul"], {"target_valence": 0.5, "target_energy": 0.58}),
    (("neo soul", "neo-soul", "네오소울"), "네오소울", ["neo-soul", "r&b", "soul"], {"target_valence": 0.52, "target_energy": 0.46}),
    (("soul", "소울", "gospel", "가스펠"), "소울", ["soul", "gospel", "r&b"], {"target_valence": 0.54, "target_energy": 0.5}),
    (("funk", "펑키", "groove", "groovy"), "펑키", ["funk", "disco", "dance"], {"target_energy": 0.76, "target_danceability": 0.82}),
    (("disco", "디스코"), "디스코", ["disco", "funk", "dance"], {"target_energy": 0.8, "target_danceability": 0.86}),
    (("punk rock", "펑크락", "펑크"), "펑크락", ["punk", "rock", "alternative", "hard-rock"], {"target_energy": 0.88, "target_danceability": 0.7}),
    (("rock", "록 음악", "록밴드", "락"), "록", ["rock", "alternative", "punk", "hard-rock"], {"target_energy": 0.82, "target_danceability": 0.58}),
    (("indie pop", "indie-pop", "인디팝"), "인디팝", ["indie", "pop", "alternative"], {"target_energy": 0.46, "target_acousticness": 0.46}),
    (("folk", "포크", "americana", "아메리카나", "bluegrass", "블루그래스"), "포크", ["folk", "acoustic", "americana"], {"target_energy": 0.28, "target_acousticness": 0.84}),
    (("hip hop", "hip-hop", "힙합", "랩", "rap", "trap"), "힙합", ["hip-hop", "rap", "trap", "chill"], {"target_energy": 0.74, "target_danceability": 0.72}),
    (("trip hop", "trip-hop", "트립합", "downtempo", "다운템포"), "트립합", ["trip-hop", "downtempo", "chill"], {"target_energy": 0.36, "target_acousticness": 0.54}),
    (("drum and bass", "dnb", "d&b", "드럼앤베이스"), "드럼앤베이스", ["drum-and-bass", "electronic", "dance"], {"target_energy": 0.9, "target_danceability": 0.74}),
    (("j-pop", "jpop", "제이팝", "japanese pop", "일본 팝"), "제이팝", ["j-pop", "japanese pop", "pop"], {"target_energy": 0.68, "target_danceability": 0.68}),
    (("anime ost", "anime soundtrack", "anisong", "anison", "애니 ost", "애니오스트", "애니송", "애니메이션 ost"), "애니 OST", ["soundtrack", "j-pop", "anime", "japanese pop"], {"target_energy": 0.56, "target_acousticness": 0.46}),
    (("soundtrack", "ost", "오스트", "영화음악"), "사운드트랙", ["soundtrack", "score", "orchestral", "piano"], {"target_energy": 0.42, "target_acousticness": 0.62}),
    (("lofi", "lo-fi", "로파이", "로피", "study beats"), "로파이", ["lo-fi", "chill", "study", "ambient"], {"target_energy": 0.28, "target_acousticness": 0.72}),
    (("swing", "스윙", "big band", "빅밴드", "jazz standard", "standard", "스탠다드"), "스윙 재즈", ["jazz", "standard", "big-band", "swing"], {"target_energy": 0.56, "target_danceability": 0.52, "target_instrumentalness": 0.7}),
    (("bebop", "bop", "비밥", "hard bop", "하드밥", "post-bop", "포스트밥"), "비밥/하드밥", ["jazz", "bebop", "instrumental"], {"target_energy": 0.7, "target_danceability": 0.44, "target_instrumentalness": 0.76}),
    (("jazz", "재즈", "모던재즈", "modal jazz", "모달재즈", "cool jazz", "쿨재즈"), "모던 재즈", ["jazz", "piano", "study"], {"target_energy": 0.44, "target_acousticness": 0.72, "target_instrumentalness": 0.48}),
    (("jazz fusion", "fusion", "퓨전재즈"), "퓨전재즈", ["jazz", "fusion", "instrumental"], {"target_energy": 0.52, "target_instrumentalness": 0.7}),
    (("bossa nova", "보사노바", "bossanova"), "보사노바", ["bossa-nova", "latin", "acoustic"], {"target_energy": 0.34, "target_acousticness": 0.76}),
    (("latin", "라틴", "reggaeton", "레게톤"), "라틴", ["latin", "reggaeton", "dance"], {"target_energy": 0.76, "target_danceability": 0.88}),
    (("afrobeats", "afrobeat", "african", "아프로비트"), "아프로비트", ["afrobeat", "afrobeats", "dance"], {"target_energy": 0.8, "target_danceability": 0.82}),
    (("electronic", "edm", "일렉", "일렉트로닉"), "일렉트로닉", ["electronic", "dance", "house", "techno"], {"target_energy": 0.82, "target_danceability": 0.8}),
    (("house", "하우스"), "하우스", ["house", "dance", "electronic", "club"], {"target_energy": 0.84, "target_danceability": 0.84}),
    (("techno", "테크노"), "테크노", ["techno", "electronic", "dance"], {"target_energy": 0.86, "target_danceability": 0.76}),
    (("synthwave", "신스웨이브", "retrowave", "레트로웨이브"), "신스웨이브", ["synthwave", "electronic", "chill"], {"target_energy": 0.42, "target_acousticness": 0.24}),
    (("vaporwave", "베이퍼웨이브"), "베이퍼웨이브", ["vaporwave", "chill", "electronic"], {"target_energy": 0.22, "target_acousticness": 0.34}),
    (("drone", "드론", "ambient", "앰비언트"), "앰비언트", ["ambient", "chill", "instrumental"], {"target_energy": 0.18, "target_acousticness": 0.84}),
    (("indie", "인디", "alternative", "얼터너티브"), "인디", ["indie", "alternative", "folk"], {"target_energy": 0.42, "target_acousticness": 0.62}),
    (("k-indie", "k indie", "한국 인디", "국내 인디"), "한국 인디", ["k-indie", "indie", "alternative"], {"target_energy": 0.4, "target_acousticness": 0.58}),
    (("acoustic", "어쿠스틱"), "어쿠스틱", ["acoustic", "folk", "indie"], {"target_energy": 0.34, "target_acousticness": 0.82}),
    (("ballad", "발라드"), "발라드", ["acoustic", "piano", "sad"], {"target_energy": 0.24, "target_acousticness": 0.84}),
    (("classical", "클래식", "오케스트라", "오케스트랄", "orchestral"), "클래식", ["classical", "piano", "orchestral", "instrumental"], {"target_energy": 0.18, "target_acousticness": 0.92, "target_instrumentalness": 0.96}),
    (("opera", "오페라", "vocal classical"), "오페라", ["classical", "opera", "orchestral"], {"target_energy": 0.2, "target_acousticness": 0.88, "target_instrumentalness": 0.92}),
    (("ambient", "앰비언트", "드론"), "앰비언트", ["ambient", "chill", "instrumental"], {"target_energy": 0.18, "target_acousticness": 0.84}),
    (("shoegaze", "슈게이즈", "dream pop", "dream-pop", "드림팝"), "드림팝", ["shoegaze", "dream-pop", "indie", "ambient"], {"target_energy": 0.42, "target_acousticness": 0.58}),
    (("post-rock", "post rock", "포스트록"), "포스트록", ["post-rock", "ambient", "indie"], {"target_energy": 0.46, "target_acousticness": 0.7, "target_instrumentalness": 0.56}),
    (("metal", "메탈", "heavy metal", "하드록"), "메탈", ["metal", "hard-rock", "rock"], {"target_energy": 0.92, "target_danceability": 0.34}),
    (("metalcore", "메탈코어", "post-hardcore", "하드코어"), "메탈코어", ["metal", "hard-rock", "rock"], {"target_energy": 0.96, "target_danceability": 0.28}),
    (("country", "컨트리", "americana"), "컨트리", ["country", "folk", "acoustic"], {"target_energy": 0.32, "target_acousticness": 0.78}),
    (("blues", "블루스"), "블루스", ["blues", "jazz", "soul"], {"target_energy": 0.34, "target_acousticness": 0.66}),
    (("reggae", "레게", "댄스홀"), "레게", ["reggae", "dancehall", "dub"], {"target_energy": 0.58, "target_danceability": 0.72}),
    (("city pop", "시티팝", "시티 팝"), "시티팝", ["city-pop", "disco", "funk", "j-pop"], {"target_energy": 0.62, "target_danceability": 0.72}),
    (("k-pop", "kpop", "케이팝", "한국"), "케이팝", ["k-pop", "korean pop", "dance", "pop"], {"target_energy": 0.76, "target_danceability": 0.76}),
]

CONTEXT_GENRE_HINTS: list[tuple[str, list[str]]] = [
    ("솔로", ["acoustic", "soul", "r&b", "indie"]),
    ("혼자", ["acoustic", "soul", "r&b", "indie"]),
    ("외로", ["acoustic", "piano", "soul", "chill"]),
    ("잔잔", ["acoustic", "piano", "chill", "ambient"]),
    ("몽환", ["ambient", "electronic", "indie", "dream-pop"]),
    ("몰입", ["study", "ambient", "piano", "instrumental"]),
    ("위로", ["acoustic", "piano", "soul", "chill"]),
    ("세련", ["city-pop", "synthwave", "disco", "funk"]),
    ("밤공기", ["synthwave", "vaporwave", "city-pop", "lo-fi"]),
    ("여름", ["city-pop", "reggae", "latin", "afrobeats"]),
    ("새벽", ["ambient", "trip-hop", "downtempo", "lo-fi"]),
    ("드라이브", ["rock", "synthwave", "electronic", "pop"]),
    ("그루브", ["funk", "disco", "soul", "r&b"]),
    ("복고", ["city-pop", "synthwave", "vaporwave", "disco"]),
]

CONTEXT_TAG_HINTS: list[tuple[str, list[str]]] = [
    ("강렬", ["high_energy", "driving", "focused"]),
    ("신나", ["high_energy", "upbeat", "driving"]),
    ("몰입", ["focused", "driving", "rhythmic"]),
    ("집중", ["focused", "driving"]),
    ("빠르게", ["driving", "rhythmic"]),
    ("빨리", ["driving", "rhythmic"]),
    ("작업", ["focused", "driving"]),
    ("포트폴리오", ["focused", "driving"]),
    ("마감", ["focused", "driving"]),
    ("감성", ["emotional", "dreamy"]),
    ("잔잔", ["calm", "soft"]),
    ("몽환", ["dreamy", "ambient"]),
    ("외로", ["emotional", "soft"]),
    ("불안", ["tense", "focused"]),
]

CONTEXT_AUDIO_HINTS: list[tuple[str, dict[str, object]]] = [
    ("강렬", {"genres": ["electronic", "dance", "rock", "pop"], "params": {"target_energy": 0.88, "target_danceability": 0.72}}),
    ("신나", {"genres": ["dance", "pop", "party", "funk"], "params": {"target_energy": 0.9, "target_danceability": 0.82}}),
    ("세련", {"genres": ["city-pop", "disco", "funk", "soul"], "params": {"target_energy": 0.7, "target_danceability": 0.76}}),
    ("여름", {"genres": ["city-pop", "reggae", "latin", "afrobeats"], "params": {"target_energy": 0.74, "target_danceability": 0.8}}),
    ("밤공기", {"genres": ["vaporwave", "synthwave", "ambient", "lo-fi"], "params": {"target_energy": 0.3, "target_acousticness": 0.5}}),
    ("그루브", {"genres": ["funk", "disco", "soul", "r&b"], "params": {"target_energy": 0.68, "target_danceability": 0.78}}),
    ("복고", {"genres": ["city-pop", "synthwave", "vaporwave", "disco"], "params": {"target_energy": 0.58, "target_danceability": 0.68}}),
    ("몰입", {"genres": ["electronic", "study", "hip-hop", "indie"], "params": {"target_energy": 0.72, "target_danceability": 0.58}}),
    ("작업", {"genres": ["electronic", "study", "hip-hop", "pop"], "params": {"target_energy": 0.7, "target_danceability": 0.56}}),
    ("포트폴리오", {"genres": ["electronic", "study", "hip-hop", "pop"], "params": {"target_energy": 0.7, "target_danceability": 0.56}}),
    ("마감", {"genres": ["electronic", "study", "hip-hop", "pop"], "params": {"target_energy": 0.72, "target_danceability": 0.58}}),
    ("불안", {"genres": ["electronic", "hip-hop", "pop", "dance"], "params": {"target_energy": 0.72, "target_danceability": 0.64}}),
    ("드라이브", {"genres": ["rock", "synthwave", "electronic", "pop"], "params": {"target_energy": 0.84, "target_danceability": 0.7}}),
]

# 자주 쓰는 큐레이션 곡은 실제로 들었을 때 포착되는 특징을 별도 힌트로 둔다.
# 추천 이유가 순번만 바꾼 템플릿으로 떨어지는 것을 막고, 확인할 수 없는 세부 묘사는 피한다.
TRACK_SOUND_HINTS: dict[tuple[str, str], tuple[str, str]] = {
    ("luv (sic.) pt3", "nujabes"): (
        "여유 있는 힙합 비트 위로 재즈 감각의 건반과 절제된 랩이 차분하게 이어져요",
        "박자가 과하게 튀지 않아 해야 할 일의 리듬을 유지하는 배경음으로 잘 맞아요",
    ),
    ("brave shine", "aimer"): (
        "Aimer의 낮고 결 있는 보컬이 밴드 사운드가 커지는 구간과 대비를 만들어요",
        "에너지를 끌어올리되 보컬의 중심이 분명해서 흐트러진 집중을 다시 모으는 데 좋아요",
    ),
    ("feel it still", "portugal. the man"): (
        "짧고 또렷한 베이스 리프와 경쾌한 드럼 패턴이 곡을 가볍게 밀고 가요",
        "무겁지 않은 추진력이 필요할 때 작업 템포를 환기하기 좋습니다",
    ),
    ("blinding lights", "the weeknd"): (
        "선명한 신스 베이스와 일정하게 달리는 드럼이 레트로 팝의 속도감을 만들어요",
        "반복적인 추진력이 산만함을 줄이고 한 가지 흐름에 붙어 있게 도와줘요",
    ),
    ("humble.", "kendrick lamar"): (
        "짧게 반복되는 피아노 리프와 단단한 비트 위에 랩의 억양이 또렷하게 올라와요",
        "강한 박자 기준점이 필요할 때 에너지를 한곳으로 모으는 선택이에요",
    ),
    ("into the night", "yoasobi"): (
        "피아노가 이끄는 빠른 전개와 선명한 보컬이 촘촘하게 맞물려요",
        "속도감은 있지만 멜로디가 분명해서 긴 작업 시간에도 흐름을 잃지 않기 좋아요",
    ),
}


def _canonical_track_token(value: str) -> str:
    """Normalize Spotify display names before matching them to curated metadata."""
    cleaned = re.sub(r"\s*[\[(].*?[\])]\s*", " ", value.lower())
    cleaned = re.sub(r"\s+(?:feat\.?|ft\.?|featuring)\s+.*$", "", cleaned)
    return " ".join(cleaned.split())


TRACK_METADATA_ALIASES: dict[tuple[str, str], tuple[str, str]] = {
    ("sleepless in seoul", "ph-1"): ("sleepless in ______", "ph-1"),
}


def _catalog_metadata_for_track(name: str, artist_name: str) -> dict[str, object]:
    normalized_name = _canonical_track_token(name)
    normalized_artist = _canonical_track_token(artist_name)
    normalized_name, normalized_artist = TRACK_METADATA_ALIASES.get(
        (normalized_name, normalized_artist),
        (normalized_name, normalized_artist),
    )
    for candidate in FALLBACK_LIBRARY:
        if (
            _canonical_track_token(str(candidate.get("name") or "")) == normalized_name
            and _canonical_track_token(str(candidate.get("artist_name") or "")) == normalized_artist
        ):
            return {
                "tags": list(candidate.get("tags") or []),
                "moods": list(candidate.get("moods") or []),
            }
    return {}


def extract_hard_constraints(context_text: str | None) -> dict[str, bool]:
    """Return only requirements that must be enforced before ranking tracks."""
    lowered = (context_text or "").lower()
    return {"instrumental_required": any(term in lowered for term in INSTRUMENTAL_REQUEST_TERMS)}


def _is_sleep_request(context_text: str | None) -> bool:
    lowered = (context_text or "").lower()
    return any(term in lowered for term in SLEEP_REQUEST_TERMS)


def is_verified_instrumental(track: TrackSummary) -> bool:
    facts = track.reason_facts or {}
    tags = facts.get("tags") if isinstance(facts, dict) else []
    return isinstance(tags, list) and "instrumental" in {str(tag).lower() for tag in tags}


def validate_hard_constraints(
    tracks: list[TrackSummary],
    context_text: str | None,
) -> list[TrackSummary]:
    """Discard unknown candidates rather than guessing that they meet a hard request."""
    constraints = extract_hard_constraints(context_text)
    if constraints["instrumental_required"]:
        return [track for track in tracks if is_verified_instrumental(track)]
    return tracks


def _build_reason_facts(name: str, artist_name: str, seed_genres: list[str] | None = None) -> dict[str, object]:
    facts = _catalog_metadata_for_track(name, artist_name)
    sound_hint = TRACK_SOUND_HINTS.get((name.strip().lower(), artist_name.strip().lower()))
    if sound_hint:
        facts["sound_profile"] = sound_hint[0]
        facts["listening_effect"] = sound_hint[1]
    if seed_genres:
        facts["selection_seed_genres"] = list(seed_genres)
    return facts


MOOD_PROFILES: dict[str, dict[str, object]] = {
    "happy": {
        "genres": ["pop", "dance", "party", "funk"],
        "params": {"target_valence": 0.9, "target_energy": 0.82, "target_danceability": 0.82},
        "label": "기쁨",
    },
    "excited": {
        "genres": ["dance", "party", "electronic", "pop"],
        "params": {"target_valence": 0.88, "target_energy": 0.92, "target_danceability": 0.88, "target_tempo": 124},
        "label": "설렘",
    },
    "sad": {
        "genres": ["acoustic", "piano", "indie", "sad"],
        "params": {"target_valence": 0.22, "target_energy": 0.28, "target_acousticness": 0.76},
        "label": "우울",
    },
    "lonely": {
        "genres": ["acoustic", "indie", "folk", "sad"],
        "params": {"target_valence": 0.26, "target_energy": 0.3, "target_acousticness": 0.7},
        "label": "외로움",
    },
    "tired": {
        "genres": ["chill", "acoustic", "ambient", "piano"],
        "params": {"target_valence": 0.34, "target_energy": 0.18, "target_acousticness": 0.82},
        "label": "피로",
    },
    "angry": {
        "genres": ["rock", "metal", "punk", "hard-rock"],
        "params": {"target_valence": 0.28, "target_energy": 0.9, "target_danceability": 0.42},
        "label": "분노",
    },
    "anxious": {
        "genres": ["chill", "acoustic", "ambient", "piano"],
        "params": {"target_valence": 0.35, "target_energy": 0.24, "target_acousticness": 0.78},
        "label": "불안",
    },
    "focused": {
        "genres": ["jazz", "study", "piano", "classical", "ambient"],
        "params": {"target_energy": 0.42, "target_acousticness": 0.7, "target_instrumentalness": 0.58},
        "label": "집중",
    },
    "calm": {
        "genres": ["chill", "acoustic", "ambient", "piano"],
        "params": {"target_valence": 0.46, "target_energy": 0.34, "target_acousticness": 0.76},
        "label": "차분함",
    },
}

MOOD_ALIASES = {
    "기쁨": "happy",
    "설렘": "excited",
    "우울": "sad",
    "외로움": "lonely",
    "피로": "tired",
    "분노": "angry",
    "불안": "anxious",
    "집중": "focused",
    "차분함": "calm",
}

FALLBACK_LIBRARY: list[dict[str, object]] = [
    {"name": "Blinding Lights", "artist_name": "The Weeknd", "moods": ["anxious", "excited", "focused", "happy"], "tags": ["driving", "high_energy"]},
    {"name": "Don't Start Now", "artist_name": "Dua Lipa", "moods": ["anxious", "excited", "happy"], "tags": ["upbeat", "high_energy"]},
    {"name": "Levitating", "artist_name": "Dua Lipa", "moods": ["excited", "happy"], "tags": ["upbeat", "dance"]},
    {"name": "HUMBLE.", "artist_name": "Kendrick Lamar", "moods": ["anxious", "angry", "focused"], "tags": ["driving", "rhythmic"]},
    {"name": "Lose Yourself", "artist_name": "Eminem", "moods": ["anxious", "focused", "angry"], "tags": ["driving", "focused"]},
    {"name": "Bad Habit", "artist_name": "Steve Lacy", "moods": ["lonely", "sad", "focused"], "tags": ["rnb", "groove"]},
    {"name": "Luv (sic) Part 3", "artist_name": "Nujabes", "moods": ["lonely", "sad", "focused"], "tags": ["emotional", "hip-hop"]},
    {"name": "Take Five", "artist_name": "The Dave Brubeck Quartet", "moods": ["focused", "calm"], "tags": ["jazz", "instrumental", "standard"]},
    {"name": "So What", "artist_name": "Miles Davis", "moods": ["focused", "calm"], "tags": ["jazz", "instrumental", "standard"]},
    {"name": "Blue in Green", "artist_name": "Miles Davis", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "instrumental", "standard"]},
    {"name": "Autumn Leaves", "artist_name": "Chet Baker", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "vocal-jazz", "standard"]},
    {"name": "My Favorite Things", "artist_name": "John Coltrane", "moods": ["focused", "calm"], "tags": ["jazz", "instrumental", "standard"]},
    {"name": "Round Midnight", "artist_name": "Thelonious Monk", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "instrumental", "standard"]},
    {"name": "Sing, Sing, Sing", "artist_name": "Benny Goodman", "moods": ["excited", "focused", "happy"], "tags": ["jazz", "swing", "big-band", "instrumental"]},
    {"name": "Take the A Train", "artist_name": "Duke Ellington", "moods": ["happy", "focused", "calm"], "tags": ["jazz", "swing", "standard", "big-band"]},
    {"name": "It Don't Mean a Thing", "artist_name": "Duke Ellington", "moods": ["happy", "excited", "focused"], "tags": ["jazz", "swing", "standard", "big-band"]},
    {"name": "Donna Lee", "artist_name": "Charlie Parker", "moods": ["focused", "excited", "angry"], "tags": ["jazz", "bebop", "instrumental"]},
    {"name": "Moanin'", "artist_name": "Art Blakey & The Jazz Messengers", "moods": ["focused", "calm"], "tags": ["jazz", "hard-bop", "instrumental"]},
    {"name": "Blue Bossa", "artist_name": "Joe Henderson", "moods": ["calm", "focused", "sad"], "tags": ["jazz", "bossa-nova", "latin", "instrumental"]},
    {"name": "The Girl from Ipanema", "artist_name": "Stan Getz & João Gilberto", "moods": ["calm", "happy", "focused"], "tags": ["bossa-nova", "latin", "acoustic", "vocal-jazz"]},
    {"name": "Birdland", "artist_name": "Weather Report", "moods": ["excited", "focused", "happy"], "tags": ["jazz", "fusion", "instrumental"]},
    {"name": "Spain", "artist_name": "Chick Corea", "moods": ["excited", "focused", "happy"], "tags": ["jazz", "fusion", "instrumental"]},
    {"name": "Cantaloupe Island", "artist_name": "Herbie Hancock", "moods": ["focused", "happy", "calm"], "tags": ["jazz", "fusion", "instrumental"]},
    {"name": "Sunset Lover", "artist_name": "Petit Biscuit", "moods": ["calm", "sad", "lonely"], "tags": ["calm", "dreamy"]},
    {"name": "Holocene", "artist_name": "Bon Iver", "moods": ["calm", "sad", "lonely"], "tags": ["calm", "dreamy"]},
    {"name": "Someone Like You", "artist_name": "Adele", "moods": ["sad", "lonely"], "tags": ["emotional", "soft"]},
    {"name": "Fix You", "artist_name": "Coldplay", "moods": ["sad", "anxious"], "tags": ["soft", "emotional"]},
    {"name": "To Build a Home", "artist_name": "The Cinematic Orchestra", "moods": ["sad", "lonely"], "tags": ["soft", "dreamy"]},
    {"name": "Love Poem", "artist_name": "IU", "moods": ["sad", "lonely", "anxious"], "tags": ["korean", "soft", "emotional", "comfort"]},
    {"name": "Through the Night", "artist_name": "IU", "moods": ["sad", "lonely", "anxious", "calm"], "tags": ["korean", "soft", "calm", "comfort"]},
    {"name": "Best Part", "artist_name": "Daniel Caesar feat. H.E.R.", "moods": ["sad", "lonely", "anxious", "calm"], "tags": ["rnb", "soul", "soft", "warm", "love"]},
    {"name": "Like I'm Gonna Lose You", "artist_name": "Meghan Trainor feat. John Legend", "moods": ["sad", "lonely", "anxious"], "tags": ["pop", "soft", "emotional", "warm", "love"]},
    {"name": "Ditto", "artist_name": "NewJeans", "moods": ["lonely", "calm", "anxious"], "tags": ["korean", "dreamy"]},
    {"name": "Hype Boy", "artist_name": "NewJeans", "moods": ["excited", "happy", "focused"], "tags": ["korean", "upbeat"]},
    {"name": "Super Shy", "artist_name": "NewJeans", "moods": ["excited", "anxious", "focused"], "tags": ["korean", "high_energy"]},
    {"name": "Love Dive", "artist_name": "IVE", "moods": ["happy", "excited"], "tags": ["korean", "upbeat"]},
    {"name": "Dynamite", "artist_name": "BTS", "moods": ["happy", "excited", "anxious"], "tags": ["korean", "high_energy"]},
    {"name": "Seven", "artist_name": "Jung Kook", "moods": ["excited", "anxious"], "tags": ["korean", "driving"]},
    {"name": "Attention", "artist_name": "NewJeans", "moods": ["focused", "excited"], "tags": ["korean", "driving"]},
    {"name": "instagram", "artist_name": "DEAN", "moods": ["sad", "lonely", "calm"], "tags": ["korean", "rnb", "soul", "soft"], "reason": "낮아진 감정을 부드럽게 받아주면서도, 한국 감성 R&B 특유의 공기가 잘 살아 있는 곡이에요."},
    {"name": "D (Half Moon)", "artist_name": "DEAN", "moods": ["sad", "lonely", "calm"], "tags": ["korean", "rnb", "soul", "dreamy"], "reason": "감정이 잠기지 않도록 천천히 떠받쳐 주는 멜로디가 좋아요."},
    {"name": "WA-R-R", "artist_name": "Colde", "moods": ["sad", "lonely", "calm"], "tags": ["korean", "rnb", "neo-soul", "soft"], "reason": "과하게 흔들지 않으면서도 한국 R&B의 결을 또렷하게 살려줘요."},
    {"name": "Don't Forget", "artist_name": "Crush", "moods": ["sad", "lonely"], "tags": ["korean", "rnb", "soul", "emotional"], "reason": "조용한 감정선을 지켜주면서, 듣는 순간 바로 분위기가 잡히는 곡이에요."},
    {"name": "HANGANG", "artist_name": "Hoody", "moods": ["sad", "lonely", "calm"], "tags": ["korean", "rnb", "soul", "calm"], "reason": "잔잔한 호흡과 부드러운 그루브가 지금 감정에 잘 맞아요."},
    {"name": "sleepless in ______", "artist_name": "pH-1", "moods": ["sad", "anxious", "calm"], "tags": ["korean", "rnb", "hip-hop", "soft"], "reason": "지친 마음을 무겁게 누르지 않으면서도, 밤공기 같은 결을 남겨줘요."},
    {"name": "Summer", "artist_name": "SAAY", "moods": ["happy", "excited", "calm"], "tags": ["korean", "rnb", "soul", "groove"]},
    {"name": "KICK BACK", "artist_name": "Kenshi Yonezu", "moods": ["excited", "focused", "angry"], "tags": ["jpop", "anime", "high_energy"], "reason": "제이팝 특유의 밀도 있는 전개가 확실하게 살아 있는 곡이에요."},
    {"name": "Idol", "artist_name": "YOASOBI", "moods": ["happy", "excited"], "tags": ["jpop", "anime", "upbeat"], "reason": "밝고 빠른 제이팝 에너지를 바로 느끼기 좋아요."},
    {"name": "Kaikai Kitan", "artist_name": "Eve", "moods": ["angry", "excited", "focused"], "tags": ["jpop", "anime", "rock"], "reason": "애니 송 특유의 추진력이 살아 있어서 분위기를 확 끌어줘요."},
    {"name": "Gurenge", "artist_name": "LiSA", "moods": ["excited", "angry", "focused"], "tags": ["jpop", "anime", "rock"], "reason": "애니 OST를 찾을 때 가장 직관적으로 붙는 에너지예요."},
    {"name": "Sparkle", "artist_name": "RADWIMPS", "moods": ["sad", "calm", "dreamy"], "tags": ["jpop", "anime", "soundtrack", "dreamy"], "reason": "애니 OST 특유의 서정성이 잘 살아 있어서 여운이 길게 남아요."},
    {"name": "Pretender", "artist_name": "Official HIGE DANDism", "moods": ["sad", "lonely", "calm"], "tags": ["jpop", "ballad", "emotional"], "reason": "제이팝 발라드의 감정선을 부드럽게 담아내는 곡이에요."},
    {"name": "Lemon", "artist_name": "Kenshi Yonezu", "moods": ["sad", "lonely"], "tags": ["jpop", "ballad", "emotional"], "reason": "제이팝의 대표적인 감성 곡으로, 서늘한 여운이 좋아요."},
    {"name": "Blue Bird", "artist_name": "Ikimonogakari", "moods": ["happy", "excited"], "tags": ["jpop", "anime", "upbeat"], "reason": "애니 오프닝처럼 시원하게 뻗는 느낌이 필요할 때 잘 맞아요."},
    {"name": "Brave Shine", "artist_name": "Aimer", "moods": ["sad", "focused", "calm"], "tags": ["jpop", "anime", "emotional"], "reason": "애니 OST의 드라마틱한 결을 부드럽게 담아내는 곡이에요."},
    {"name": "Into The Night", "artist_name": "YOASOBI", "moods": ["calm", "focused"], "tags": ["jpop", "emotional", "dreamy"], "reason": "제이팝의 선명한 보컬 중심 흐름을 느끼기 좋아요."},
    {"name": "American Idiot", "artist_name": "Green Day", "moods": ["angry", "anxious", "focused"], "tags": ["punk", "rock", "high_energy"], "reason": "에너지를 확 끌어올리고 싶을 때 가장 직선적으로 붙는 펑크락이에요."},
    {"name": "Basket Case", "artist_name": "Green Day", "moods": ["angry", "anxious", "focused"], "tags": ["punk", "rock", "high_energy"], "reason": "울적한 감정을 너무 무겁지 않게 날려버리는 속도가 좋아요."},
    {"name": "Misery Business", "artist_name": "Paramore", "moods": ["angry", "anxious", "excited"], "tags": ["punk", "rock", "high_energy"], "reason": "시원하게 달리는 기타와 보컬이 기분 전환용으로 잘 맞아요."},
    {"name": "All The Small Things", "artist_name": "Blink-182", "moods": ["happy", "excited", "focused"], "tags": ["punk", "pop-punk", "rock"], "reason": "가볍게 치고 나가는 팝펑크 결이 필요할 때 부담 없이 붙어요."},
    {"name": "Sugar, We're Goin Down", "artist_name": "Fall Out Boy", "moods": ["angry", "anxious", "excited"], "tags": ["punk", "rock", "high_energy"], "reason": "답답한 기분을 조금 더 세게 밀어내고 싶을 때 좋은 곡이에요."},
    {"name": "In Too Deep", "artist_name": "Sum 41", "moods": ["angry", "anxious", "focused"], "tags": ["punk", "rock", "high_energy"], "reason": "속도감이 살아 있어서 시원한 펑크락 흐름에 잘 붙어요."},
    {"name": "The Kids Aren't Alright", "artist_name": "The Offspring", "moods": ["angry", "anxious", "focused"], "tags": ["punk", "rock", "high_energy"], "reason": "거친 에너지와 직선적인 질감이 펑크락 요청에 잘 맞아요."},
    {"name": "Smells Like Teen Spirit", "artist_name": "Nirvana", "moods": ["angry", "anxious", "focused"], "tags": ["rock", "alternative", "high_energy"], "reason": "대놓고 거칠게 밀어붙이고 싶을 때 잘 맞는 대표적인 얼터너티브 록이에요."},
    {"name": "Clair de Lune", "artist_name": "Claude Debussy", "moods": ["calm", "sad", "lonely"], "tags": ["classical", "piano", "instrumental"], "reason": "클래식 피아노의 정서가 감정을 차분하게 정리해줘요."},
    {"name": "Gymnopédie No. 1", "artist_name": "Erik Satie", "moods": ["calm", "sad"], "tags": ["classical", "piano", "instrumental"], "reason": "클래식 특유의 느슨한 호흡이 마음을 안정시키는 데 좋아요."},
    {"name": "Three Little Birds", "artist_name": "Bob Marley & The Wailers", "moods": ["happy", "calm"], "tags": ["reggae", "uplifting", "groove"], "reason": "레게의 느긋한 리듬이 기분을 부드럽게 들어 올려줘요."},
    {"name": "The Thrill Is Gone", "artist_name": "B.B. King", "moods": ["sad", "lonely"], "tags": ["blues", "soul", "emotional"], "reason": "블루스의 깊은 결이 감정 정리에 잘 맞아요."},
    {"name": "An Ending (Ascent)", "artist_name": "Brian Eno", "moods": ["calm", "lonely"], "tags": ["ambient", "instrumental", "dreamy"], "reason": "앰비언트 특유의 넓은 공간감이 생각을 천천히 가라앉혀줘요."},
    {"name": "One More Time", "artist_name": "Daft Punk", "moods": ["happy", "excited"], "tags": ["house", "dance", "electronic"], "reason": "하우스/댄스 결을 직관적으로 느끼기 좋은 곡이에요."},
    {"name": "When The Sun Hits", "artist_name": "Slowdive", "moods": ["sad", "dreamy", "calm"], "tags": ["shoegaze", "dream-pop", "dreamy"], "reason": "슈게이즈 특유의 물결 같은 질감이 몽환적인 분위기를 잘 만들어줘요."},
    {"name": "Rhubarb", "artist_name": "Aphex Twin", "moods": ["calm", "lonely"], "tags": ["ambient", "electronic", "instrumental"], "reason": "차분한 전자음의 결이 앰비언트 요청에 잘 맞아요."},
    {"name": "I Like Me Better", "artist_name": "Lauv", "moods": ["happy", "lonely"], "tags": ["soft", "upbeat"]},
    {"name": "Permission to Dance", "artist_name": "BTS", "moods": ["happy", "excited"], "tags": ["korean", "upbeat"]},
    {"name": "The Nights", "artist_name": "Avicii", "moods": ["happy", "excited", "anxious"], "tags": ["high_energy", "upbeat"]},
    {"name": "Feel It Still", "artist_name": "Portugal. The Man", "moods": ["excited", "focused"], "tags": ["upbeat", "driving"]},
]

FALLBACK_LIMIT = 6


class SpotifyRecommendationError(RuntimeError):
    pass


def _spotify_request(url: str, access_token: str, params: dict[str, object] | None = None) -> dict:
    request_url = f"{url}?{urlencode({k: v for k, v in (params or {}).items() if v is not None})}" if params else url
    request = Request(
        request_url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        raise SpotifyRecommendationError(f"Spotify recommendation request failed: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise SpotifyRecommendationError(f"Spotify recommendation request failed: {exc.reason}") from exc


def _get_app_access_token() -> str | None:
    """Use the app token only to enrich verified fallback tracks with album art."""
    global _app_access_token, _app_access_token_expires_at

    if _app_access_token and time.time() < _app_access_token_expires_at:
        return _app_access_token
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        return None

    credentials = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode("utf-8")
    ).decode("ascii")
    request = Request(
        SPOTIFY_TOKEN_URL,
        data=urlencode({"grant_type": "client_credentials"}).encode("utf-8"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    access_token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(access_token, str) or not access_token:
        return None
    expires_in = payload.get("expires_in") if isinstance(payload, dict) else 3600
    _app_access_token = access_token
    _app_access_token_expires_at = time.time() + max(60, int(expires_in) - 60)
    return _app_access_token


@lru_cache(maxsize=1)
def _fallback_genre_pool() -> tuple[str, ...]:
    return (
        "acoustic",
        "ambient",
        "classical",
        "chill",
        "dance",
        "electronic",
        "folk",
        "funk",
        "indie",
        "metal",
        "party",
        "piano",
        "pop",
        "punk",
        "rock",
        "sad",
        "study",
    )


def _normalize_mood(mood: str | None) -> str:
    if not mood:
        return "calm"
    if mood in MOOD_PROFILES:
        return mood
    return MOOD_ALIASES.get(mood, mood.lower())


def _extract_context_genre_hints(context_text: str | None) -> list[str]:
    if not context_text or not isinstance(context_text, str):
        return []

    lowered = context_text.lower()
    matches: list[str] = []
    for keyword, genres in CONTEXT_GENRE_HINTS:
        haystack = lowered if keyword.isascii() else context_text
        if keyword in haystack:
            matches.extend(genres)
    return list(dict.fromkeys(matches))


def _extract_context_tags(context_text: str | None) -> list[str]:
    if not context_text or not isinstance(context_text, str):
        return []

    lowered = context_text.lower()
    tags: list[str] = []
    for keyword, mapped_tags in CONTEXT_TAG_HINTS:
        haystack = lowered if keyword.isascii() else context_text
        if keyword in haystack:
            tags.extend(mapped_tags)
    return list(dict.fromkeys(tags))


def _extract_genre_family_matches(context_text: str | None) -> tuple[list[str], list[str], dict[str, object]]:
    if not context_text or not isinstance(context_text, str):
        return [], [], {}

    lowered = context_text.lower()
    seed_genres: list[str] = []
    labels: list[str] = []
    params: dict[str, object] = {}

    for keywords, label, genres, audio_params in GENRE_FAMILY_HINTS:
        if any((keyword in lowered if keyword.isascii() else keyword in context_text) for keyword in keywords):
            labels.append(label)
            seed_genres.extend(genres)
            params.update(audio_params)

    return list(dict.fromkeys(seed_genres)), list(dict.fromkeys(labels)), params


def _has_explicit_genre_request(context_text: str | None) -> bool:
    explicit_genres, genre_labels, _ = _extract_genre_family_matches(context_text)
    return bool(explicit_genres or genre_labels)


def _merge_context_audio_hints(context_text: str | None) -> tuple[list[str], dict[str, object]]:
    genres: list[str] = []
    params: dict[str, object] = {}

    if not context_text or not isinstance(context_text, str):
        return genres, params

    explicit_genres, _, explicit_params = _extract_genre_family_matches(context_text)
    genres.extend(explicit_genres)
    params.update(explicit_params)

    lowered = context_text.lower()
    for keyword, data in CONTEXT_AUDIO_HINTS:
        haystack = lowered if keyword.isascii() else context_text
        if keyword in haystack:
            genres.extend(data.get("genres", []))  # type: ignore[arg-type]
            params.update(data.get("params", {}))  # type: ignore[arg-type]

    return list(dict.fromkeys(genres)), params


def _pick_seed_genres(
    mood: str,
    available_genres: set[str] | None = None,
    context_text: str | None = None,
) -> list[str]:
    profile = MOOD_PROFILES.get(mood, MOOD_PROFILES["calm"])
    explicit_genres, _, _ = _extract_genre_family_matches(context_text)
    if explicit_genres:
        if available_genres:
            filtered = [genre for genre in explicit_genres if genre in available_genres]
            if filtered:
                return filtered[:5]
            pool = [genre for genre in _fallback_genre_pool() if genre in available_genres]
            if pool:
                return pool[:5]
            return [next(iter(available_genres))]
        return explicit_genres[:5]
    if _context_prefers_korean_rnb(context_text):
        preferred = ["r&b", "r-n-b", "soul", "neo-soul", "indie"]
        if available_genres:
            filtered = [genre for genre in preferred if genre in available_genres]
            if filtered:
                return filtered[:5]
        return preferred[:5]
    context_genres, _ = _merge_context_audio_hints(context_text)
    candidates = explicit_genres + context_genres + list(profile["genres"])  # type: ignore[index]
    candidates.extend(_extract_context_genre_hints(context_text))
    candidates = list(dict.fromkeys(candidates))
    if available_genres:
        explicit_filtered = [genre for genre in explicit_genres if genre in available_genres]
        if explicit_filtered:
            return explicit_filtered[:5]
        filtered = [genre for genre in candidates if genre in available_genres]
        if filtered:
            return filtered[:5]
        pool = [genre for genre in _fallback_genre_pool() if genre in available_genres]
        if pool:
            return pool[:5]
        return [next(iter(available_genres))]
    return candidates[:5]


def _map_track(track: dict, mood_label: str, seed_genres: list[str]) -> TrackSummary:
    artists = track.get("artists") or []
    album = track.get("album") or {}
    primary_artist = artists[0].get("name") if artists and isinstance(artists[0], dict) else "Unknown Artist"
    album_images = album.get("images") or []
    album_image_url = album_images[0].get("url") if album_images and isinstance(album_images[0], dict) else None
    spotify_url = (track.get("external_urls") or {}).get("spotify") or (
        f"https://open.spotify.com/track/{track.get('id')}" if track.get("id") else None
    )
    chosen_seed = seed_genres[0] if seed_genres else "mood"
    duration_ms = track.get("duration_ms")
    reason = f"{mood_label} 분위기와 잘 맞는 {chosen_seed} 계열 트랙이에요."

    return TrackSummary(
        track_id=str(track.get("id") or track.get("uri") or track.get("name")),
        name=str(track.get("name") or "Unknown Track"),
        artist_name=str(primary_artist),
        album_name=album.get("name"),
        album_image_url=album_image_url,
        spotify_url=spotify_url,
        preview_url=track.get("preview_url"),
        duration_ms=duration_ms if isinstance(duration_ms, int) else None,
        reason_facts=_build_reason_facts(str(track.get("name") or "Unknown Track"), str(primary_artist), seed_genres),
        reason=reason,
    )


def _attach_particle(word: str, consonant: str = "이", vowel: str = "가") -> str:
    if not word:
        return word
    last_char = word[-1]
    code = ord(last_char)
    if 0xAC00 <= code <= 0xD7A3:
        has_batchim = (code - 0xAC00) % 28 != 0
        return f"{word}{consonant if has_batchim else vowel}"
    return f"{word}{vowel}"


def _excerpt(text: str | None, limit: int = 42) -> str:
    if not text:
        return ""
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}…"


def _context_intent(context_text: str | None) -> str:
    if not context_text or not isinstance(context_text, str):
        return ""

    lowered = context_text.lower()
    if any(token in context_text for token in ("집중하기 좋은", "집중", "몰입")):
        if any(token in lowered for token in ("jazz", "재즈", "standard", "스탠다드")):
            return "집중하기 좋은 스탠다드 재즈 흐름"
        return "집중력을 유지하기 좋은 흐름"
    if any(token in context_text for token in ("포트폴리오", "작업", "과제", "공부", "마감")):
        return "작업 속도를 유지"
    if any(token in context_text for token in ("불안", "초조", "걱정", "긴장")):
        return "긴장을 조금 낮추면서"
    if any(token in lowered for token in ("fast", "quick", "speed")) or "빠르게" in context_text or "빨리" in context_text:
        return "빠른 템포를 유지"
    return ""


def _reason_situation(mood: str, context_text: str | None) -> str:
    raw_text = context_text or ""
    lowered = raw_text.lower()
    if any(token in raw_text or token in lowered for token in ("취업", "입사", "면접", "지원서", "자소서", "이력서")):
        return "취업 준비가 마음처럼 풀리지 않아 초조한 지금"
    if _context_requests_comfort(context_text):
        return "불안한 마음을 가라앉히고 위로받고 싶은 지금 상황"
    if context_text and any(token in context_text for token in ("졸려", "피곤", "처져", "늘어")):
        return "처진 집중력을 다시 끌어올리고 싶은 순간"
    if context_text and any(token in context_text for token in ("공부", "작업", "과제", "마감", "집중", "몰입")):
        return "집중을 오래 이어가고 싶은 상황"
    return "지금의 감정과 원하는 분위기"


def _recommendation_need(context_text: str | None) -> str:
    raw_text = context_text or ""
    lowered = raw_text.lower()
    if any(token in raw_text or token in lowered for token in ("취업", "입사", "면접", "지원서", "자소서", "이력서")):
        return "마음처럼 진전되지 않는 취업 준비 때문에 쌓인 불안"
    if _context_requests_comfort(context_text):
        return "마음을 다독이고 위로받고 싶은 지금의 불안"
    return "지금 느끼는 감정"


def _connect_effect_to_situation(effect: str, situation: str) -> str:
    trimmed = effect.rstrip(".")
    endings = {
        "좋아요": "좋아",
        "좋습니다": "좋아",
        "도와줘요": "도와줘",
        "선택이에요": "선택이라",
    }
    for ending, replacement in endings.items():
        if trimmed.endswith(ending):
            trimmed = f"{trimmed[: -len(ending)]}{replacement}"
            break
    return f"{trimmed}, {situation}에 특히 추천해요."


def _connect_classification_effect(effect: str, situation: str) -> str:
    trimmed = effect.rstrip(".")
    for ending, replacement in (("만들어줘요", "만들어줘서"), ("더해줘요", "더해줘서"), ("도움을 줘요", "도움을 줘서"), ("좋아요", "좋아서")):
        if trimmed.endswith(ending):
            return f"{trimmed[: -len(ending)]}{replacement} {situation}에 맞춰 골랐어요."
    return f"{trimmed} 덕분에 {situation}에 맞춰 골랐어요."


def _split_context(raw_text: str | None) -> tuple[str, list[str]]:
    if not raw_text or not isinstance(raw_text, str):
        return "", []

    match = VIBE_PATTERN.match(raw_text)
    if not match:
        return raw_text.strip(), []

    free_text = raw_text[: match.start()].strip()
    vibes = [v.strip() for v in match.group(1).split(",") if v.strip()]
    return free_text, vibes


def _build_context_summary(context_text: str | None) -> dict[str, str | list[str]]:
    free_text, vibes = _split_context(context_text)
    lowered = (context_text or "").lower()
    explicit_genres, genre_labels, _ = _extract_genre_family_matches(context_text)

    style_bits: list[str] = []
    if any(token in lowered for token in ("rnb", "r&b", "r-n-b")) or "알앤비" in (context_text or ""):
        style_bits.append("R&B")
    if "한국" in (context_text or "") and style_bits:
        style_bits[0] = "한국 감성 R&B"
    elif "한국" in (context_text or ""):
        style_bits.append("한국 감성")
    style_bits.extend(genre_labels)
    if any(token in (context_text or "") for token in ("솔로", "혼자")):
        style_bits.append("솔로 감성")
    if any(token in lowered for token in ("swing", "스윙", "big band", "빅밴드")):
        style_bits.append("스윙 재즈")
    if any(token in lowered for token in ("bebop", "bop", "비밥", "hard bop", "하드밥", "post-bop", "포스트밥")):
        style_bits.append("비밥/하드밥")
    if any(token in lowered for token in ("bossa nova", "bossanova", "보사노바")):
        style_bits.append("보사노바")
    if any(token in lowered for token in ("jazz fusion", "fusion", "퓨전재즈")):
        style_bits.append("퓨전재즈")
    if any(token in lowered for token in ("cool jazz", "쿨재즈", "modal jazz", "모달재즈", "jazz", "재즈", "standard")):
        style_bits.append("재즈")
    if any(token in (context_text or "") for token in ("외로", "외롭")):
        style_bits.append("외로움")

    vibe_labels = [v for v in vibes if v in {"감성적인", "잔잔한", "몽환적인", "몰입되는"}]
    tags = _extract_context_tags(context_text)

    return {
        "free_text": free_text,
        "vibes": vibes,
        "style": " / ".join(dict.fromkeys(style_bits)),
        "vibe_phrase": " · ".join(vibe_labels),
        "genres": explicit_genres,
        "genre_phrase": " · ".join(genre_labels),
        "tags": tags,
        "intent": _context_intent(context_text),
    }


def _context_prefers_korean_rnb(context_text: str | None) -> bool:
    if not context_text or not isinstance(context_text, str):
        return False
    lowered = context_text.lower()
    has_korean = "한국" in context_text or "korean" in lowered
    has_rnb = any(token in lowered for token in ("rnb", "r&b", "r-n-b", "알앤비"))
    return has_korean and has_rnb


def _context_prefers_punk_rock(context_text: str | None) -> bool:
    if not context_text or not isinstance(context_text, str):
        return False
    lowered = context_text.lower()
    return any(token in context_text or token in lowered for token in ("펑크락", "punk rock", "punk", "펑크"))


def _context_requests_comfort(context_text: str | None) -> bool:
    if not context_text or not isinstance(context_text, str):
        return False

    lowered = context_text.lower()
    comfort_words = ("위로", "따뜻", "포근", "잔잔", "감성", "사랑 노래", "이별", "헤어", "다독")
    return sum(word in context_text or word in lowered for word in comfort_words) >= 2


def _build_contextual_search_terms(context_text: str | None) -> list[str]:
    if not context_text or not isinstance(context_text, str):
        return []

    lowered = context_text.lower()
    explicit_genres, genre_labels, _ = _extract_genre_family_matches(context_text)
    terms: list[str] = []

    if _context_prefers_korean_rnb(context_text):
        terms.extend(["DEAN", "Colde", "Crush", "Zion.T", "Hoody", "SAAY", "Heize", "BIBI"])
    if _context_prefers_punk_rock(context_text):
        terms.extend(["Green Day", "Paramore", "Blink-182", "Fall Out Boy", "Sum 41", "The Offspring", "Panic! At The Disco"])
    if "제이팝" in genre_labels or any(token in lowered for token in ("j-pop", "jpop", "japanese pop", "일본 팝")):
        terms.extend(["YOASOBI", "Aimer", "LiSA", "Kenshi Yonezu", "Official HIGE DANDism", "Vaundy", "Eve"])
    if "애니 OST" in genre_labels or any(token in lowered for token in ("anime ost", "anime soundtrack", "anisong", "anison", "애니", "오스트")):
        terms.extend(["LiSA", "RADWIMPS", "Eve", "Aimer", "Yuki Hayashi", "Hiroyuki Sawano"])
    if "시티팝" in genre_labels or any(token in lowered for token in ("city pop", "city-pop", "시티팝", "시티 팝")):
        terms.extend(["Tatsuro Yamashita", "Mariya Takeuchi", "Anri", "Miki Matsubara"])
    if "스윙 재즈" in genre_labels or any(token in lowered for token in ("swing", "스윙", "big band", "빅밴드")):
        terms.extend(["Benny Goodman", "Duke Ellington", "Count Basie", "Ella Fitzgerald", "Louis Armstrong", "Glenn Miller"])
    if "비밥/하드밥" in genre_labels or any(token in lowered for token in ("bebop", "bop", "비밥", "hard bop", "하드밥", "post-bop", "포스트밥")):
        terms.extend(["Charlie Parker", "Dizzy Gillespie", "Thelonious Monk", "Art Blakey", "Clifford Brown", "Sonny Rollins"])
    if "보사노바" in genre_labels or any(token in lowered for token in ("bossa nova", "보사노바", "bossanova")):
        terms.extend(["Joao Gilberto", "Antonio Carlos Jobim", "Stan Getz", "Astrud Gilberto", "Sergio Mendes"])
    if "퓨전재즈" in genre_labels or any(token in lowered for token in ("jazz fusion", "fusion", "퓨전재즈")):
        terms.extend(["Miles Davis", "Herbie Hancock", "Weather Report", "Chick Corea", "Return to Forever", "Mahavishnu Orchestra"])
    if "모던 재즈" in genre_labels or any(token in lowered for token in ("jazz", "재즈", "standard", "모던재즈", "cool jazz", "쿨재즈", "modal jazz", "모달재즈")):
        terms.extend(["Bill Evans", "Chet Baker", "Miles Davis", "John Coltrane", "Herbie Hancock", "Nujabes"])
    if "로파이" in genre_labels or any(token in lowered for token in ("lofi", "lo-fi", "로파이", "로피")):
        terms.extend(["Nujabes", "jinsang", "idealism", "Kupla", "kudasai"])
    if "한국 인디" in genre_labels or any(token in lowered for token in ("k-indie", "k indie", "한국 인디", "국내 인디")):
        terms.extend(["Hyukoh", "Se So Neon", "9m88", "DPR LIVE", "ADOY"])
    if any(token in lowered for token in ("클래식", "classical", "오케스트라", "orchestral")):
        terms.extend(["Ludovico Einaudi", "Yiruma", "Debussy", "Max Richter"])
    if any(token in lowered for token in ("메탈", "metal", "heavy metal")):
        terms.extend(["Metallica", "Bring Me The Horizon", "Iron Maiden", "Slipknot"])
    if any(token in lowered for token in ("일렉", "electronic", "edm", "house", "techno")):
        terms.extend(["Daft Punk", "Avicii", "Disclosure", "deadmau5"])

    # Explicit genre terms should appear first and duplicates should collapse later.
    terms.extend(explicit_genres)
    return list(dict.fromkeys([term.strip() for term in terms if isinstance(term, str) and term.strip()]))


def _pick_variant(seed: str, variants: list[str]) -> str:
    if not variants:
        return ""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return variants[int(digest[:8], 16) % len(variants)]


def _reason_focus(seed: str, index: int) -> tuple[str, str]:
    focuses = [
        ("도입부", "도입부가 감정을 천천히 열어줘서"),
        ("보컬", "보컬의 온도가 과하지 않아서"),
        ("리듬", "리듬이 너무 앞서지 않아서"),
        ("여백", "악기 사이 여백이 넉넉해서"),
        ("전개", "곡의 전개가 자연스럽게 이어져서"),
        ("여운", "끝난 뒤 여운이 오래 남아서"),
    ]
    digest = hashlib.sha256(f"{seed}|{index}".encode("utf-8")).hexdigest()
    return focuses[int(digest[:8], 16) % len(focuses)]


def _get_track_sound_hint(track: TrackSummary) -> tuple[str, str] | None:
    key = (track.name.strip().lower(), track.artist_name.strip().lower())
    return TRACK_SOUND_HINTS.get(key)


def build_recommendation_message(
    mood: str,
    context_text: str | None,
    track_count: int,
    tracks: list[TrackSummary] | None = None,
) -> str:
    normalized_mood = _normalize_mood(mood)
    mood_label = str(MOOD_PROFILES.get(normalized_mood, MOOD_PROFILES["calm"])["label"])
    context = _build_context_summary(context_text)
    korean_rnb_request = _context_prefers_korean_rnb(context_text)
    punk_request = _context_prefers_punk_rock(context_text)
    comfort_request = _context_requests_comfort(context_text)
    job_search_request = any(
        token in (context_text or "").lower()
        for token in ("취업", "입사", "면접", "지원서", "자소서", "이력서")
    )
    study_flow_request = any(token in (context_text or "").lower() for token in ("공부", "과제", "작업", "집중", "몰입"))
    avoids_overstimulation = any(token in (context_text or "").lower() for token in ("소란", "시끄", "방해", "과하지", "너무 강", "자극"))
    sleep_request = _is_sleep_request(context_text)
    constraints = extract_hard_constraints(context_text)
    verified_instrumental_only = bool(tracks) and all(is_verified_instrumental(track) for track in tracks)
    free_excerpt = _excerpt(str(context["free_text"]) if context["free_text"] else "", 46)
    vibe_text = str(context["vibe_phrase"])
    style_text = str(context["style"])
    genre_text = str(context.get("genre_phrase") or "")
    intent_text = str(context.get("intent") or "")
    tags = context.get("tags") or []
    track_signature = "|".join(track.track_id for track in (tracks or [])[:3])
    base_seed = f"{normalized_mood}|{context_text or ''}|{track_count}|{track_signature}"

    if study_flow_request and avoids_overstimulation:
        return "지금의 좋은 집중 흐름은 유지하면서도 너무 과하지 않게 활기를 더할 수 있는 곡들을 골라봤어요."

    if sleep_request and constraints["instrumental_required"] and verified_instrumental_only:
        return (
            "어젯밤 생각이 많아 충분히 쉬지 못한 만큼, 잠들기 전 부담 없이 들을 수 있는 잔잔한 연주곡 위주로 골라봤어요. "
            "복잡한 생각에서 잠시 거리를 두고 편하게 쉬어가고 싶은 순간에 어울리는 곡들입니다."
        )

    if comfort_request or (normalized_mood == "anxious" and job_search_request):
        return (
            f"{_recommendation_need(context_text)}이 느껴져서, 자극적인 곡보다 호흡을 고르게 해주는 쪽으로 {track_count}곡을 골랐어요. "
            f"따뜻한 보컬과 부드러운 무드를 중심으로, 초조함을 잠시 낮추고 다시 하루의 페이스를 찾는 데 어울리도록 구성했어요."
        )

    variants = [
        (
            f"오늘 느낀 ‘{mood_label}’은 그냥 눌러두기보다, "
            f"{intent_text or '지금의 흐름'}을 지키는 쪽으로 음악을 골랐어요. "
            f"{f'특히 {style_text} 결을 살리고 ' if style_text else ''}"
            f"{'스탠다드 재즈의 여유를 더해 ' if 'jazz' in tags or '재즈' in style_text else ''}"
            f"{'작업 템포를 놓치지 않게' if 'driving' in tags or 'focused' in tags else '지금 호흡을 안정적으로 이어가게'} "
            f"구성했어요."
        ),
        (
            f"입력해준 내용을 읽어보니, 지금은 ‘{mood_label}’를 "
            f"{'조금 다독이면서도' if 'tense' in tags else '담백하게 받아주면서도'} 흐름을 너무 끊지 않는 음악이 잘 맞아 보여요. "
            f"{f'직접 적어준 내용과 {style_text or vibe_text}를 같이 보면서 톤을 맞춰봤어요.' if free_excerpt or style_text or vibe_text else '그 결을 기준으로 톤을 맞춰봤어요.'}"
        ),
        (
            f"{'직접 적어준 맥락을 살려서' if free_excerpt else '지금 감정의 결을 살려서'} {track_count}곡을 골랐어요. "
            f"무드가 과하게 튀지 않도록, {style_text + (' / ' if vibe_text else '') if style_text else ''}{vibe_text or '현재 감정과 가까운 결'} 중심으로 맞췄어요."
        ),
        (
            f"‘{mood_label}’이 있는 날에는 너무 무거운 답보다, "
            f"{'속도를 유지할 수 있는 리듬' if 'driving' in tags else '숨을 고를 수 있는 호흡'}이 먼저 필요하더라고요. "
            f"{'한국 감성 R&B의 결을 더 살려서 ' if korean_rnb_request else ''}"
            f"{'펑크락의 시원한 직진감을 먼저 살려서 ' if punk_request else ''}"
            f"{f'{genre_text} 쪽 장르감을 더 또렷하게 살려서 ' if genre_text and not korean_rnb_request and not punk_request else ''}"
            f"{f'그래서 {style_text} 분위기를 조금 더 선명하게 살렸어요.' if style_text else '오늘은 그 온도를 지켜주는 쪽으로 골라봤어요.'}"
        ),
    ]
    return _pick_variant(base_seed, variants)


def _role_listening_sentence(recommendation_role: dict[str, str] | None, index: int) -> str:
    focus = (recommendation_role or {}).get("focus", "")
    situation_angle = (recommendation_role or {}).get("situation_angle", "")
    templates = {
        "생각의 속도를 늦추기": "잠시 머릿속의 속도를 늦추며 쉬어가고 싶을 때 잘 어울려요.",
        "긴장을 느슨하게 풀기": "스스로를 너무 몰아붙이고 있다고 느껴질 때 부담 없이 들을 수 있어요.",
        "복잡한 생각 정리하기": "여러 생각이 한꺼번에 떠오를 때 차분히 정리하며 듣기 좋습니다.",
        "조용한 위로의 시간 만들기": "계획대로 풀리지 않아 지친 순간에 잠깐 쉬어가며 듣기 좋아요.",
        "잠시 숨 고르기": "미래에 대한 걱정이 커질 때 잠깐 숨을 고르며 듣기 좋습니다.",
        "현실적인 고민에서 거리 두기": "현실적인 고민이 계속 맴돌 때 잠시 다른 데로 시선을 돌리고 싶다면 들어보세요.",
        "현재 공부 흐름 유지": "지금의 공부 흐름을 그대로 이어가며 듣기 좋아요.",
        "적당한 활기 더하기": "너무 처지지 않게 가벼운 활기를 더하고 싶을 때 잘 어울려요.",
        "기분 좋은 텐션 유지": "기분 좋은 텐션을 과하지 않게 이어가고 싶을 때 잘 맞아요.",
        "지루함 방지": "집중이 조금 느슨해지는 구간에 분위기를 가볍게 바꾸고 싶을 때 어울려요.",
        "공부 템포 유지": "해야 할 일을 같은 템포로 이어가며 듣기 좋습니다.",
        "짧은 분위기 환기": "공부 흐름을 크게 바꾸지 않고 분위기를 잠깐 바꾸고 싶을 때 잘 어울려요.",
        "기분 좋은 흐름 유지": "지금의 좋은 흐름을 그대로 이어가며 듣기 좋아요.",
        "몰입 상태 이어가기": "지금의 몰입을 무리 없이 이어가고 싶을 때 잘 맞아요.",
        "잠들기 전 긴장 내려놓기": "잠들기 전 몸과 마음의 긴장을 조금 내려놓고 싶을 때 잘 어울려요.",
        "생각의 속도 늦추기": "생각이 계속 이어져 쉽게 잠들기 어려운 순간에, 머릿속의 속도를 조금 늦추며 듣기 좋아요.",
        "조용히 쉬어가기": "자극적인 분위기보다 조용히 쉬어가고 싶은 밤에 부담 없이 들을 수 있어요.",
        "수면 전 분위기 가라앉히기": "잠자리에 들기 전 차분한 분위기로 하루를 마무리하고 싶을 때 잘 맞아요.",
        "복잡한 생각에서 거리 두기": "여러 생각이 한꺼번에 떠오를 때 잠시 다른 곳에 마음을 두고 싶다면 들어보세요.",
        "편안한 잠자리 준비": "잠들기 전 편안한 시간을 만들고 싶은 순간에 곁들이기 좋아요.",
    }
    if focus in templates:
        return templates[focus]
    if situation_angle:
        return f"{situation_angle}, 잠시 쉬어가며 듣기 좋아요."
    return [
        "잠시 생각의 속도를 늦추며 쉬어가고 싶을 때 잘 어울려요.",
        "복잡한 마음을 천천히 정리하며 듣기 좋습니다.",
    ][index % 2]


def _tag_feature_sentence(track_tags: list[str], tag_labels: dict[str, str]) -> str | None:
    tag_set = set(track_tags)
    combinations = (
        (("dreamy", "calm"), "몽환적이고 차분하게 가라앉는 분위기가 부담 없이 이어지는 곡이에요."),
        (("soft", "warm"), "부드럽고 따뜻한 분위기가 편안하게 이어지는 곡이에요."),
        (("rnb", "soul"), "R&B의 편안한 그루브와 소울 특유의 부드러운 분위기가 어우러지는 곡이에요."),
        (("upbeat", "high_energy"), "밝고 활기찬 분위기가 일정하게 이어지는 곡이에요."),
        (("comfort", "calm"), "편안하면서 차분한 분위기가 조용히 이어지는 곡이에요."),
        (("emotional", "soft"), "감정적이지만 부드럽게 이어지는 분위기가 인상적인 곡이에요."),
    )
    for required_tags, sentence in combinations:
        if set(required_tags).issubset(tag_set):
            return sentence

    features = [tag_labels[tag] for tag in track_tags if tag in tag_labels]
    if not features:
        return None
    primary_feature = features[0]
    secondary_feature = next((feature for feature in features[1:] if feature != primary_feature), None)
    if secondary_feature:
        return f"{primary_feature}, {secondary_feature}처럼 서로 다른 특징이 함께 느껴지는 곡이에요."
    return f"{primary_feature} 같은 특징이 느껴지는 곡이에요."


def _sleep_feature_sentence(track_tags: list[str], track_moods: list[str]) -> str | None:
    """Use only calm-oriented catalog metadata when explaining a sleep ranking."""
    tag_set = set(track_tags)
    mood_set = set(track_moods)
    if {"ambient", "dreamy"}.issubset(tag_set):
        return "앰비언트와 몽환적인 분위기가 차분하게 이어지는 연주곡이에요."
    if {"classical", "piano"}.issubset(tag_set):
        return "클래식 피아노 중심의 연주가 조용히 이어지는 곡이에요."
    if "ambient" in tag_set and "calm" in mood_set:
        return "앰비언트 기반의 차분한 분위기가 이어지는 연주곡이에요."
    if "calm" in tag_set or "calm" in mood_set:
        return "차분한 분위기가 부담 없이 이어지는 연주곡이에요."
    if "dreamy" in tag_set:
        return "몽환적인 분위기가 잔잔하게 이어지는 연주곡이에요."
    return None


def build_track_reason(
    track: TrackSummary,
    mood: str,
    context_text: str | None,
    index: int,
    recommendation_role: dict[str, str] | None = None,
) -> str:
    normalized_mood = _normalize_mood(mood)
    mood_label = str(MOOD_PROFILES.get(normalized_mood, MOOD_PROFILES["calm"])["label"])
    context = _build_context_summary(context_text)
    korean_rnb_request = _context_prefers_korean_rnb(context_text)
    punk_request = _context_prefers_punk_rock(context_text)
    vibe_text = str(context["vibe_phrase"])
    free_excerpt = _excerpt(str(context["free_text"]) if context["free_text"] else "", 42)
    style_text = str(context["style"])
    genre_text = str(context.get("genre_phrase") or "")
    intent_text = str(context.get("intent") or "")
    tags = context.get("tags") or []
    track_name = track.name
    artist_name = track.artist_name
    album_name = track.album_name or ""
    focus_label, focus_phrase = _reason_focus(f"{track.track_id}|{normalized_mood}|{context_text or ''}", index)
    context_hook = "직접 적어준 취향"
    if korean_rnb_request:
        context_hook = "한국 감성 R&B 취향"
    elif punk_request:
        context_hook = "시원한 펑크락 취향"
    elif genre_text:
        context_hook = f"{genre_text} 취향"
    elif vibe_text:
        context_hook = f"{vibe_text} 톤"

    sound_hint = _get_track_sound_hint(track)
    if sound_hint:
        sound_point, _ = sound_hint
        return (
            f"{_attach_particle(sound_point)} 자연스럽게 드러나는 곡이에요. "
            f"{_role_listening_sentence(recommendation_role, index)}"
        )

    facts = track.reason_facts or {}
    track_tags = [str(tag) for tag in facts.get("tags", []) if tag]
    track_moods = [str(item) for item in facts.get("moods", []) if item]
    if _is_sleep_request(context_text):
        sleep_feature = _sleep_feature_sentence(track_tags, track_moods)
        if sleep_feature:
            return f"{sleep_feature} {_role_listening_sentence(recommendation_role, index)}"
    situation = _reason_situation(normalized_mood, context_text)
    tag_labels = {
        "soft": "부드러운 사운드",
        "emotional": "감성적인 분위기",
        "calm": "차분한 무드",
        "dreamy": "몽환적인 분위기",
        "warm": "따뜻한 분위기",
        "comfort": "위로가 되는 분위기",
        "love": "사랑 노래 분위기",
        "soul": "소울 계열의 정서",
        "rnb": "R&B 계열의 그루브",
        "instrumental": "연주 중심 구성",
        "jazz": "재즈 계열의 리듬",
        "upbeat": "경쾌한 에너지",
        "high_energy": "높은 에너지",
        "driving": "추진력 있는 리듬",
    }
    feature_sentence = _tag_feature_sentence(track_tags, tag_labels)
    if feature_sentence:
        return (
            f"{feature_sentence} "
            f"{_role_listening_sentence(recommendation_role, index)}"
        )

    fallback_openings = {
        "anxious": "생각이 많고 마음이 조급한 순간에 부담 없이 곁들여 듣기 좋은 곡이에요.",
        "focused": "해야 할 일이 많아 마음이 분주할 때 부담 없이 곁들여 듣기 좋은 곡이에요.",
    }
    is_studying = any(token in (context_text or "").lower() for token in ("공부", "과제", "작업", "집중", "몰입"))
    is_preparing_sleep = _is_sleep_request(context_text)
    fallback_opening = (
        "자극적인 분위기보다 편안하게 쉬어갈 수 있는 방향으로 고른 곡이에요."
        if is_preparing_sleep
        else "현재의 좋은 공부 흐름을 크게 바꾸지 않으면서 가볍게 곁들이기 좋은 곡이에요."
        if is_studying
        else fallback_openings.get(normalized_mood, "지금의 감정에 부담 없이 곁들여 듣기 좋은 곡이에요.")
    )
    fallback_angles = [
        "잠시 생각의 속도를 늦추며 쉬어가고 싶을 때",
        "마음을 조금 가볍게 하며 숨을 고르고 싶을 때",
        "복잡한 생각을 천천히 정돈하고 싶을 때",
        "오늘의 감정에 조용히 머물고 싶을 때",
        "부담 없이 잠깐 쉬어가고 싶을 때",
        "현실적인 고민에서 잠시 거리를 두고 싶을 때",
    ]
    if is_studying and (recommendation_role or {}).get("focus") == "짧은 분위기 환기":
        return (
            "현재의 좋은 공부 흐름에 부담 없이 곁들이기 좋은 곡이에요. "
            "같은 분위기가 조금 지루해질 때 가볍게 변화를 주고 싶다면 들어보세요."
        )
    return (
        f"{fallback_opening} "
        f"{_role_listening_sentence(recommendation_role, index) if recommendation_role else fallback_angles[index % len(fallback_angles)] + ' 들어보세요.'}"
    )

    if korean_rnb_request:
        variants = [
            (
                f"{artist_name}의 {track_name}은 지금처럼 {_attach_particle(mood_label)} 있는 날에 "
                f"{focus_phrase} 한국 감성을 부드럽게 받쳐줘요. "
                f"{context_hook}를 같이 반영했고, "
                f"{'잔잔한 보컬과 부드러운 리듬이' if 'soft' in tags or 'calm' in tags else '감정을 너무 세게 흔들지 않는 흐름이'} "
                f"지금 기분을 안정적으로 받쳐줘요."
            ),
            (
                f"{track_name}은 {album_name + '라는 앨범 안에서 ' if album_name else ''}"
                f"{'한국 R&B 특유의 공기감' if korean_rnb_request else '부드러운 결'}가 살아 있어서, "
                f"{mood_label}가 남아 있는 상태에서도 흐름을 이어가기 좋아요. "
                f"{'특히 직접 적어준 문장과 한국 감성 R&B를 찾는 흐름이 잘 맞고, ' if free_excerpt else ''}"
                f"{'과하게 들뜨지 않으면서도 깊이가 남는 곡' if 'dreamy' in tags or 'emotional' in tags else '조용히 몰입하기 좋은 곡'}이에요."
            ),
            (
                f"{artist_name} 특유의 분위기가 {track_name}에서 자연스럽게 드러나서, "
                f"{'팝송보다 더 가까운 한국 R&B 쪽 결을 원할 때' if korean_rnb_request else '지금 감정을 다루는 데'} 잘 맞아요. "
                f"{f'{style_text or vibe_text} 취향을 같이 반영했고, ' if style_text or vibe_text else ''}"
                f"{'마음이 내려앉지 않게 부드럽게 받쳐주는 점' if 'sad' in tags or 'lonely' in tags else '호흡이 끊기지 않게 이어주는 점'}이 좋아요."
            ),
            (
                f"{index + 1}번째로 둔 이유는, {track_name}이 {mood_label}의 감정을 "
                f"{'조금 더 깊게 안아주면서도' if 'emotional' in tags else '무겁게 끌고 가지 않으면서'} "
                f"한국 감성 R&B의 속도를 유지해주기 때문이에요. "
                f"{'직접 적어준 내용과도 자연스럽게 이어져요.' if free_excerpt else '지금처럼 감정과 취향을 함께 챙길 때 자연스럽게 어울려요.'}"
            ),
        ]
    elif punk_request:
        variants = [
            (
                f"{artist_name}의 {track_name}은 지금처럼 {_attach_particle(mood_label)} 남아 있을 때 "
                f"{focus_phrase} 펑크락의 시원한 직진감을 살려줘요. "
                f"{context_hook}를 함께 반영했고, "
                f"{'거친 기타와 빠른 전개가' if 'high_energy' in tags or 'driving' in tags else '빠르게 몰아치는 에너지가'} "
                f"울적한 기분을 너무 오래 붙잡지 않게 해줘요."
            ),
            (
                f"{track_name}은 {('앨범 ' + album_name + '의' if album_name else '')} "
                f"펑크락 쪽 질감이 살아 있어서, 원하는 방향을 더 정확하게 밀어줘요. "
                f"{'직접 적어준 문장처럼 시원한 펑크락을 찾는 흐름과 잘 맞고, ' if free_excerpt else ''}"
                f"{'답답함을 빠르게 날려주는' if 'high_energy' in tags else '기분 전환에 바로 붙는'} 곡이에요."
            ),
            (
                f"{artist_name} 특유의 에너지가 {track_name}에서 직선적으로 살아나서, "
                f"펑크락을 듣고 싶다는 요청에 더 가깝게 붙어요. "
                f"{f'{style_text or vibe_text} 취향을 같이 반영했고, ' if style_text or vibe_text else ''}"
                f"{'너무 팝처럼 매끈하게 가지 않고' if 'pop' in tags else '시원하게 터지는'} 점이 좋아요."
            ),
            (
                f"{index + 1}번째 곡으로 둔 이유는, {track_name}이 "
                f"울적한 감정을 너무 질질 끌지 않으면서도 펑크락의 속도로 바꿔 주기 때문이에요. "
                f"{'직접 적어준 장르 요청에도 잘 붙어요.' if free_excerpt else '지금처럼 장르를 분명히 적어준 경우에 특히 잘 맞아요.'}"
            ),
        ]
    elif genre_text:
        variants = [
            (
                f"{artist_name}의 {track_name}은 지금처럼 {_attach_particle(mood_label)} 남아 있을 때 "
                f"{focus_phrase} {genre_text} 결을 자연스럽게 이어줘요. "
                f"{context_hook}와 함께 봤고, "
                f"{'너무 멀리 가지 않으면서' if 'calm' in tags or 'soft' in tags else '장르의 속도를 살리면서'} "
                f"듣기 좋게 붙어요."
            ),
            (
                f"{track_name}은 {genre_text}를 듣고 싶다는 요청에 맞춰, "
                f"장르의 핵심 느낌이 먼저 느껴지도록 골랐어요. "
                f"{'특히 직접 장르를 적어준 경우와 잘 맞고, ' if free_excerpt else ''}"
                f"{'너무 팝 쪽으로 새지 않게' if 'pop' in tags else '원하는 결을 유지하면서'} 이어져요."
            ),
            (
                f"{artist_name} 특유의 분위기가 {track_name}에서 {genre_text}의 결로 잘 드러나서, "
                f"감정과 장르를 같이 잡고 싶을 때 어울려요. "
                f"{f'{style_text or vibe_text} 취향도 같이 반영했고, ' if style_text or vibe_text else ''}"
                f"{'기분 전환이 필요할 때도 과하지 않게' if 'high_energy' not in tags else '에너지를 확실히 올려주면서'} 들을 수 있어요."
            ),
            (
                f"{index + 1}번째 곡으로 둔 이유는, {track_name}이 "
                f"{genre_text} 장르의 질감을 유지하면서도 {mood_label} 감정을 잘 받쳐주기 때문이에요. "
                f"{'직접 입력한 취향과도 자연스럽게 이어져요.' if free_excerpt else '지금처럼 장르를 분명히 말해준 요청에 잘 맞아요.'}"
            ),
        ]
    else:
        variants = [
            (
                f"{artist_name}의 {track_name}은 지금처럼 {_attach_particle(mood_label)} 남아 있는 날에 "
                f"{intent_text or '작업 흐름'}을 유지하면서 들을 수 있게 골랐어요. "
                f"{'직접 적어준 내용의 결도 같이 반영했고, ' if free_excerpt else ''}"
                f"{'속도는 살리되 너무 산만하지 않게' if 'driving' in tags else '감정을 너무 세게 흔들지 않게'} 이어지는 점이 좋아요."
            ),
            (
                f"{track_name}은 {('앨범 ' + album_name + '의' if album_name else '')} 결이 "
                f"{'몰입감 있게' if 'focused' in tags or 'rhythmic' in tags else '부드럽게'} 이어져서, "
                f"{mood_label}가 있는 상태에서도 흐름을 끊지 않아요. "
                f"{f'원했던 {style_text or vibe_text} 느낌이 같이 살아 있고, ' if style_text or vibe_text else ''}"
                f"{'빠르게 작업할 때도 버퍼 역할을 해주는 곡' if 'driving' in tags else '지금 감정을 안정적으로 받쳐주는 곡'}이에요."
            ),
            (
                f"이 곡은 {artist_name} 특유의 분위기가 살아 있어서, {mood_label}를 "
                f"{'조용히 잠재우기보다' if 'high_energy' in tags else '무리 없이'} 다루는 데 좋아요. "
                f"{f'{style_text or vibe_text} 쪽 결을 살려서, ' if style_text or vibe_text else ''}"
                f"{'브러시 드럼과 피아노 같은 재즈의 결이 작업 속도에 잘 붙고, ' if 'jazz' in tags or '재즈' in style_text else ''}"
                f"{'집중력을 오래 유지하고 싶을 때' if 'focused' in tags else '감정이 흔들리는 순간에도'} 부담이 적어요."
            ),
            (
                f"{track_name}은 {index + 1}번째 곡답게 흐름의 온도를 정리해 주는 자리예요. "
                f"{'직접 적어준 상황' if free_excerpt else '지금의 상황'}을 생각했을 때 "
                f"{'너무 처지지 않고' if 'upbeat' in tags else '부담을 키우지 않고'} 이어지도록 골랐어요. "
                f"{f'특히 {style_text or vibe_text} 취향이 있으면 더 자연스럽게 붙어요.' if style_text or vibe_text else ''}"
            ),
        ]

    seed = f"{track.track_id}|{normalized_mood}|{context_text or ''}|{index}"
    return _pick_variant(seed, variants)


def _search_track(access_token: str, name: str, artist_name: str, reason: str) -> TrackSummary | None:
    # Spotify 검색은 정확한 문장 매칭에 약해서, 제목/아티스트 조합을 여러 방식으로 시도한다.
    queries = [
        f'track:"{name}" artist:"{artist_name}"',
        f"{name} {artist_name}",
        f'track:"{name}"',
        name,
        artist_name,
    ]

    for query in queries:
        try:
            response = _spotify_request(
                SPOTIFY_SEARCH_URL,
                access_token,
                params={"q": query, "type": "track", "limit": 5},
            )
        except SpotifyRecommendationError:
            continue

        tracks = (((response or {}).get("tracks") or {}).get("items")) or []
        for track in tracks:
            if not isinstance(track, dict):
                continue
            album = track.get("album") or {}
            album_images = album.get("images") or []
            album_image_url = album_images[0].get("url") if album_images and isinstance(album_images[0], dict) else None
            spotify_url = (track.get("external_urls") or {}).get("spotify") or (
                f"https://open.spotify.com/track/{track.get('id')}" if track.get("id") else None
            )
            if album_image_url or spotify_url:
                mapped = _map_track(track, artist_name, [name])
                if _canonical_track_token(mapped.name) == _canonical_track_token(name) and _canonical_track_token(
                    mapped.artist_name
                ) == _canonical_track_token(artist_name):
                    mapped.reason_facts = _build_reason_facts(name, artist_name)
                    mapped.reason = reason
                    return mapped

    return None


def _search_tracks_by_query(
    access_token: str,
    query: str,
    reason: str,
    mood_label: str,
    seed_genres: list[str],
    limit: int = 3,
) -> list[TrackSummary]:
    try:
        response = _spotify_request(
            SPOTIFY_SEARCH_URL,
            access_token,
            params={"q": query, "type": "track", "limit": limit},
        )
    except SpotifyRecommendationError:
        return []

    items = (((response or {}).get("tracks") or {}).get("items")) or []
    results: list[TrackSummary] = []
    for track in items:
        if not isinstance(track, dict):
            continue
        mapped = _map_track(track, mood_label, seed_genres)
        mapped.reason = reason
        results.append(mapped)
    return results


def _fetch_available_genres(access_token: str) -> set[str]:
    response = _spotify_request(SPOTIFY_AVAILABLE_GENRES_URL, access_token)
    genres = response.get("genres") or []
    return {str(genre) for genre in genres if genre}


def _build_spotify_search_url(name: str, artist_name: str) -> str:
    query = urlencode({"q": f"{name} {artist_name}"})
    return f"https://open.spotify.com/search/{query[2:]}"


def _score_fallback_candidate(candidate: dict[str, object], mood: str, context_text: str | None) -> int:
    score = 0
    candidate_moods = {str(item) for item in candidate.get("moods", []) if item}
    candidate_tags = {str(item) for item in candidate.get("tags", []) if item}
    candidate_name = str(candidate.get("name") or "")
    candidate_artist = str(candidate.get("artist_name") or "")
    context_tags = set(_extract_context_tags(context_text))
    context_lower = (context_text or "").lower()
    korean_rnb_request = _context_prefers_korean_rnb(context_text)
    punk_request = _context_prefers_punk_rock(context_text)
    comfort_request = _context_requests_comfort(context_text)
    sleep_request = _is_sleep_request(context_text)
    explicit_genres, _, _ = _extract_genre_family_matches(context_text)
    explicit_genre_set = set(explicit_genres)

    if mood in candidate_moods:
        score += 6
    if candidate_moods & {"anxious", "focused"} and mood in {"anxious", "focused"}:
        score += 2
    if candidate_tags & context_tags:
        score += 6
    if explicit_genre_set and candidate_tags & explicit_genre_set:
        score += 7
    if explicit_genre_set and not (candidate_tags & explicit_genre_set):
        score -= 4
    if "한국" in (context_text or "") and "korean" in candidate_tags:
        score += 6
    if any(token in context_lower for token in ("rnb", "r&b", "알앤비")) and "rnb" in candidate_tags:
        score += 5
    if korean_rnb_request and candidate_tags & {"korean", "rnb", "soul", "neo-soul"}:
        score += 9
    if korean_rnb_request and "pop" in candidate_tags and not (candidate_tags & {"korean", "rnb", "soul", "neo-soul"}):
        score -= 5
    if korean_rnb_request and candidate_artist in {"DEAN", "Colde", "Crush", "Zion.T", "Hoody", "SAAY", "Heize", "BIBI"}:
        score += 8
    if punk_request and candidate_tags & {"punk", "pop-punk", "rock", "high_energy", "driving"}:
        score += 10
    if punk_request and "pop" in candidate_tags and not (candidate_tags & {"punk", "pop-punk", "rock"}):
        score -= 6
    if punk_request and candidate_artist in {"Green Day", "Paramore", "Blink-182", "Fall Out Boy", "Sum 41", "The Offspring", "Panic! At The Disco"}:
        score += 8
    if comfort_request and candidate_tags & {"soft", "emotional", "calm", "dreamy", "warm", "comfort", "love", "soul"}:
        score += 12
    if comfort_request and candidate_tags & {"punk", "pop-punk", "rock", "high_energy", "driving"}:
        score -= 18
    if sleep_request:
        # Instrumental is a gate, not a sleep-suitability score. Prefer candidates
        # with calm/rest metadata and strongly demote energetic jazz subgenres.
        if "calm" in candidate_moods:
            score += 16
        if "sad" in candidate_moods:
            score += 4
        if candidate_tags & {"ambient", "piano", "classical"}:
            score += 22
        if candidate_tags & {"calm", "soft", "dreamy", "emotional"}:
            score += 12
        if candidate_tags & {"fusion", "bebop", "hard-bop", "swing", "big-band", "high_energy", "driving"}:
            score -= 28
        if candidate_tags & {"jazz", "standard"}:
            score += 3
    if any(token in context_lower for token in ("스윙", "swing", "빅밴드", "big band")) and candidate_tags & {"jazz", "standard", "instrumental"}:
        score += 7
    if any(token in context_lower for token in ("비밥", "bebop", "bop", "하드밥", "hard bop", "포스트밥", "post-bop")) and candidate_tags & {"jazz", "instrumental"}:
        score += 7
    if any(token in context_lower for token in ("보사노바", "bossa nova", "bossanova")) and candidate_tags & {"bossa-nova", "latin", "acoustic"}:
        score += 8
    if any(token in context_lower for token in ("퓨전재즈", "jazz fusion", "fusion")) and candidate_tags & {"jazz", "fusion", "instrumental"}:
        score += 8
    if any(token in context_lower for token in ("재즈", "jazz", "스탠다드", "standard", "모던재즈", "cool jazz", "쿨재즈", "모달재즈", "modal jazz")) and candidate_tags & {"jazz", "standard", "instrumental"}:
        score += 8
    if any(token in context_lower for token in ("빠르게", "빨리", "작업", "포트폴리오", "마감")) and candidate_tags & {"driving", "focused"}:
        score += 5
    if any(token in context_lower for token in ("강렬", "신나")) and candidate_tags & {"high_energy", "upbeat"}:
        score += 5
    if any(token in context_lower for token in ("몽환", "감성", "잔잔", "위로")) and candidate_tags & {"dreamy", "soft", "emotional", "calm"}:
        score += 3

    seed = f"{mood}|{context_text or ''}|{candidate_name}|{candidate_artist}"
    score += int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:4], 16) % 7
    return score


def _select_fallback_catalog(
    mood: str,
    context_text: str | None,
    limit: int,
    selection_guidance: dict[str, Any] | None = None,
) -> list[dict[str, object]]:
    catalog = FALLBACK_LIBRARY
    constraints = extract_hard_constraints(context_text)
    if constraints["instrumental_required"]:
        # A missing tag is unknown, not proof that a track has no vocals.
        catalog = [
            candidate
            for candidate in catalog
            if "instrumental" in {str(tag).lower() for tag in candidate.get("tags", []) if tag}
        ]
    if _context_prefers_korean_rnb(context_text):
        preferred = [
            candidate
            for candidate in catalog
            if "korean" in {str(tag) for tag in candidate.get("tags", []) if tag}
            and {str(tag) for tag in candidate.get("tags", []) if tag} & {"rnb", "soul", "neo-soul", "soft", "dreamy"}
        ]
        if preferred:
            catalog = preferred + [candidate for candidate in catalog if candidate not in preferred]
    elif _context_requests_comfort(context_text):
        preferred = [
            candidate
            for candidate in catalog
            if {"soft", "emotional", "calm", "dreamy", "warm", "comfort", "love", "soul"}
            & {str(tag) for tag in candidate.get("tags", []) if tag}
            and not {"punk", "pop-punk", "rock", "high_energy", "driving"}
            & {str(tag) for tag in candidate.get("tags", []) if tag}
        ]
        if preferred:
            catalog = preferred + [candidate for candidate in catalog if candidate not in preferred]
    elif _context_prefers_punk_rock(context_text):
        preferred = [
            candidate
            for candidate in catalog
            if {"punk", "pop-punk", "rock", "high_energy"} & {str(tag) for tag in candidate.get("tags", []) if tag}
        ]
        if preferred:
            catalog = preferred + [candidate for candidate in catalog if candidate not in preferred]

    if selection_guidance and not _has_explicit_genre_request(context_text):
        avoid_tags = {str(tag) for tag in selection_guidance.get("avoid_tags", [])}
        preferred_tags = {str(tag) for tag in selection_guidance.get("preferred_tags", [])}
        safe = [
            candidate
            for candidate in catalog
            if not avoid_tags.intersection({str(tag) for tag in candidate.get("tags", [])})
        ]
        if safe:
            preferred = [
                candidate
                for candidate in safe
                if preferred_tags.intersection({str(tag) for tag in candidate.get("tags", [])})
            ]
            catalog = preferred + [candidate for candidate in safe if candidate not in preferred]

    ranked = sorted(
        catalog,
        key=lambda candidate: (
            -_score_fallback_candidate(candidate, mood, context_text),
            str(candidate.get("name") or ""),
        ),
    )
    unique: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in ranked:
        key = (str(candidate.get("name") or ""), str(candidate.get("artist_name") or ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
        if len(unique) >= limit:
            break
    return unique


def _fallback_tracks(
    mood: str,
    access_token: str | None = None,
    context_text: str | None = None,
    limit: int = FALLBACK_LIMIT,
    selection_guidance: dict[str, Any] | None = None,
) -> list[TrackSummary]:
    constraints = extract_hard_constraints(context_text)
    # For a hard instrumental request, keep searching the verified catalog until
    # enough tracks with real Spotify album art are available.
    catalog_limit = len(FALLBACK_LIBRARY) if access_token and constraints["instrumental_required"] else limit
    catalog = _select_fallback_catalog(mood, context_text, catalog_limit, selection_guidance)
    if not access_token:
        tracks = [
            TrackSummary(
                track_id=f"fallback-{mood}-{index + 1}",
                name=str(item["name"]),
                artist_name=str(item["artist_name"]),
                reason_facts=_build_reason_facts(str(item["name"]), str(item["artist_name"])),
                reason=str(item.get("reason") or "지금 분위기에 맞게 골라본 곡이에요."),
                spotify_url=_build_spotify_search_url(str(item["name"]), str(item["artist_name"])),
            )
            for index, item in enumerate(catalog)
        ]
        return validate_hard_constraints(tracks, context_text)

    resolved: list[TrackSummary] = []
    unresolved: list[TrackSummary] = []
    cover_first = constraints["instrumental_required"]
    for index, item in enumerate(catalog):
        try:
            track = _search_track(
                access_token,
                str(item["name"]),
                str(item["artist_name"]),
                str(item.get("reason") or "지금 분위기에 맞게 골라본 곡이에요."),
            )
            if track is not None and (track.album_image_url or not cover_first):
                resolved.append(track)
                if len(resolved) >= limit:
                    break
                continue
        except Exception:
            pass

        if cover_first:
            # Keep looking: a verified track without a resolved cover should not
            # displace a later verified candidate with real album art.
            unresolved.append(
                TrackSummary(
                    track_id=f"fallback-{mood}-{index + 1}",
                    name=str(item["name"]),
                    artist_name=str(item["artist_name"]),
                    reason_facts=_build_reason_facts(str(item["name"]), str(item["artist_name"])),
                    reason=str(item.get("reason") or "지금 분위기에 맞게 골라본 곡이에요."),
                    spotify_url=_build_spotify_search_url(str(item["name"]), str(item["artist_name"])),
                )
            )
            continue

        resolved.append(
            TrackSummary(
                track_id=f"fallback-{mood}-{index + 1}",
                name=str(item["name"]),
                artist_name=str(item["artist_name"]),
                reason_facts=_build_reason_facts(str(item["name"]), str(item["artist_name"])),
                reason=str(item.get("reason") or "지금 분위기에 맞게 골라본 곡이에요."),
                spotify_url=_build_spotify_search_url(str(item["name"]), str(item["artist_name"])),
            )
        )
        if len(resolved) >= limit and not cover_first:
            break

    if cover_first and len(resolved) < limit:
        resolved.extend(unresolved[: limit - len(resolved)])
    return validate_hard_constraints(resolved[:limit], context_text)


def recommend_tracks(
    mood: str,
    access_token: str | None = None,
    limit: int = 6,
    context_text: str | None = None,
    selection_guidance: dict[str, Any] | None = None,
) -> list[TrackSummary]:
    normalized_mood = _normalize_mood(mood)
    constraints = extract_hard_constraints(context_text)
    profile = MOOD_PROFILES.get(normalized_mood, MOOD_PROFILES["calm"])
    mood_label = str(profile["label"])

    if constraints["instrumental_required"]:
        # Spotify search/recommendation responses expose no verified vocals field.
        # Stay within the tagged catalog rather than returning an unverified track.
        return _fallback_tracks(
            normalized_mood,
            access_token=access_token or _get_app_access_token(),
            context_text=context_text,
            limit=limit,
            selection_guidance=selection_guidance,
        )

    if not access_token:
        return _fallback_tracks(normalized_mood, access_token=None, context_text=context_text, limit=limit, selection_guidance=selection_guidance)

    try:
        has_explicit_genre_request = _has_explicit_genre_request(context_text)
        available_genres = _fetch_available_genres(access_token)
        seed_genres = _pick_seed_genres(normalized_mood, available_genres, context_text=context_text)
        context_genres, context_params = _merge_context_audio_hints(context_text)
        if selection_guidance and not has_explicit_genre_request:
            context_params.update(selection_guidance.get("audio_hints") or {})
        query: dict[str, object] = {
            "limit": limit,
            "seed_genres": ",".join(seed_genres),
        }
        query.update(profile["params"])  # type: ignore[arg-type]
        query.update(context_params)

        curated_tracks: list[TrackSummary] = []
        seen_pairs: set[tuple[str, str]] = set()
        contextual_search_terms = _build_contextual_search_terms(context_text)

        for term in contextual_search_terms:
            if not term.strip():
                continue
            for track in _search_tracks_by_query(
                access_token,
                term.strip(),
                reason=f"입력한 분위기와 이어지는 '{term.strip()}' 검색 결과예요.",
                mood_label=mood_label,
                seed_genres=seed_genres,
                limit=2,
            ):
                key = (track.name, track.artist_name)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                curated_tracks.append(track)
                if len(curated_tracks) >= limit:
                    return curated_tracks[:limit]

        if len(curated_tracks) >= limit:
            return curated_tracks[:limit]

        response = _spotify_request(SPOTIFY_RECOMMENDATIONS_URL, access_token, params=query)
        tracks = response.get("tracks") or []
        mapped_tracks = [_map_track(track, mood_label, seed_genres) for track in tracks if isinstance(track, dict)]
        if mapped_tracks:
            unique_tracks: list[TrackSummary] = list(curated_tracks)
            for track in mapped_tracks:
                key = (track.name, track.artist_name)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                unique_tracks.append(track)
            if len(unique_tracks) < limit and context_genres:
                # Spotify 결과가 적으면 컨텍스트 기반 fallback으로 빈 칸을 채운다.
                filler_tracks = _fallback_tracks(
                    normalized_mood,
                    access_token=access_token,
                    context_text=context_text,
                    limit=limit,
                    selection_guidance=selection_guidance,
                )
                for filler in filler_tracks:
                    key = (filler.name, filler.artist_name)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    unique_tracks.append(filler)
                    if len(unique_tracks) >= limit:
                        break
            return unique_tracks[:limit]
    except SpotifyRecommendationError:
        return _fallback_tracks(normalized_mood, access_token=access_token, context_text=context_text, limit=limit, selection_guidance=selection_guidance)
    except Exception:
        return _fallback_tracks(normalized_mood, access_token=access_token, context_text=context_text, limit=limit, selection_guidance=selection_guidance)

    return _fallback_tracks(normalized_mood, access_token=access_token, context_text=context_text, limit=limit, selection_guidance=selection_guidance)
