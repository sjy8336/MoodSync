from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import time
from datetime import datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.schemas.track import TrackSummary
from app.services.mbti_aesthetics import detect_mbti_aesthetic


logger = logging.getLogger(__name__)


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

INSTRUMENT_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("피아노", "piano", "keys", "keyboard"), "piano"),
    (("색소폰", "saxophone", "sax"), "saxophone"),
    (("기타", "guitar"), "guitar"),
    (("트럼펫", "trumpet"), "trumpet"),
    (("바이올린", "violin"), "violin"),
)

GENRE_FAMILY_HINTS: list[tuple[tuple[str, ...], str, list[str], dict[str, object]]] = [
    (("rnb", "r&b", "알앤비"), "R&B", ["r&b", "r-n-b", "soul", "neo-soul"], {"target_valence": 0.5, "target_energy": 0.58}),
    (("neo soul", "neo-soul", "네오소울"), "네오소울", ["neo-soul", "r&b", "soul"], {"target_valence": 0.52, "target_energy": 0.46}),
    (("soul", "소울", "gospel", "가스펠"), "소울", ["soul", "gospel", "r&b"], {"target_valence": 0.54, "target_energy": 0.5}),
    (("funk", "펑키", "groove", "groovy"), "펑키", ["funk", "disco", "dance"], {"target_energy": 0.76, "target_danceability": 0.82}),
    (("disco", "디스코"), "디스코", ["disco", "funk", "dance"], {"target_energy": 0.8, "target_danceability": 0.86}),
    (("punk rock", "펑크락", "펑크"), "펑크락", ["punk", "rock", "alternative", "hard-rock"], {"target_energy": 0.88, "target_danceability": 0.7}),
    (("pop", "팝"), "팝", ["pop", "dance-pop", "synth-pop"], {"target_energy": 0.68, "target_danceability": 0.72}),
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

# Spotify may return romanized artist names for Korean catalog entries.
_SPOTIFY_ARTIST_ALIASES: dict[tuple[str, str], tuple[str, ...]] = {
    ("여행을 떠나요", "조용필"): ("Cho Yong Pil",),
    ("해변의 여인", "COOL"): ("Cool",),
    ("아모르 파티", "김연자"): ("Kim Yon Ja", "Kim Yeon Ja"),
    ("붉은 노을", "이문세"): ("Lee Moon Sae",),
    ("강남스타일", "싸이"): ("PSY",),
    ("챔피언", "싸이"): ("PSY",),
    ("롤린 (Rollin')", "브레이브걸스"): ("Brave Girls",),
    ("바래", "FTISLAND"): ("FT Island", "FTIsland"),
    ("거울", "국카스텐"): ("Guckkasten",),
    ("낭만고양이", "체리필터"): ("Cherry Filter",),
    ("일탈", "자우림"): ("Jaurim",),
    ("겁쟁이", "버즈"): ("Buzz",),
    ("나는 나비", "YB"): ("YB",),
    ("박하사탕", "YB"): ("YB",),
    ("하하하쏭", "자우림"): ("Jaurim",),
    ("오리 날다", "체리필터"): ("Cherry Filter",),
    ("말달리자", "크라잉넛"): ("Crying Nut",),
}

# Spotify can return romanized or translated Korean titles even when the
# catalog entry was requested with its Korean display title.
_SPOTIFY_TRACK_ALIASES: dict[tuple[str, str], tuple[str, ...]] = {
    ("강남스타일", "싸이"): ("Gangnam Style",),
    ("아모르 파티", "김연자"): ("아모르파티", "Amor Fati"),
    ("붉은 노을", "이문세"): ("Sunset Glow",),
    ("붉은 노을", "BIGBANG"): ("Sunset Glow",),
    ("바래", "FTISLAND"): ("Barae",),
    ("거울", "국카스텐"): ("Mirror",),
    ("낭만고양이", "체리필터"): ("Romantic Cat",),
    ("일탈", "자우림"): ("Illusion",),
    ("겁쟁이", "버즈"): ("Coward",),
    ("나는 나비", "YB"): ("Butterfly",),
    ("박하사탕", "YB"): ("Peppermint Candy",),
    ("하하하쏭", "자우림"): ("Hahaha Song",),
    ("오리 날다", "체리필터"): ("Flying Duck",),
    ("말달리자", "크라잉넛"): ("March",),
}


def _spotify_search_title(name: str, artist_name: str) -> str:
    """Use aliases only for enrichment; the curated title remains the UI title."""
    aliases = _SPOTIFY_TRACK_ALIASES.get((name, artist_name), ())
    return str(aliases[0]) if aliases else name


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
                "cross_generation_fit": int(candidate.get("cross_generation_fit") or 0),
                "release_year": int(candidate.get("release_year") or 0),
                "instrument_source": candidate.get("instrument_source"),
                "instruments": [
                    tag for tag in ("piano", "saxophone", "guitar", "trumpet", "violin")
                    if tag in {str(value).lower() for value in candidate.get("tags", []) if value}
                ],
            }
    return {}


def extract_hard_constraints(context_text: str | None) -> dict[str, bool]:
    """Return only requirements that must be enforced before ranking tracks."""
    lowered = (context_text or "").lower()
    return {"instrumental_required": any(term in lowered for term in INSTRUMENTAL_REQUEST_TERMS)}


def extract_instrument_preferences(context_text: str | None) -> dict[str, object]:
    """Extract only explicitly named instruments; unknown instruments stay unknown."""
    text = context_text or ""
    lowered = text.lower()
    instruments: list[str] = []
    for aliases, instrument in INSTRUMENT_HINTS:
        if any(alias in (lowered if alias.isascii() else text) for alias in aliases):
            instruments.append(instrument)
    strong = len(instruments) >= 2 or any(marker in text for marker in ("들어간", "중심", "함께"))
    return {
        "instruments": list(dict.fromkeys(instruments)),
        "relation": "all_preferred" if len(instruments) >= 2 else "single_preference",
        "strength": "strong" if strong and instruments else "soft" if instruments else None,
    }


def _is_sleep_request(context_text: str | None) -> bool:
    lowered = (context_text or "").lower()
    return any(term in lowered for term in SLEEP_REQUEST_TERMS)


def _is_long_focus_request(context_text: str | None) -> bool:
    text = context_text or ""
    lowered = text.lower()
    has_long_session = any(token in text or token in lowered for token in ("오래 앉", "오랫동안", "장시간", "long session"))
    has_focus_goal = any(token in text or token in lowered for token in ("몰입", "집중", "산만하지", "노트북 앞"))
    return has_long_session and has_focus_goal


def _is_dream_pop_synth_request(context_text: str | None) -> bool:
    """Recognize explicit sound requests without treating immersion as study."""
    text = context_text or ""
    lowered = text.lower()
    wants_dream_pop = any(token in lowered or token in text for token in ("dream pop", "dream-pop", "드림 팝", "드림팝"))
    wants_synth_or_space = any(
        token in lowered or token in text
        for token in ("synth", "신스", "공간감", "공간 감", "atmospheric", "atmosphere", "spatial", "immersive", "몰입감")
    )
    return wants_dream_pop and wants_synth_or_space


def _is_calm_jazz_instrument_request(context_text: str | None) -> bool:
    explicit_genres, genre_labels, _ = _extract_genre_family_matches(context_text)
    preferences = extract_instrument_preferences(context_text)
    return "jazz" in explicit_genres and bool(preferences.get("instruments")) and any(
        token in (context_text or "") for token in ("자극", "차분", "지쳐", "피곤", "천천히", "긴장")
    )


def _requests_unhurried_flow(context_text: str | None) -> bool:
    text = context_text or ""
    return any(token in text.lower() for token in ("천천히", "느긋", "서두르지", "여유 있는", "자극적이지"))


def _is_dawn_sentimental_request(context_text: str | None) -> bool:
    """Recognize a late-night listening aesthetic without treating it as sleep."""
    text = context_text or ""
    lowered = text.lower()
    has_time_or_mood_cue = any(token in text or token in lowered for token in ("새벽", "늦은 밤", "밤공기", "센치"))
    has_aesthetic_cue = any(token in text or token in lowered for token in ("몽환", "감성", "센치", "플레이리스트"))
    return has_time_or_mood_cue and has_aesthetic_cue and not _is_sleep_request(context_text)


def _sleep_ranking_factors(tags: list[object], moods: list[object]) -> list[str]:
    """Expose the verified catalog facts that made a track suitable for rest."""
    tag_set = {str(tag).lower() for tag in tags if tag}
    mood_set = {str(mood).lower() for mood in moods if mood}
    factors: list[str] = []
    if "ambient" in tag_set:
        factors.append("앰비언트")
    if {"classical", "piano"}.issubset(tag_set):
        factors.append("클래식 피아노 연주")
    elif "piano" in tag_set:
        factors.append("피아노 연주")
    if "calm" in mood_set or "calm" in tag_set:
        factors.append("차분한 분위기")
    if "dreamy" in tag_set:
        factors.append("몽환적인 분위기")
    if {"jazz", "standard"}.issubset(tag_set) and "calm" in mood_set:
        factors.append("차분한 재즈 연주")
    return factors


def is_verified_instrumental(track: TrackSummary) -> bool:
    facts = track.reason_facts or {}
    tags = facts.get("tags") if isinstance(facts, dict) else []
    return isinstance(tags, list) and "instrumental" in {str(tag).lower() for tag in tags}


def validate_hard_constraints(
    tracks: list[TrackSummary],
    context_text: str | None,
) -> list[TrackSummary]:
    """Discard unknown candidates rather than guessing that they meet a hard request."""
    tracks = [track for track in tracks if _has_valid_track_identity(track)]
    constraints = extract_hard_constraints(context_text)
    if constraints["instrumental_required"]:
        return [track for track in tracks if is_verified_instrumental(track)]
    return tracks


def _has_valid_track_identity(track: TrackSummary) -> bool:
    """Reject placeholder-like titles before they reach ranking or the UI."""
    title = (track.display_title or track.name or "").strip().lower()
    if not title or title in {"unknown", "untitled", "null", "none"}:
        return False
    if "____" in title or "unknown track" in title:
        return False
    if not (track.track_id or "").strip() or not (track.artist_name or "").strip():
        return False
    if track.recording_match_confidence is not None and track.recording_match_confidence < 0.7:
        return False
    return True


def _build_reason_facts(name: str, artist_name: str, seed_genres: list[str] | None = None) -> dict[str, object]:
    facts = _catalog_metadata_for_track(name, artist_name)
    if facts.get("tags") or facts.get("moods"):
        facts["feature_provenance"] = {
            "tags": "curated_catalog_metadata",
            "moods": "curated_catalog_metadata",
            "origin_kr": "curated_artist_identity_metadata",
            "artist_band": "curated_artist_identity_metadata",
        }
    if facts.get("instrument_source"):
        facts.setdefault("feature_provenance", {})["instruments"] = facts["instrument_source"]
    sound_hint = TRACK_SOUND_HINTS.get((name.strip().lower(), artist_name.strip().lower()))
    if sound_hint:
        facts["sound_profile"] = sound_hint[0]
        facts["listening_effect"] = sound_hint[1]
    if seed_genres:
        facts["selection_seed_genres"] = list(seed_genres)
    return facts


def _focus_feature_role_compatibility(tags: set[str], moods: set[str]) -> float:
    """Estimate long-session focus compatibility from verified catalog facts."""
    score = 0.5
    if tags & {"calm", "soft", "ambient", "relaxed"} or "calm" in moods:
        score += 0.18
    if "instrumental" in tags:
        score += 0.12
    if tags & {"groove", "rhythmic_light", "bossa-nova"}:
        score += 0.06
    if tags & {"prominent_vocal", "high_energy", "driving", "aggressive", "busy", "dense"}:
        score -= 0.2
    if tags & {"fast", "rhythmic_strong", "bebop", "hard-bop", "fusion", "swing", "big-band", "dynamic_build"}:
        score -= 0.18
    return max(0.0, min(1.0, round(score, 2)))


def _build_contextual_reason_facts(name: str, artist_name: str, context_text: str | None) -> dict[str, object]:
    facts = _build_reason_facts(name, artist_name)
    if _is_sleep_request(context_text):
        factors = _sleep_ranking_factors(
            list(facts.get("tags") or []),
            list(facts.get("moods") or []),
        )
        if factors:
            facts["sleep_ranking_factors"] = factors
    if _is_calm_jazz_instrument_request(context_text):
        tags = {str(tag).lower() for tag in facts.get("tags", []) if tag}
        facts["rhythmic_intensity"] = (
            "high" if tags & {"rhythmic_strong", "hard-bop", "bebop", "fusion", "swing", "big-band", "odd_meter"}
            else "moderate" if tags & {"rhythmic_light", "groove", "bossa-nova"}
            else "low"
        )
        facts["low_stimulation_fit"] = bool(tags & {"low_stimulation", "relaxed", "subdued"}) and facts["rhythmic_intensity"] != "high"
        facts["relaxed_fit"] = bool("relaxed" in tags or "low_stimulation" in tags)
        facts["relaxed_flow_fit"] = facts["relaxed_fit"] and facts["rhythmic_intensity"] != "high"
        facts["calm_fit"] = bool("calm" in {str(mood).lower() for mood in facts.get("moods", []) if mood} or "calm" in tags)
        facts["jazz_ranking_factors"] = [
            label
            for label, present in (
                ("jazz", "jazz" in tags),
                ("requested_instruments_catalog_match", {"piano", "saxophone"}.issubset(tags)),
                ("low_stimulation", "low_stimulation" in tags),
                ("relaxed_flow", "relaxed" in tags),
                ("rhythmic_strong_penalty", bool(tags & {"rhythmic_strong", "hard-bop", "fusion", "swing"})),
            )
            if present
        ]
    if _is_drive_request(context_text) and not _is_family_trip_request(context_text):
        tags = {str(tag).lower() for tag in facts.get("tags", []) if tag}
        facts["drive_fit"] = bool(tags & {"driving", "upbeat", "high_energy", "rock", "punk", "pop-punk", "pop"})
        facts["energy_fit"] = bool(tags & {"upbeat", "high_energy", "driving"})
        facts["pop_fit"] = bool(tags & {"pop", "dance-pop", "synth-pop", "pop-punk"})
        facts["punk_fit"] = bool(tags & {"punk", "pop-punk"})
        facts["pop_punk_bridge"] = "pop-punk" in tags
        facts["singalong_fit"] = bool(tags & {"mainstream", "broad_familiarity_ko", "family_trip"})
        facts["drive_ranking_factors"] = [
            key for key, present in (
                ("drive", facts["drive_fit"]),
                ("energy", facts["energy_fit"]),
                ("pop", facts["pop_fit"]),
                ("punk", facts["punk_fit"]),
                ("singalong_proxy", facts["singalong_fit"]),
            ) if present
        ]
    if _is_dream_pop_synth_request(context_text):
        tags = {str(tag).lower() for tag in facts.get("tags", []) if tag}
        facts["dream_pop_fit"] = "dream-pop" in tags
        facts["synth_fit"] = bool(tags & {"synth", "synth-pop"})
        facts["atmospheric_fit"] = "atmospheric" in tags
        facts["spatial_fit"] = "spacious" in tags
        facts["immersive_fit"] = "immersive" in tags
        facts["dreamy_fit"] = "dreamy" in tags
        facts["intensity"] = "moderate" if tags & {"immersive", "synth", "electronic", "synth-pop"} else "low"
        facts["dream_pop_ranking_factors"] = [
            key
            for key, present in (
                ("dream_pop", facts["dream_pop_fit"]),
                ("synth", facts["synth_fit"]),
                ("atmospheric", facts["atmospheric_fit"]),
                ("spatial", facts["spatial_fit"]),
                ("immersive", facts["immersive_fit"]),
                ("dreamy", facts["dreamy_fit"]),
            )
            if present
        ]
    if _is_long_focus_request(context_text):
        tags = {str(tag).lower() for tag in facts.get("tags", []) if tag}
        moods = {str(mood).lower() for mood in facts.get("moods", []) if mood}
        facts["feature_role_compatibility"] = _focus_feature_role_compatibility(tags, moods)
        facts["low_stimulation_fit"] = bool(
            tags & {"calm", "soft", "ambient", "relaxed"} or "calm" in moods
        ) and not bool(tags & {"prominent_vocal", "high_energy", "busy", "dense", "rhythmic_strong"})
        facts["sustained_focus_fit"] = bool(tags & {"focused", "calm", "soft", "ambient", "instrumental"} or moods & {"focused", "calm"})
        facts["long_session_fit"] = facts["sustained_focus_fit"] and facts["feature_role_compatibility"] >= 0.5
        facts["mellow_fit"] = bool(tags & {"calm", "soft", "ambient", "relaxed", "dreamy"} or "calm" in moods)
        facts["calm_fit"] = bool("calm" in tags or "calm" in moods)
        facts["relaxed_flow_fit"] = bool(tags & {"relaxed", "calm", "soft", "ambient"})
        facts["light_rhythm_fit"] = bool(tags & {"groove", "rhythmic", "rhythmic_light", "bossa-nova"})
        facts["distraction_risk"] = (
            "high"
            if tags & {"high_energy", "driving", "busy", "dense", "prominent_vocal", "rhythmic_strong", "bebop", "fast"}
            else "low" if facts["low_stimulation_fit"] else "unknown"
        )
        facts["focus_ranking_factors"] = [
            key for key, present in (
                ("low_stimulation", facts["low_stimulation_fit"]),
                ("sustained_focus", facts["sustained_focus_fit"]),
                ("calm", facts["calm_fit"]),
                ("light_rhythm", facts["light_rhythm_fit"]),
                ("distraction_risk", facts["distraction_risk"] == "low"),
            ) if present
        ]
    return facts


def _attach_spotify_recording_facts(facts: dict[str, object], track: TrackSummary) -> dict[str, object]:
    """Keep catalog tags useful for ranking without presenting them as recording facts."""
    enriched = dict(facts)
    enriched["recording_identity_source"] = "spotify_title_artist_match"
    enriched["instrumentation_verification"] = "unknown"
    enriched["recording_instruments"] = []
    enriched.setdefault("feature_provenance", {})["instruments"] = "not_available_from_spotify_track_response"
    if track.spotify_track_name and track.album_name:
        enriched["canonical_recording_identity"] = f"{track.spotify_track_name} — {track.artist_name} — {track.album_name}"
    return enriched


def _build_candidate_reason_facts(
    item: dict[str, object],
    context_text: str | None,
    mood: str,
    recent_track_keys: set[str] | None = None,
) -> dict[str, object]:
    facts = _build_contextual_reason_facts(str(item["name"]), str(item["artist_name"]), context_text)
    facts["final_ranking_score"] = _score_fallback_candidate(item, mood, context_text, recent_track_keys)
    if item.get("selection_category"):
        facts["selection_category"] = item["selection_category"]
    return facts


def _is_korean_band_rock_track(track: TrackSummary) -> bool:
    tags = track.reason_facts.get("tags", []) if isinstance(track.reason_facts, dict) else []
    return {"origin_kr", "artist_band", "rock"}.issubset({str(tag).lower() for tag in tags if tag})


def _enforce_korean_band_rock_selection(
    tracks: list[TrackSummary], context_text: str | None, limit: int
) -> list[TrackSummary]:
    """Keep foreign tracks out when a strong Korean-band-rock pool is available."""
    if _korean_band_rock_preference_strength(context_text) not in {"hard", "strong"}:
        return tracks[:limit]
    exact = [track for track in tracks if _is_korean_band_rock_track(track)]
    if len(exact) >= limit:
        return exact[:limit]
    # Preserve the preference as far as the verified response allows. A
    # non-exact fallback is only retained when the exact pool is genuinely short.
    remainder = [track for track in tracks if track not in exact]
    return (exact + remainder)[:limit]


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
    {"name": "Blinding Lights", "artist_name": "The Weeknd", "moods": ["anxious", "excited", "focused", "happy"], "tags": ["pop", "driving", "high_energy", "global_only"], "generation": "recent", "release_year": 2019, "cross_generation_fit": 1},
    {"name": "Don't Start Now", "artist_name": "Dua Lipa", "moods": ["anxious", "excited", "happy"], "tags": ["pop", "upbeat", "high_energy", "global_only"], "generation": "recent"},
    {"name": "Levitating", "artist_name": "Dua Lipa", "moods": ["excited", "happy"], "tags": ["pop", "upbeat", "dance", "global_only"], "generation": "recent", "release_year": 2020, "cross_generation_fit": 1},
    {"name": "HUMBLE.", "artist_name": "Kendrick Lamar", "moods": ["anxious", "angry", "focused"], "tags": ["driving", "rhythmic"]},
    {"name": "Lose Yourself", "artist_name": "Eminem", "moods": ["anxious", "focused", "angry"], "tags": ["driving", "focused"]},
    {"name": "Bad Habit", "artist_name": "Steve Lacy", "moods": ["lonely", "sad", "focused"], "tags": ["rnb", "groove"]},
    {"name": "Luv (sic) Part 3", "artist_name": "Nujabes", "moods": ["lonely", "sad", "focused"], "tags": ["emotional", "hip-hop"]},
    {"name": "Take Five", "artist_name": "The Dave Brubeck Quartet", "moods": ["focused", "calm"], "tags": ["jazz", "instrumental", "standard", "piano", "saxophone", "rhythmic_strong", "odd_meter"], "instrument_source": "curated_catalog_metadata"},
    {"name": "So What", "artist_name": "Miles Davis", "moods": ["focused", "calm"], "tags": ["jazz", "instrumental", "standard", "modal", "piano", "saxophone", "relaxed", "rhythmic_light", "groove"], "instrument_source": "curated_catalog_metadata"},
    {"name": "Blue in Green", "artist_name": "Miles Davis", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "instrumental", "standard", "modal", "piano", "saxophone", "low_stimulation", "relaxed"], "instrument_source": "curated_catalog_metadata"},
    {"name": "Autumn Leaves", "artist_name": "Chet Baker", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "vocal-jazz", "standard"]},
    {"name": "My Favorite Things", "artist_name": "John Coltrane", "moods": ["focused", "calm"], "tags": ["jazz", "instrumental", "standard", "piano", "saxophone", "relaxed", "rhythmic_strong"], "instrument_source": "curated_catalog_metadata"},
    {"name": "Round Midnight", "artist_name": "Thelonious Monk", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "instrumental", "standard", "piano", "saxophone", "low_stimulation", "relaxed"], "instrument_source": "curated_catalog_metadata"},
    {"name": "Naima", "artist_name": "John Coltrane", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "instrumental", "standard", "piano", "saxophone", "low_stimulation", "relaxed"], "instrument_source": "curated_catalog_metadata"},
    {"name": "In a Sentimental Mood", "artist_name": "John Coltrane & Duke Ellington", "moods": ["focused", "calm", "sad"], "tags": ["jazz", "instrumental", "standard", "piano", "saxophone", "low_stimulation", "relaxed"], "instrument_source": "curated_catalog_metadata"},
    {"name": "Sing, Sing, Sing", "artist_name": "Benny Goodman", "moods": ["excited", "focused", "happy"], "tags": ["jazz", "swing", "big-band", "instrumental"]},
    {"name": "Take the A Train", "artist_name": "Duke Ellington", "moods": ["happy", "focused", "calm"], "tags": ["jazz", "swing", "standard", "big-band"]},
    {"name": "It Don't Mean a Thing", "artist_name": "Duke Ellington", "moods": ["happy", "excited", "focused"], "tags": ["jazz", "swing", "standard", "big-band"]},
    {"name": "Donna Lee", "artist_name": "Charlie Parker", "moods": ["focused", "excited", "angry"], "tags": ["jazz", "bebop", "instrumental", "rhythmic_strong", "busy"]},
    {"name": "Moanin'", "artist_name": "Art Blakey & The Jazz Messengers", "moods": ["focused", "calm"], "tags": ["jazz", "hard-bop", "instrumental", "piano", "saxophone", "rhythmic_strong"], "instrument_source": "curated_catalog_metadata"},
    {"name": "Blue Bossa", "artist_name": "Joe Henderson", "moods": ["calm", "focused", "sad"], "tags": ["jazz", "bossa-nova", "latin", "instrumental", "piano", "saxophone", "low_stimulation", "relaxed"], "instrument_source": "curated_catalog_metadata"},
    {"name": "The Girl from Ipanema", "artist_name": "Stan Getz & João Gilberto", "moods": ["calm", "happy", "focused"], "tags": ["bossa-nova", "latin", "acoustic", "vocal-jazz", "prominent_vocal"]},
    {"name": "Birdland", "artist_name": "Weather Report", "moods": ["excited", "focused", "happy"], "tags": ["jazz", "fusion", "instrumental"]},
    {"name": "Spain", "artist_name": "Chick Corea", "moods": ["excited", "focused", "happy"], "tags": ["jazz", "fusion", "instrumental"]},
    {"name": "Cantaloupe Island", "artist_name": "Herbie Hancock", "moods": ["focused", "happy", "calm"], "tags": ["jazz", "fusion", "instrumental"]},
    {"name": "Sunset Lover", "artist_name": "Petit Biscuit", "moods": ["calm", "sad", "lonely"], "tags": ["calm", "dreamy"]},
    {"name": "Holocene", "artist_name": "Bon Iver", "moods": ["calm", "sad", "lonely"], "tags": ["calm", "dreamy"]},
    {"name": "Someone Like You", "artist_name": "Adele", "moods": ["sad", "lonely"], "tags": ["emotional", "soft"]},
    {"name": "Fix You", "artist_name": "Coldplay", "moods": ["sad", "anxious"], "tags": ["soft", "emotional"]},
    {"name": "To Build a Home", "artist_name": "The Cinematic Orchestra", "moods": ["sad", "lonely"], "tags": ["soft", "dreamy"]},
    {"name": "Love Poem", "artist_name": "IU", "moods": ["sad", "lonely", "anxious"], "tags": ["korean", "soft", "emotional", "comfort"]},
    {"name": "Through the Night", "artist_name": "IU", "moods": ["sad", "lonely", "anxious", "calm"], "tags": ["korean", "soft", "calm", "comfort", "prominent_vocal"]},
    {"name": "Best Part", "artist_name": "Daniel Caesar feat. H.E.R.", "moods": ["sad", "lonely", "anxious", "calm"], "tags": ["rnb", "soul", "soft", "warm", "love", "prominent_vocal"]},
    {"name": "Like I'm Gonna Lose You", "artist_name": "Meghan Trainor feat. John Legend", "moods": ["sad", "lonely", "anxious"], "tags": ["pop", "soft", "emotional", "warm", "love"]},
    {"name": "Ditto", "artist_name": "NewJeans", "moods": ["lonely", "calm", "anxious"], "tags": ["korean", "dreamy"]},
    {"name": "Hype Boy", "artist_name": "NewJeans", "moods": ["excited", "happy", "focused"], "tags": ["korean", "upbeat"]},
    {"name": "Super Shy", "artist_name": "NewJeans", "moods": ["excited", "anxious", "focused"], "tags": ["korean", "high_energy"]},
    {"name": "Love Dive", "artist_name": "IVE", "moods": ["happy", "excited"], "tags": ["korean", "upbeat"]},
    {"name": "Dynamite", "artist_name": "BTS", "moods": ["happy", "excited", "anxious"], "tags": ["korean", "high_energy", "mainstream", "family_trip", "summer"], "generation": "recent", "release_year": 2020, "cross_generation_fit": 4},
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
    {"name": "Brave Shine", "artist_name": "Aimer", "moods": ["sad", "focused", "calm"], "tags": ["jpop", "anime", "emotional", "prominent_vocal"], "reason": "애니 OST의 드라마틱한 결을 부드럽게 담아내는 곡이에요."},
    {"name": "Into The Night", "artist_name": "YOASOBI", "moods": ["calm", "focused"], "tags": ["jpop", "emotional", "dreamy", "prominent_vocal"], "reason": "제이팝의 선명한 보컬 중심 흐름을 느끼기 좋아요."},
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
    {"name": "An Ending (Ascent)", "artist_name": "Brian Eno", "moods": ["calm", "lonely"], "tags": ["ambient", "electronic", "synth", "instrumental", "dreamy", "atmospheric", "spacious", "immersive"], "reason": "앰비언트 특유의 넓은 공간감이 생각을 천천히 가라앉혀줘요."},
    {"name": "One More Time", "artist_name": "Daft Punk", "moods": ["happy", "excited"], "tags": ["house", "dance", "electronic"], "reason": "하우스/댄스 결을 직관적으로 느끼기 좋은 곡이에요."},
    {"name": "When The Sun Hits", "artist_name": "Slowdive", "moods": ["sad", "dreamy", "calm"], "tags": ["shoegaze", "dream-pop", "dreamy"], "reason": "슈게이즈 특유의 물결 같은 질감이 몽환적인 분위기를 잘 만들어줘요."},
    {"name": "Space Song", "artist_name": "Beach House", "moods": ["calm", "dreamy", "sad"], "tags": ["dream-pop", "dreamy", "atmospheric", "spacious", "immersive"]},
    {"name": "Myth", "artist_name": "Beach House", "moods": ["calm", "dreamy", "emotional"], "tags": ["dream-pop", "dreamy", "atmospheric", "immersive"]},
    {"name": "Heaven or Las Vegas", "artist_name": "Cocteau Twins", "moods": ["dreamy", "excited", "calm"], "tags": ["dream-pop", "dreamy", "atmospheric", "spacious"]},
    {"name": "Midnight City", "artist_name": "M83", "moods": ["dreamy", "excited", "calm"], "tags": ["synth-pop", "electronic", "synth", "atmospheric", "spacious", "immersive"]},
    {"name": "Oblivion", "artist_name": "Grimes", "moods": ["dreamy", "excited", "emotional"], "tags": ["synth-pop", "electronic", "synth", "dreamy", "immersive"]},
    {"name": "Rhubarb", "artist_name": "Aphex Twin", "moods": ["calm", "lonely"], "tags": ["ambient", "electronic", "instrumental"], "reason": "차분한 전자음의 결이 앰비언트 요청에 잘 맞아요."},
    {"name": "Comptine d'un autre été: L'après-midi", "artist_name": "Yann Tiersen", "moods": ["calm", "lonely"], "tags": ["classical", "piano", "instrumental", "soft", "emotional"]},
    {"name": "Nuvole Bianche", "artist_name": "Ludovico Einaudi", "moods": ["calm", "sad"], "tags": ["classical", "piano", "instrumental", "soft", "emotional"]},
    {"name": "Una Mattina", "artist_name": "Ludovico Einaudi", "moods": ["calm", "lonely"], "tags": ["classical", "piano", "instrumental", "soft"]},
    {"name": "Kiss The Rain", "artist_name": "Yiruma", "moods": ["calm", "sad"], "tags": ["classical", "piano", "instrumental", "soft", "emotional"]},
    {"name": "River Flows In You", "artist_name": "Yiruma", "moods": ["calm", "sad"], "tags": ["classical", "piano", "instrumental", "soft", "emotional"]},
    {"name": "1/1", "artist_name": "Brian Eno", "moods": ["calm", "lonely"], "tags": ["ambient", "instrumental", "dreamy"]},
    {"name": "Avril 14th", "artist_name": "Aphex Twin", "moods": ["calm", "lonely"], "tags": ["piano", "instrumental", "dreamy", "soft"]},
    {"name": "Near Light", "artist_name": "Ólafur Arnalds", "moods": ["calm", "sad"], "tags": ["classical", "ambient", "instrumental", "emotional"]},
    {"name": "I Like Me Better", "artist_name": "Lauv", "moods": ["happy", "lonely"], "tags": ["soft", "upbeat"]},
    {"name": "Permission to Dance", "artist_name": "BTS", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "family_trip", "summer"], "generation": "recent", "release_year": 2021, "cross_generation_fit": 3},
    {"name": "The Nights", "artist_name": "Avicii", "moods": ["happy", "excited", "anxious"], "tags": ["high_energy", "upbeat", "mainstream", "family_trip", "summer"], "generation": "bridge", "release_year": 2014, "cross_generation_fit": 2},
    # Editorially curated for Korean family-trip familiarity. This is kept
    # separate from Spotify popularity, which is global and time-sensitive.
    {"name": "여행을 떠나요", "artist_name": "조용필", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip", "summer"], "generation": "legacy", "release_year": 1985, "cross_generation_fit": 2},
    {"name": "해변의 여인", "artist_name": "COOL", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip", "summer"], "generation": "legacy", "release_year": 1997, "cross_generation_fit": 2},
    {"name": "아모르 파티", "artist_name": "김연자", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip"], "generation": "bridge", "release_year": 2013, "cross_generation_fit": 3},
    {"name": "붉은 노을", "artist_name": "이문세", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip"], "generation": "legacy", "release_year": 1988, "cross_generation_fit": 2},
    {"name": "강남스타일", "artist_name": "싸이", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip", "summer"], "generation": "bridge", "release_year": 2012, "cross_generation_fit": 5},
    {"name": "챔피언", "artist_name": "싸이", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip"], "generation": "bridge", "release_year": 2002, "cross_generation_fit": 3},
    {"name": "빨간 맛", "artist_name": "Red Velvet", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "family_trip", "summer"], "generation": "bridge", "release_year": 2017, "cross_generation_fit": 3},
    {"name": "롤린 (Rollin')", "artist_name": "브레이브걸스", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "youth_skewed"], "generation": "recent", "release_year": 2017, "cross_generation_fit": 1},
    {"name": "아주 NICE", "artist_name": "SEVENTEEN", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "youth_skewed"], "generation": "recent", "release_year": 2016, "cross_generation_fit": 1},
    {"name": "붉은 노을", "artist_name": "BIGBANG", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip"], "generation": "bridge", "release_year": 2008, "cross_generation_fit": 4},
    {"name": "좋은 날", "artist_name": "아이유", "moods": ["happy", "excited"], "tags": ["korean", "upbeat", "mainstream", "broad_familiarity_ko", "family_trip"], "generation": "bridge", "release_year": 2010, "cross_generation_fit": 3},
    {"name": "나는 나비", "artist_name": "YB", "moods": ["happy", "excited", "angry"], "tags": ["korean", "origin_kr", "artist_band", "rock", "upbeat", "high_energy", "mainstream", "broad_familiarity_ko", "family_trip"], "generation": "bridge", "release_year": 2006, "cross_generation_fit": 4},
    {"name": "일탈", "artist_name": "자우림", "moods": ["angry", "excited", "happy"], "tags": ["korean", "origin_kr", "artist_band", "rock", "alternative", "upbeat", "high_energy"], "release_year": 1997},
    {"name": "낭만고양이", "artist_name": "체리필터", "moods": ["angry", "excited", "happy"], "tags": ["korean", "origin_kr", "artist_band", "rock", "punk", "upbeat", "high_energy"], "release_year": 2002},
    {"name": "거울", "artist_name": "국카스텐", "moods": ["angry", "excited", "focused"], "tags": ["korean", "origin_kr", "artist_band", "rock", "alternative", "high_energy"], "release_year": 2008},
    {"name": "바래", "artist_name": "FTISLAND", "moods": ["angry", "excited", "sad"], "tags": ["korean", "origin_kr", "artist_band", "rock", "pop-rock", "upbeat"], "release_year": 2009},
    {"name": "겁쟁이", "artist_name": "버즈", "moods": ["angry", "excited", "sad"], "tags": ["korean", "origin_kr", "artist_band", "rock", "pop-rock", "mainstream"], "release_year": 2005},
    {"name": "박하사탕", "artist_name": "YB", "moods": ["angry", "excited", "focused"], "tags": ["korean", "origin_kr", "artist_band", "rock", "alternative", "high_energy", "upbeat"], "release_year": 2001},
    {"name": "하하하쏭", "artist_name": "자우림", "moods": ["angry", "excited", "happy"], "tags": ["korean", "origin_kr", "artist_band", "rock", "alternative", "upbeat", "high_energy"], "release_year": 2004},
    {"name": "오리 날다", "artist_name": "체리필터", "moods": ["angry", "excited", "happy"], "tags": ["korean", "origin_kr", "artist_band", "rock", "punk", "upbeat", "high_energy"], "release_year": 2003},
    {"name": "말달리자", "artist_name": "크라잉넛", "moods": ["angry", "excited", "happy"], "tags": ["korean", "origin_kr", "artist_band", "rock", "punk", "upbeat", "high_energy"], "release_year": 1998},
    {"name": "Happy", "artist_name": "Pharrell Williams", "moods": ["happy", "excited"], "tags": ["upbeat", "mainstream", "family_trip", "summer"], "generation": "bridge", "release_year": 2013, "cross_generation_fit": 2},
    {"name": "Uptown Funk", "artist_name": "Mark Ronson feat. Bruno Mars", "moods": ["happy", "excited"], "tags": ["upbeat", "mainstream", "family_trip"], "generation": "bridge", "release_year": 2014, "cross_generation_fit": 2},
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
    except HTTPError as exc:
        logger.warning("Spotify app token request failed with HTTP %s", exc.code)
        return None
    except URLError as exc:
        logger.warning("Spotify app token request failed: %s", exc.reason)
        return None
    except (TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Spotify app token request failed: %s", type(exc).__name__)
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


def _is_family_trip_request(context_text: str | None) -> bool:
    text = context_text or ""
    return any(token in text for token in ("가족 여행", "가족여행", "가족")) and any(
        token in text for token in ("여행", "차", "자동차", "드라이브", "이동")
    )


def _current_season() -> str:
    month = datetime.now(ZoneInfo("Asia/Seoul")).month
    return "summer" if month in (6, 7, 8) else "spring" if month in (3, 4, 5) else "autumn" if month in (9, 10, 11) else "winter"


def _extract_genre_family_matches(context_text: str | None) -> tuple[list[str], list[str], dict[str, object]]:
    if not context_text or not isinstance(context_text, str):
        return [], [], {}

    lowered = context_text.lower()
    seed_genres: list[str] = []
    labels: list[str] = []
    params: dict[str, object] = {}
    is_pop_punk_compound = any(
        token in lowered or token in context_text
        for token in ("pop-punk", "pop punk", "팝펑크", "팝 펑크")
    )

    for keywords, label, genres, audio_params in GENRE_FAMILY_HINTS:
        # "팝과 펑크" means two requested genre axes. Only the explicit
        # compounds above should collapse into the pop-punk family.
        if is_pop_punk_compound and label in {"팝", "펑크락"}:
            continue
        if any((keyword in lowered if keyword.isascii() else keyword in context_text) for keyword in keywords):
            labels.append(label)
            seed_genres.extend(genres)
            params.update(audio_params)

    return list(dict.fromkeys(seed_genres)), list(dict.fromkeys(labels)), params


def _has_explicit_genre_request(context_text: str | None) -> bool:
    explicit_genres, genre_labels, _ = _extract_genre_family_matches(context_text)
    return bool(explicit_genres or genre_labels)


def build_selection_debug(context_text: str | None, tracks: list[TrackSummary]) -> dict[str, object]:
    """Expose request-isolation facts without carrying state between requests."""
    explicit_genres, genre_labels, _ = _extract_genre_family_matches(context_text)
    lowered_context = (context_text or "").lower()
    compound_pop_punk = any(token in lowered_context or token in (context_text or "") for token in ("pop-punk", "pop punk", "팝펑크", "팝 펑크"))
    requested_genre_axes = []
    if not compound_pop_punk and ("pop" in lowered_context or "팝" in (context_text or "")):
        requested_genre_axes.append("pop")
    if not compound_pop_punk and ("punk" in lowered_context or "펑크" in (context_text or "")):
        requested_genre_axes.append("punk")
    if compound_pop_punk:
        requested_genre_axes.append("pop-punk")
    current_genre = explicit_genres[0] if explicit_genres else None
    dream_pop_synth_request = _is_dream_pop_synth_request(context_text)
    selected_tracks = []
    for track in tracks:
        facts = track.reason_facts or {}
        selected_tracks.append({
            "display_title": track.display_title or track.name,
            "artist": track.artist_name,
            "album": track.album_name,
            "spotify_track_name": track.spotify_track_name,
            "spotify_track_id": track.track_id if not track.track_id.startswith("fallback-") else None,
            "canonical_recording_identity": track.canonical_recording_identity or facts.get("canonical_recording_identity"),
            "recording_match_confidence": track.recording_match_confidence,
            "actual_instruments": facts.get("recording_instruments") or [],
            "piano": "piano" in set(facts.get("recording_instruments") or []),
            "saxophone": "saxophone" in set(facts.get("recording_instruments") or []),
            "instrumentation_source": track.instrumentation_source or facts.get("instrumentation_verification") or "unknown",
            "actual_track_features": {
                "tags": facts.get("tags", []),
                "moods": facts.get("moods", []),
                "feature_provenance": facts.get("feature_provenance", {}),
            },
            "low_stimulation_fit": facts.get("low_stimulation_fit"),
            "relaxed_fit": facts.get("relaxed_fit"),
            "relaxed_flow_fit": facts.get("relaxed_flow_fit"),
            "calm_fit": facts.get("calm_fit"),
            "rhythmic_intensity": facts.get("rhythmic_intensity"),
            "mellow_fit": facts.get("mellow_fit"),
            "light_rhythm_fit": facts.get("light_rhythm_fit"),
            "long_session_fit": facts.get("long_session_fit"),
            "sustained_focus_fit": facts.get("sustained_focus_fit"),
            "distraction_risk": facts.get("distraction_risk"),
            "feature_role_compatibility": facts.get("feature_role_compatibility"),
            "drive_fit": facts.get("drive_fit"),
            "energy_fit": facts.get("energy_fit"),
            "pop_fit": facts.get("pop_fit"),
            "punk_fit": facts.get("punk_fit"),
            "pop_punk_bridge": facts.get("pop_punk_bridge"),
            "singalong_fit": facts.get("singalong_fit"),
            "dream_pop_fit": facts.get("dream_pop_fit"),
            "synth_fit": facts.get("synth_fit"),
            "atmospheric_fit": facts.get("atmospheric_fit"),
            "spatial_fit": facts.get("spatial_fit"),
            "immersive_fit": facts.get("immersive_fit"),
            "dreamy_fit": facts.get("dreamy_fit"),
            "intensity": facts.get("intensity"),
            "playlist_role": (
                "light_rhythm"
                if facts.get("light_rhythm_fit")
                else "calm_anchor"
                if facts.get("low_stimulation_fit")
                else "bridge"
            ),
            "final_ranking_score": facts.get("final_ranking_score"),
        })
    return {
        "previous_request_genre": None,
        "previous_request_explicit_genre": None,
        "current_request_genre": current_genre,
        "current_request_explicit_genre": current_genre,
        "current_request_explicit_genres": explicit_genres,
        "current_request_requested_genre_axes": requested_genre_axes,
        "current_request_genre_labels": genre_labels,
        "current_artist_origin_preference": None,
        "genre_state_reset": True,
        "previous_candidate_pool_reused": False,
        "focus_request_feature_reset": True,
        "current_retrieval_query": (
            ["dream-pop", "synth", "atmospheric", "spacious", "immersive"]
            if dream_pop_synth_request
            else explicit_genres[:5] if explicit_genres else ["genre_neutral_catalog"]
        ),
        "genre_ranking_weights": (
            {"explicit_genre": 1.0}
            if dream_pop_synth_request
            else {"explicit_genre": 1.0}
            if explicit_genres
            else {"low_stimulation": 1.0, "sustained_focus": 1.0, "calm": 0.9, "light_rhythm": 0.7}
        ),
        "genre_bonus": 0 if not explicit_genres else 1.0,
        "drive_request": _is_drive_request(context_text),
        "previous_focus_context_reset": True,
        "previous_artist_origin_preference_reset": True,
        "selected_track_count": len(tracks),
        "pop_side_count": sum(bool((track.reason_facts or {}).get("pop_fit")) and not bool((track.reason_facts or {}).get("pop_punk_bridge")) for track in tracks),
        "punk_side_count": sum(bool((track.reason_facts or {}).get("punk_fit")) and not bool((track.reason_facts or {}).get("pop_punk_bridge")) for track in tracks),
        "pop_punk_bridge_count": sum(bool((track.reason_facts or {}).get("pop_punk_bridge")) for track in tracks),
        "dream_pop_count": sum(bool((track.reason_facts or {}).get("dream_pop_fit")) for track in tracks),
        "ambient_electronic_count": sum(
            bool({"ambient", "electronic"}.intersection({str(tag).lower() for tag in (track.reason_facts or {}).get("tags", []) if tag}))
            for track in tracks
        ),
        "dream_pop_adjacent_count": sum(
            bool((track.reason_facts or {}).get("atmospheric_fit")) and not bool((track.reason_facts or {}).get("dream_pop_fit"))
            for track in tracks
        ),
        "synth_confirmed_count": sum(bool((track.reason_facts or {}).get("synth_fit")) for track in tracks),
        "synth_related_count": sum(
            bool({"synth", "synth-pop"}.intersection({str(tag).lower() for tag in (track.reason_facts or {}).get("tags", []) if tag}))
            for track in tracks
        ),
        "shoegaze_count": sum(
            "shoegaze" in {str(tag).lower() for tag in (track.reason_facts or {}).get("tags", []) if tag}
            for track in tracks
        ),
        "atmospheric_count": sum(bool((track.reason_facts or {}).get("atmospheric_fit")) for track in tracks),
        "spatial_fit_count": sum(bool((track.reason_facts or {}).get("spatial_fit")) for track in tracks),
        "immersive_fit_count": sum(bool((track.reason_facts or {}).get("immersive_fit")) for track in tracks),
        "acoustic_or_piano_only_count": sum(
            bool({"acoustic", "piano", "classical"}.intersection({str(tag).lower() for tag in (track.reason_facts or {}).get("tags", []) if tag}))
            and not bool({"dream-pop", "synth", "synth-pop", "electronic", "atmospheric", "spacious", "immersive"}.intersection({str(tag).lower() for tag in (track.reason_facts or {}).get("tags", []) if tag}))
            for track in tracks
        ),
        "selected_tracks": selected_tracks,
    }


def _merge_context_audio_hints(context_text: str | None) -> tuple[list[str], dict[str, object]]:
    genres: list[str] = []
    params: dict[str, object] = {}

    if not context_text or not isinstance(context_text, str):
        return genres, params

    explicit_genres, _, explicit_params = _extract_genre_family_matches(context_text)
    genres.extend(explicit_genres)
    params.update(explicit_params)

    if _is_dream_pop_synth_request(context_text):
        genres.extend(["dream-pop", "shoegaze", "synth-pop", "electronic"])
        params.update({"target_energy": 0.52, "target_acousticness": 0.38})

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
    explicit_genre_set = set(explicit_genres)
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
    spotify_name = str(track.get("name") or "Unknown Track")
    album_name = album.get("name")
    identity = f"{spotify_name} — {primary_artist} — {album_name}" if album_name else None
    reason_facts = {
        **_build_reason_facts(spotify_name, str(primary_artist), seed_genres),
        **({"popularity": track["popularity"]} if isinstance(track.get("popularity"), int) else {}),
        "recording_identity_source": "spotify_title_artist_match",
        "instrumentation_verification": "unknown",
        "recording_instruments": [],
    }

    return TrackSummary(
        track_id=str(track.get("id") or track.get("uri") or track.get("name")),
        name=spotify_name,
        artist_name=str(primary_artist),
        display_title=str(track.get("name") or "Unknown Track"),
        spotify_track_name=spotify_name,
        canonical_recording_identity=identity,
        recording_match_confidence=0.8,
        instrumentation_source="not_available_from_spotify_track_response",
        album_name=album_name,
        album_image_url=album_image_url,
        spotify_url=spotify_url,
        preview_url=track.get("preview_url"),
        duration_ms=duration_ms if isinstance(duration_ms, int) else None,
        reason_facts=reason_facts,
        reason=reason,
    )


def _track_summary_category(track: TrackSummary) -> str:
    facts = track.reason_facts if isinstance(track.reason_facts, dict) else {}
    tags = {str(tag).strip().lower() for tag in facts.get("tags", []) if tag}
    return next(
        (
            value
            for value in (
                "jazz", "classical", "ambient", "electronic", "rnb",
                "rock", "jpop", "pop", "hip-hop",
            )
            if value in tags
        ),
        "other",
    )


def _select_diverse_track_summaries(
    tracks: list[TrackSummary],
    limit: int,
    recent_track_keys: set[str] | None = None,
) -> list[TrackSummary]:
    """Choose from a wider ranked pool while avoiding recent repeats."""
    if len(tracks) <= limit and not recent_track_keys:
        return tracks[:limit]

    recent_keys = recent_track_keys or set()
    ranked = sorted(
        enumerate(tracks),
        key=lambda item: (
            _track_history_key(item[1].name, item[1].artist_name) in recent_keys,
            -int((item[1].reason_facts or {}).get("popularity") or 0),
            item[0],
        ),
    )
    pool = [track for _, track in ranked[: max(limit * 3, limit)]]
    selected: list[TrackSummary] = []
    seen: set[tuple[str, str]] = set()
    seen_artists: set[str] = set()
    category_counts: dict[str, int] = {}

    def add(track: TrackSummary) -> None:
        key = (track.name.strip().lower(), track.artist_name.strip().lower())
        if key in seen:
            return
        seen.add(key)
        selected.append(track)
        seen_artists.add(key[1])
        category = _track_summary_category(track)
        category_counts[category] = category_counts.get(category, 0) + 1

    for track in pool:
        key = (track.name.strip().lower(), track.artist_name.strip().lower())
        category = _track_summary_category(track)
        if key in seen or key[1] in seen_artists:
            continue
        if category_counts.get(category, 0) >= 2 and len(selected) < limit - 1:
            continue
        add(track)
        if len(selected) >= limit:
            return selected

    for track in pool:
        add(track)
        if len(selected) >= limit:
            break
    return selected[:limit]


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


def _is_drive_request(context_text: str | None) -> bool:
    if not context_text or not isinstance(context_text, str):
        return False
    lowered = context_text.lower()
    return any(token in context_text or token in lowered for token in ("차 타고", "차 안", "드라이브", "도로 위", "운전", "drive", "road trip"))


def _korean_band_rock_preference_strength(context_text: str | None) -> str | None:
    """Parse origin, artist type, genre, and strength instead of one vague tag."""
    if not context_text:
        return None
    lowered = context_text.lower()
    korean = any(token in context_text or token in lowered for token in ("우리나라", "국내", "한국", "korean"))
    band = any(token in context_text or token in lowered for token in ("밴드", "band", "그룹"))
    rock = any(token in context_text or token in lowered for token in ("락", "록", "rock"))
    if not (korean and band and rock):
        return None
    if any(token in context_text or token in lowered for token in ("만 추천", "전부", "only", "only korean")):
        return "hard"
    if any(token in context_text or token in lowered for token in ("위주", "중심", "mostly")):
        return "strong"
    return "moderate"


def _prefers_korean_band_rock(context_text: str | None) -> bool:
    return _korean_band_rock_preference_strength(context_text) is not None


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

    if _is_family_trip_request(context_text):
        terms.extend(["여행을 떠나요 조용필", "해변의 여인 COOL", "아모르파티 김연자", "summer drive pop"])
    if _context_prefers_korean_rnb(context_text):
        terms.extend(["DEAN", "Colde", "Crush", "Zion.T", "Hoody", "SAAY", "Heize", "BIBI"])
    if _context_prefers_punk_rock(context_text):
        terms.extend(["Green Day", "Paramore", "Blink-182", "Fall Out Boy", "Sum 41", "The Offspring", "Panic! At The Disco"])
    if _prefers_korean_band_rock(context_text):
        terms.extend(["YB 나는 나비", "자우림 일탈", "체리필터 낭만고양이", "국카스텐 거울", "FTISLAND 바래", "버즈 겁쟁이"])
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
    korean_band_rock_strength = _korean_band_rock_preference_strength(context_text)
    comfort_request = _context_requests_comfort(context_text)
    job_search_request = any(
        token in (context_text or "").lower()
        for token in ("취업", "입사", "면접", "지원서", "자소서", "이력서")
    )
    study_flow_request = any(token in (context_text or "").lower() for token in ("공부", "과제", "작업", "집중", "몰입"))
    long_focus_request = _is_long_focus_request(context_text)
    calm_jazz_instrument_request = _is_calm_jazz_instrument_request(context_text)
    avoids_overstimulation = any(token in (context_text or "").lower() for token in ("소란", "시끄", "방해", "과하지", "너무 강", "자극"))
    sleep_request = _is_sleep_request(context_text)
    dawn_sentimental_request = _is_dawn_sentimental_request(context_text)
    dream_pop_synth_request = _is_dream_pop_synth_request(context_text)
    mbti_aesthetic = detect_mbti_aesthetic(context_text)
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

    if _is_dream_pop_synth_request(context_text):
        return (
            "몽환적인 신스와 공간감 있는 사운드를 중심으로, 현실과 조금 떨어진 듯한 분위기에서 듣기 좋은 곡들을 골라봤어요. "
            "잔잔함에만 치우치지 않도록 드림 팝과 전자 사운드가 있는 곡들도 함께 담았어요."
        )

    if _is_calm_jazz_instrument_request(context_text):
        track_facts = [track.reason_facts or {} for track in (tracks or [])]
        all_jazz = bool(track_facts) and all(
            "jazz" in {str(tag).lower() for tag in facts.get("tags", []) if tag}
            for facts in track_facts
        )
        piano_sax_count = sum(
            {"piano", "saxophone"}.issubset(
                {str(tag).lower() for tag in facts.get("tags", []) if tag}
            )
            for facts in track_facts
        )
        verified_piano_sax_count = sum(
            facts.get("instrumentation_verification") == "recording_metadata"
            and {"piano", "saxophone"}.issubset(set(facts.get("recording_instruments") or []))
            for facts in track_facts
        )
        high_rhythm_count = sum(facts.get("rhythmic_intensity") == "high" for facts in track_facts)
        moderate_rhythm_count = sum(facts.get("rhythmic_intensity") == "moderate" for facts in track_facts)
        if all_jazz and verified_piano_sax_count >= max(1, len(track_facts) // 2):
            return (
                "오늘처럼 조금 지친 상태에서 차분하게 들을 수 있는 재즈 곡들을 골라봤어요. "
                f"피아노와 색소폰이 어우러지는 연주를 중심으로, {'중간중간 가벼운 리듬감이 느껴지는 곡도' if high_rhythm_count or moderate_rhythm_count else '느긋한 연주를'} 함께 담았어요."
            )
        rhythm_clause = (
            "차분한 연주를 중심으로, 중간중간 가벼운 리듬감이 느껴지는 곡도 함께 담았어요."
            if high_rhythm_count or moderate_rhythm_count
            else "느긋한 연주를 중심으로 골라봤어요."
        )
        return f"오늘처럼 조금 지친 상태에서 차분하게 들을 수 있는 재즈 곡들을 중심으로 골라봤어요. {rhythm_clause}"

    if study_flow_request and avoids_overstimulation:
        return "지금의 좋은 집중 흐름은 유지하면서도 너무 과하지 않게 활기를 더할 수 있는 곡들을 골라봤어요."

    if long_focus_request:
        focus_facts = [track.reason_facts or {} for track in (tracks or [])]
        calm_count = sum(bool(facts.get("calm_fit")) for facts in focus_facts)
        light_rhythm_count = sum(bool(facts.get("light_rhythm_fit")) for facts in focus_facts)
        rhythm_clause = (
            "일부 곡에는 가벼운 리듬감도 확인돼요."
            if light_rhythm_count
            else "리듬감이 확인되지 않은 곡의 특징은 임의로 덧붙이지 않았어요."
        )
        calm_clause = "차분한 곡들을 중심으로" if calm_count else "오래 이어 듣기 부담이 적은 곡들을 중심으로"
        return f"노트북 앞에 오래 앉아 있을 때 {calm_clause} 골라봤어요. {rhythm_clause}"

    if _is_drive_request(context_text) and not _is_family_trip_request(context_text):
        return (
            "주말 장거리 드라이브에 어울리는 신나는 팝과 펑크 곡들을 골라봤어요. "
            "밝은 팝부터 강한 밴드 사운드까지, 이동하면서 활기 있게 듣기 좋은 곡들을 함께 담았어요."
        )

    if _is_family_trip_request(context_text):
        season_text = "여름" if _current_season() == "summer" else "지금 계절"
        departure = "내일 가족과 함께 떠나는" if "내일" in (context_text or "") else "가족과 함께 떠나는"
        return (
            f"{departure} 여행길에 듣기 좋은 "
            "신나는 곡들을 골라봤어요. "
            f"{season_text} 여행의 설렘을 이어가며 차 안에서 다 같이 즐기기 좋은 음악들이에요."
        )

    if _is_dream_pop_synth_request(context_text):
        preferred = [
            candidate
            for candidate in catalog
            if {"dream-pop", "synth", "synth-pop", "atmospheric", "spacious", "immersive"}.intersection(
                {str(tag).lower() for tag in candidate.get("tags", []) if tag}
            )
        ]
        # Keep the candidate pool specific to the requested sound first. A
        # broader ambient bridge may remain only when it carries verified
        # synth/space metadata, never as a substitute for dream pop.
        if preferred:
            catalog = preferred + [candidate for candidate in catalog if candidate not in preferred]
    elif _is_dawn_sentimental_request(context_text):
        return (
            "새벽의 센치한 분위기에 천천히 잠겨 듣기 좋은 몽환적이고 감성적인 곡들을 골라봤어요. "
            "혼자 생각이 길어지는 순간에 조용히 이어 듣기 좋은 음악들이에요."
        )

    if _korean_band_rock_preference_strength(context_text):
        return (
            "오늘 쌓인 답답한 기분을 강한 음악으로 환기하고 싶을 때 듣기 좋은 국내 밴드 록을 중심으로 골라봤어요. "
            "신나고 강렬한 분위기로 기분을 바꾸며 듣기 좋은 곡들이에요."
        )

    if sleep_request and constraints["instrumental_required"] and verified_instrumental_only:
        return (
            "어젯밤 생각이 많아 충분히 쉬지 못한 만큼, 지금 잠시 편안하게 쉬어가며 들을 수 있는 잔잔한 연주곡 위주로 골라봤어요. "
            "복잡한 생각에서 잠시 거리를 두고 싶을 때 부담 없이 곁들이기 좋은 곡들이에요."
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
        "긴장 내려놓기": "지금 쌓인 긴장을 조금 내려놓고 싶을 때 잘 어울려요.",
        "생각의 속도 늦추기": "생각이 계속 이어져 쉽게 잠들기 어려운 순간에, 머릿속의 속도를 조금 늦추며 듣기 좋아요.",
        "감정을 조용히 정리하기": "마음이 쉽게 가라앉지 않을 때 오늘의 감정을 천천히 정리하며 듣기 좋습니다.",
        "생각을 가볍게 정돈하기": "머릿속에 남은 생각을 가볍게 정돈하고 싶을 때 잘 맞아요.",
        "복잡한 생각에서 잠시 거리 두기": "여러 생각이 한꺼번에 떠오를 때, 잠시 다른 흐름에 마음을 두고 쉬어가고 싶다면 잘 어울려요.",
        "휴식 분위기로 전환하기": "잠시 휴식하는 분위기로 자연스럽게 전환하고 싶을 때 잘 어울려요.",
        "여행 출발 전 기분 끌어올리기": "여행을 떠나는 설렘을 그대로 이어가고 싶을 때 듣기 좋아요.",
        "차 안 분위기 밝게 유지하기": "이동하는 동안 차 안 분위기를 밝게 이어가고 싶을 때 듣기 좋아요.",
        "가족이 함께 즐기기": "가족과 함께 이동하며 다 같이 흥겹게 듣고 싶을 때 잘 맞아요.",
        "이동 중 분위기 환기하기": "이동이 길어져 분위기를 가볍게 바꾸고 싶을 때 어울려요.",
        "여름 드라이브 분위기 살리기": "여름 여행의 들뜬 분위기를 조금 더 살리고 싶은 순간에 듣기 좋아요.",
        "여행의 설렘 이어가기": "목적지로 향하는 시간을 즐겁게 이어가고 싶을 때 듣기 좋아요.",
        "드라이브 시작 분위기 열기": "주말 드라이브를 시작하며 신나는 곡을 듣고 싶을 때 잘 맞아요.",
        "차 안에서 따라 부르기": "차 안에서 함께 따라 부르며 듣고 싶은 순간에 잘 맞아요.",
        "팝 분위기 더하기": "도로 위에서 밝은 팝 분위기를 이어가고 싶을 때 잘 맞아요.",
        "펑크 에너지 더하기": "강한 밴드 사운드로 드라이브 분위기를 바꾸고 싶을 때 어울려요.",
        "이동 중 리듬 변화": "이동하면서 에너지 있는 곡을 이어 듣고 싶을 때 듣기 좋아요.",
        "장거리 드라이브 기분 유지": "멀리 이동하는 동안 활기 있는 음악을 듣고 싶을 때 잘 맞아요.",
        "조금 더 강한 사운드 듣기": "이동 중 조금 더 강한 밴드 사운드를 원할 때 잘 맞아요.",
        "펑크 사운드로 구간 바꾸기": "장거리 이동 중 사운드를 한 번 바꾸고 싶은 구간에 듣기 좋아요.",
        "몽환적인 시작 열기": "현실과 조금 떨어진 듯한 분위기에서 음악을 시작하고 싶을 때 잘 맞아요.",
        "신스 중심 분위기 이어가기": "신스가 어우러진 사운드에 자연스럽게 몰입하고 싶은 순간에 듣기 좋아요.",
        "공간감 있는 사운드에 머물기": "소리가 넓게 퍼지는 듯한 분위기에 귀를 두고 싶을 때 잘 어울려요.",
        "잔잔함에서 한 걸음 벗어나기": "조용하기만 한 곡보다 조금 더 밀도 있는 사운드를 찾을 때 잘 맞아요.",
        "감성적인 흐름 이어가기": "몽환적이면서 감성적인 흐름을 이어 듣는 시간에 잘 맞아요.",
        "몰입감 있는 구간 만들기": "주변과 잠시 거리를 두고 사운드에 집중하고 싶은 순간에 잘 맞아요.",
        "새벽 분위기에 천천히 잠기기": "새벽 특유의 고요한 분위기에 천천히 잠기고 싶을 때 잘 맞아요.",
        "혼자 생각에 머물기": "혼자 생각이 길어지는 순간에 듣기 좋아요.",
        "센치한 감정을 따라가기": "센치해진 감정을 억지로 바꾸지 않고 따라가고 싶을 때 잘 어울려요.",
        "몽환적인 분위기 유지하기": "새벽의 센치한 흐름에 더 깊이 잠기고 싶을 때 잘 맞아요.",
        "감정의 여운 이어가기": "마음에 남은 여운을 천천히 느끼고 싶을 때 듣기 좋아요.",
        "새벽의 고요함에 머물기": "새벽에 혼자 조용한 시간을 보내고 싶을 때 잘 어울려요.",
        "답답한 기분 강하게 환기하기": "답답한 기분을 강한 음악으로 환기하고 싶을 때 듣기 좋아요.",
        "분노의 에너지와 맞추기": "화가 아직 가라앉지 않았을 때 강한 분위기의 음악을 듣고 싶다면 잘 맞아요.",
        "신나는 록으로 방향 바꾸기": "스트레스를 잠시 잊고 분위기를 바꾸고 싶을 때 어울려요.",
        "속이 답답할 때 텐션 올리기": "속이 답답할 때 강렬한 록으로 분위기를 바꾸고 싶다면 듣기 좋아요.",
        "밴드 사운드에 몰입하기": "강렬한 밴드 음악에 집중해 듣고 싶을 때 잘 맞아요.",
        "기분을 확 바꾸기": "지금의 기분을 빠르게 전환하고 싶을 때 어울려요.",
        "장시간 틀어두기": "노트북 앞에 오래 앉아 음악을 틀어두고 싶을 때 듣기 좋아요.",
        "차분한 흐름 유지": "긴 시간 차분한 음악을 이어 듣고 싶을 때 잘 맞아요.",
        "가벼운 리듬 더하기": "잔잔함을 유지하면서 리듬감을 조금 더하고 싶을 때 어울려요.",
        "낮은 자극으로 배경 유지": "음악이 지나치게 앞에 나서지 않는 분위기를 원할 때 듣기 좋아요.",
        "단조로움 줄이기": "차분한 흐름 안에서 작은 리듬 변화를 듣고 싶을 때 잘 맞아요.",
        "긴 청취에 맞추기": "오래 이어 들어도 강한 자극을 피하고 싶을 때 어울려요.",
        "차분한 배경으로 이어 듣기": "음악이 앞에 나서지 않는 분위기로 오래 듣고 싶을 때 잘 맞아요.",
        "집중 흐름에 무리 없이 맞추기": "차분한 음악을 오래 이어 듣고 싶을 때 잘 맞아요.",
        "리듬 변화 듣기": "차분한 곡들 사이에서 리듬이 조금 더 있는 재즈를 듣고 싶을 때 잘 맞아요.",
        "재즈의 박자감 느끼기": "느긋한 곡만 이어지지 않도록 박자감에 작은 변화를 주고 싶을 때 잘 어울려요.",
        "가벼운 재즈 리듬 더하기": "차분한 분위기를 유지하면서 가벼운 리듬을 더하고 싶을 때 잘 맞아요.",
        "지친 상태에서 차분한 재즈 듣기": "오늘 조금 지친 상태에서 자극적인 음악보다 차분하게 듣고 싶을 때 잘 맞아요.",
        "피아노와 색소폰의 흐름 듣기": "피아노와 색소폰 연주를 천천히 듣고 싶을 때 잘 어울려요.",
        "낮은 강도의 연주 선택": "강한 자극보다 느긋한 재즈를 찾을 때 듣기 좋아요.",
        "느긋한 재즈로 쉬기": "긴장이 남아 있어 여유 있는 음악을 듣고 싶을 때 잘 맞아요.",
        "감성적인 연주에 머물기": "감성적인 재즈를 차분하게 듣고 싶은 순간에 어울려요.",
        "재즈의 여백 즐기기": "피아노와 색소폰이 어우러지는 흐름을 부담 없이 듣고 싶을 때 잘 맞아요.",
    }
    family_templates = {
        "여행 출발 전 기분 끌어올리기": "여행을 떠나는 설렘을 그대로 이어가고 싶을 때 듣기 좋아요.",
        "차 안 분위기 밝게 유지하기": "이동하는 동안 차 안의 밝은 분위기를 이어가고 싶을 때 잘 맞아요.",
        "가족이 함께 즐기기": "가족과 함께 흥겹게 듣고 싶은 순간에 잘 맞아요.",
        "이동 중 분위기 환기하기": "이동이 길어져 차 안 분위기를 가볍게 환기하고 싶을 때 듣기 좋아요.",
        "여름 드라이브 분위기 살리기": "여름 여행의 들뜬 분위기를 조금 더 살리고 싶은 순간에 듣기 좋아요.",
        "여행의 설렘 이어가기": "목적지로 향하는 시간에 기분 좋게 듣고 싶을 때 잘 맞아요.",
    }
    if focus in family_templates:
        return family_templates[focus]
    if focus in templates:
        return templates[focus]
    if situation_angle:
        return f"{situation_angle}, 잠시 쉬어가며 듣기 좋아요."
    return [
        "잠시 생각의 속도를 늦추며 쉬어가고 싶을 때 잘 어울려요.",
        "복잡한 마음을 천천히 정리하며 듣기 좋습니다.",
    ][index % 2]


def _calm_jazz_role_without_instrumentation(index: int) -> str:
    sentences = (
        "오늘처럼 조금 지친 상태에서 자극적인 음악보다 차분하게 듣고 싶을 때 잘 맞아요.",
        "연주를 천천히 따라가며 여유 있는 시간을 보내고 싶을 때 잘 어울려요.",
        "강한 자극보다 느긋한 재즈를 찾는 순간에 듣기 좋아요.",
        "긴장이 남아 있어 서두르지 않는 음악을 듣고 싶을 때 잘 맞아요.",
        "감성적인 재즈를 차분하게 듣고 싶은 순간에 어울려요.",
        "재즈의 흐름을 부담 없이 이어 듣고 싶을 때 잘 맞아요.",
    )
    return sentences[index % len(sentences)]


def _tag_feature_sentence(
    track_tags: list[str], tag_labels: dict[str, str], variant_index: int = 0
) -> str | None:
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
    natural_single_features = {
        "경쾌한 에너지": (
            "밝고 신나는 분위기가 가볍게 이어지는 곡이에요.",
            "기분 좋은 활기가 자연스럽게 살아 있는 곡이에요.",
            "신나는 분위기가 부담 없이 이어지는 곡이에요.",
        ),
        "높은 에너지": (
            "활기찬 분위기가 또렷하게 느껴지는 곡이에요.",
            "기분을 밝게 끌어올리는 에너지가 느껴지는 곡이에요.",
        ),
        "추진력 있는 리듬": "힘 있게 이어지는 분위기가 인상적인 곡이에요.",
    }
    sentence = natural_single_features.get(primary_feature)
    if isinstance(sentence, tuple):
        return sentence[variant_index % len(sentence)]
    if isinstance(sentence, str):
        return sentence
    return f"{primary_feature}이 자연스럽게 드러나는 곡이에요."


def _family_trip_feature_sentence(reason_facts: dict[str, object], index: int) -> str | None:
    """Use the family playlist's verified ranking cue before generic energy metadata."""
    tags = {str(tag).strip().lower() for tag in reason_facts.get("tags", []) if str(tag).strip()}
    cross_generation_fit = int(reason_facts.get("cross_generation_fit") or 0)
    role_index = index % 6
    if role_index == 1 and tags & {"mainstream", "broad_familiarity_ko"}:
        return "여러 사람이 비교적 익숙하게 들을 수 있는 대중적인 곡이에요."
    if role_index == 2 and "mainstream" in tags:
        return "대중적으로 익숙한 편인 곡이에요."
    if role_index == 4 and cross_generation_fit >= 3:
        return "세대가 달라도 비교적 익숙하게 느낄 수 있는 곡이에요."
    if role_index == 4 and "summer" in tags:
        return "여름의 밝은 분위기와 잘 어울리는 곡이에요."
    if role_index == 5 and "summer" in tags:
        return "여름의 밝은 분위기와 잘 어울리는 곡이에요."
    if role_index == 0 and tags & {"upbeat", "high_energy"}:
        return "밝고 신나는 분위기가 또렷하게 느껴지는 곡이에요."
    if role_index == 3 and tags & {"upbeat", "high_energy"}:
        return "흥겹고 활기찬 분위기가 또렷한 곡이에요."
    if "broad_familiarity_ko" in tags:
        return "여러 사람이 비교적 익숙하게 들을 수 있는 대중적인 곡이에요."
    if "mainstream" in tags:
        return "대중적으로 익숙한 편인 곡이에요."
    if "summer" in tags:
        return "여름의 밝은 분위기와 잘 어울리는 곡이에요."
    if tags & {"upbeat", "high_energy"}:
        return "밝고 신나는 분위기가 자연스럽게 이어지는 곡이에요."
    return None


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
    if {"jazz", "standard"}.issubset(tag_set) and "calm" in mood_set:
        return "차분한 재즈 연주가 중심이 되는 곡이에요."
    if "calm" in tag_set or "calm" in mood_set:
        return "차분한 분위기가 부담 없이 이어지는 연주곡이에요."
    if "dreamy" in tag_set:
        return "몽환적인 분위기가 잔잔하게 이어지는 연주곡이에요."
    return None


def _focus_feature_sentence(track_tags: list[str], track_moods: list[str]) -> str | None:
    tags = {str(tag).lower() for tag in track_tags if tag}
    moods = {str(mood).lower() for mood in track_moods if mood}
    if "prominent_vocal" in tags:
        return "보컬이 중심이 되는 곡이에요."
    if "bossa-nova" in tags:
        return "보사노바 계열의 가벼운 리듬이 이어지는 재즈 연주곡이에요."
    if "rhythmic_light" in tags or "groove" in tags:
        return "잔잔한 분위기 안에 가벼운 리듬감이 있는 곡이에요."
    if {"jazz", "standard"}.issubset(tags):
        return "스탠더드 재즈 연주가 중심인 곡이에요."
    if {"rnb", "groove"}.issubset(tags):
        return "부드러운 R&B와 가벼운 그루브가 함께 느껴지는 곡이에요."
    if {"jazz", "instrumental"}.issubset(tags):
        return "재즈 연주가 중심인 곡이에요."
    if "piano" in tags and "instrumental" in tags:
        return "피아노 중심의 연주곡이에요."
    if "calm" in moods or "calm" in tags:
        return "차분한 분위기의 곡이에요."
    if "soft" in tags:
        return "부드러운 분위기가 오래 이어 듣기 좋은 곡이에요."
    if "focused" in moods or "focused" in tags:
        return "일정한 분위기가 이어지는 곡이에요."
    return None


def _jazz_instrument_feature_sentence(track_facts: dict[str, object], index: int = 0) -> str | None:
    tags = {str(tag).lower() for tag in track_facts.get("tags", []) if tag}
    if track_facts.get("instrumentation_verification") != "recording_metadata":
        return _jazz_catalog_feature_sentence(tags, index)
    instruments = set(str(item).lower() for item in track_facts.get("recording_instruments", []) if item)
    if {"piano", "saxophone"}.issubset(instruments) and "jazz" in tags:
        if "low_stimulation" in tags or "relaxed" in tags:
            return "피아노와 색소폰이 함께하는 차분한 재즈 연주곡이에요."
        return "피아노와 색소폰이 함께하는 재즈 연주곡이에요."
    if "saxophone" in instruments and "jazz" in tags:
        return "색소폰이 중심이 되는 재즈 연주곡이에요."
    if "piano" in instruments and "jazz" in tags:
        return "피아노가 중심이 되는 차분한 재즈 연주곡이에요."
    return None


def _jazz_catalog_feature_sentence(tags: set[str], index: int = 0) -> str | None:
    """Describe only catalog-level genre/mood facts when recording instruments are unknown."""
    feature_sentences: list[str] = []
    if "bossa-nova" in tags:
        feature_sentences.append("보사노바 계열의 가벼운 리듬이 있는 재즈 연주곡이에요.")
    if "odd_meter" in tags:
        feature_sentences.append("독특한 박자감이 또렷한 재즈 연주곡이에요.")
    if "hard-bop" in tags:
        feature_sentences.append("하드 밥 계열의 리듬감이 분명한 재즈 곡이에요.")
    if "rhythmic_light" in tags or "groove" in tags:
        feature_sentences.append("가벼운 리듬감이 있는 재즈 연주곡이에요.")
    if "modal" in tags:
        feature_sentences.append("모달 재즈 특성이 드러나는 연주곡이에요.")
    if "low_stimulation" in tags:
        feature_sentences.append("자극이 적은 편인 재즈 연주곡이에요.")
    if "standard" in tags:
        feature_sentences.append("재즈 스탠더드의 연주가 중심인 곡이에요.")
    if "relaxed" in tags:
        feature_sentences.append("느긋한 분위기의 재즈 연주곡이에요.")
    if "instrumental" in tags:
        feature_sentences.append("기악 연주가 중심인 재즈 곡이에요.")
    if "jazz" in tags:
        feature_sentences.append("재즈 연주가 중심인 곡이에요.")
    return feature_sentences[index % len(feature_sentences)] if feature_sentences else None


def _dawn_sentimental_feature_sentence(
    track_tags: list[str], recommendation_role: dict[str, str] | None = None
) -> str | None:
    """Describe only verified traits that fit a dreamy, late-night playlist."""
    tags = {str(tag).lower() for tag in track_tags if tag}
    role_focus = (recommendation_role or {}).get("focus", "")
    if {"piano", "instrumental"}.issubset(tags):
        return "피아노 중심의 연주가 자연스럽게 이어지는 곡이에요."
    if {"dream-pop", "dreamy"}.issubset(tags):
        return "드림 팝 특유의 몽환적인 분위기가 느껴지는 곡이에요."
    if {"rnb", "soul"}.issubset(tags):
        return "R&B/Soul 계열의 분위기가 자연스럽게 이어지는 곡이에요."
    if {"soft", "emotional"}.issubset(tags):
        return "부드럽고 감성적인 분위기가 자연스럽게 이어지는 곡이에요."
    if "soft" in tags:
        return "부드러운 분위기가 자연스럽게 이어지는 곡이에요."
    if "calm" in tags and role_focus == "혼자 생각에 머물기":
        return "차분한 분위기가 자연스럽게 이어지는 곡이에요."
    if "ambient" in tags:
        return "앰비언트 분위기가 자연스럽게 이어지는 곡이에요."
    if {"rnb", "soul", "emotional"}.issubset(tags):
        return "R&B/Soul 계열의 감성적인 분위기가 느껴지는 곡이에요."
    if "dreamy" in tags:
        return "몽환적인 분위기가 자연스럽게 이어지는 곡이에요."
    if "emotional" in tags:
        return "감성적인 분위기가 자연스럽게 이어지는 곡이에요."
    if "soft" in tags:
        return "부드러운 분위기가 자연스럽게 이어지는 곡이에요."
    return None


def _korean_band_rock_feature_sentence(track_tags: list[str], index: int = 0) -> str | None:
    """Use one verified rock feature without exposing a raw tag list."""
    tags = {str(tag).lower() for tag in track_tags if tag}
    if "pop-rock" in tags:
        return "팝 록 특유의 선명한 분위기가 느껴지는 곡이에요."
    if "alternative" in tags:
        return "얼터너티브 록 특유의 강한 분위기가 느껴지는 곡이에요."
    if "punk" in tags:
        return "펑크 록의 신나는 분위기가 또렷한 곡이에요."
    if "high_energy" in tags:
        return "강렬한 록 분위기가 또렷한 곡이에요."
    if "upbeat" in tags:
        return "신나는 록 분위기가 자연스럽게 이어지는 곡이에요."
    if "rock" in tags:
        return "록 사운드가 중심인 곡이에요."
    return None


def _drive_feature_sentence(track_tags: list[str], index: int = 0) -> str | None:
    """Describe a supplied drive/genre feature without promising an effect."""
    tags = {str(tag).lower() for tag in track_tags if tag}
    feature_sentences: list[str] = []
    if "pop-punk" in tags:
        feature_sentences.append("팝과 펑크의 성격이 함께 드러나는 팝펑크 곡이에요.")
    if "punk" in tags:
        feature_sentences.append("강한 밴드 사운드가 중심인 펑크 록 곡이에요.")
        feature_sentences.append("펑크 록 특유의 직선적인 사운드가 분명한 곡이에요.")
        feature_sentences.append("펑크 성향의 록 사운드가 중심인 곡이에요.")
    if "pop" in tags or "dance-pop" in tags or "synth-pop" in tags:
        feature_sentences.append("밝고 신나는 팝 분위기가 또렷한 곡이에요.")
    if "rock" in tags:
        feature_sentences.append(
            "밴드 중심의 록 사운드가 있는 곡이에요."
            if "artist_band" in tags
            else "록 사운드가 중심인 곡이에요."
        )
    if "high_energy" in tags or "driving" in tags:
        feature_sentences.append("에너지 있는 분위기가 분명한 곡이에요.")
    if "upbeat" in tags:
        feature_sentences.append("밝고 경쾌한 분위기가 이어지는 곡이에요.")
    return feature_sentences[index % len(feature_sentences)] if feature_sentences else None


def _dream_pop_synth_feature_sentence(track_tags: list[str], index: int = 0) -> str | None:
    """Describe only catalog-confirmed genre and sound traits for this request."""
    tags = {str(tag).lower() for tag in track_tags if tag}
    feature_sentences: list[str] = []
    if {"dream-pop", "synth"}.issubset(tags):
        feature_sentences.append("드림 팝과 신스가 함께 어우러지는 곡이에요.")
    if {"dream-pop", "atmospheric"}.issubset(tags):
        feature_sentences.append("드림 팝 특유의 몽환적인 사운드가 중심인 곡이에요.")
    if {"dream-pop", "shoegaze"}.issubset(tags):
        feature_sentences.append("드림 팝과 슈게이즈 성향이 함께 드러나는 곡이에요.")
    if {"dream-pop", "spacious"}.issubset(tags):
        feature_sentences.append("공간감 있는 드림 팝 사운드가 중심인 곡이에요.")
    if {"dream-pop", "immersive"}.issubset(tags):
        feature_sentences.append("몰입감 있는 드림 팝 사운드가 또렷한 곡이에요.")
    if {"synth-pop", "synth"}.issubset(tags):
        feature_sentences.append("신스팝 기반의 전자 사운드가 또렷한 곡이에요.")
    if {"ambient", "synth", "spacious"}.issubset(tags):
        feature_sentences.append("신스 중심의 앰비언트 사운드가 넓게 이어지는 연주곡이에요.")
    if {"electronic", "spacious"}.issubset(tags):
        feature_sentences.append("공간감 있는 전자 사운드가 중심인 곡이에요.")
    if "atmospheric" in tags:
        feature_sentences.append("대기감 있는 사운드가 자연스럽게 이어지는 곡이에요.")
    return feature_sentences[index % len(feature_sentences)] if feature_sentences else None


def build_track_reason(
    track: TrackSummary,
    mood: str,
    context_text: str | None,
    index: int,
    recommendation_role: dict[str, str] | None = None,
    reason_feature_index: int | None = None,
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

    facts = track.reason_facts or {}
    track_tags = [str(tag) for tag in facts.get("tags", []) if tag]
    track_moods = [str(item) for item in facts.get("moods", []) if item]
    if _is_family_trip_request(context_text):
        family_feature = _family_trip_feature_sentence(facts, index)
        if family_feature:
            return f"{family_feature} {_role_listening_sentence(recommendation_role, index)}"
    if _prefers_korean_band_rock(context_text):
        rock_feature = _korean_band_rock_feature_sentence(track_tags, index)
        if rock_feature:
            return f"{rock_feature} {_role_listening_sentence(recommendation_role, index)}"
    if _is_sleep_request(context_text):
        sleep_feature = _sleep_feature_sentence(track_tags, track_moods)
        if sleep_feature:
            return f"{sleep_feature} {_role_listening_sentence(recommendation_role, index)}"
    if _is_long_focus_request(context_text):
        focus_feature = _focus_feature_sentence(track_tags, track_moods)
        if focus_feature:
            return f"{focus_feature} {_role_listening_sentence(recommendation_role, index)}"
    if _is_dream_pop_synth_request(context_text):
        dream_feature = _dream_pop_synth_feature_sentence(
            track_tags, index if reason_feature_index is None else reason_feature_index
        )
        if dream_feature:
            return f"{dream_feature} {_role_listening_sentence(recommendation_role, index)}"
    if _is_drive_request(context_text) and not _is_family_trip_request(context_text):
        drive_feature = _drive_feature_sentence(
            track_tags, index if reason_feature_index is None else reason_feature_index
        )
        if drive_feature:
            return f"{drive_feature} {_role_listening_sentence(recommendation_role, index)}"
    if _is_calm_jazz_instrument_request(context_text):
        jazz_feature = _jazz_instrument_feature_sentence(
            facts, index if reason_feature_index is None else reason_feature_index
        )
        if jazz_feature:
            role_sentence = (
                _calm_jazz_role_without_instrumentation(index)
                if facts.get("instrumentation_verification") != "recording_metadata"
                else _role_listening_sentence(recommendation_role, index)
            )
            return f"{jazz_feature} {role_sentence}"
    if _is_dawn_sentimental_request(context_text):
        dawn_feature = _dawn_sentimental_feature_sentence(track_tags, recommendation_role)
        if dawn_feature:
            return f"{dawn_feature} {_role_listening_sentence(recommendation_role, index)}"
    sound_hint = _get_track_sound_hint(track)
    if sound_hint:
        sound_point, _ = sound_hint
        return (
            f"{_attach_particle(sound_point)} 자연스럽게 드러나는 곡이에요. "
            f"{_role_listening_sentence(recommendation_role, index)}"
        )
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
        "instrumental": "연주곡",
        "jazz": "재즈 계열의 리듬",
        "upbeat": "경쾌한 에너지",
        "high_energy": "높은 에너지",
        "driving": "추진력 있는 리듬",
    }
    feature_sentence = _tag_feature_sentence(track_tags, tag_labels, index)
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
    is_family_trip = _is_family_trip_request(context_text)
    if is_family_trip:
        family_openings = (
            "여행을 앞둔 설렘을 가볍게 이어가기 좋은 곡이에요.",
            "차 안에서 밝은 분위기를 이어가기 좋은 곡이에요.",
            "가족과 함께 부담 없이 곁들이기 좋은 곡이에요.",
            "이동 중 분위기에 가벼운 변화를 더하기 좋은 곡이에요.",
            "여름 여행의 들뜬 기분과 어울리는 곡이에요.",
            "목적지로 향하는 시간에 기분 좋게 곁들이기 좋은 곡이에요.",
        )
        return (
            f"{family_openings[index % len(family_openings)]} "
            f"{_role_listening_sentence(recommendation_role, index)}"
        )
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
    artist_aliases = _SPOTIFY_ARTIST_ALIASES.get((name, artist_name), ())
    title_aliases = _SPOTIFY_TRACK_ALIASES.get((name, artist_name), ())
    accepted_artists = {_canonical_track_token(artist_name)} | {
        _canonical_track_token(alias) for alias in artist_aliases
    }
    accepted_titles = {_canonical_track_token(name)} | {_canonical_track_token(alias) for alias in title_aliases}
    title_candidates = (name, *title_aliases)
    artist_candidates = (artist_name, *artist_aliases)
    queries = list(
        dict.fromkeys(
            [
                *[f'track:"{title}" artist:"{artist}"' for title in title_candidates for artist in artist_candidates],
                *[f"{title} {artist_name}" for title in title_candidates],
                *[f'track:"{title}"' for title in title_candidates],
                *title_candidates,
                artist_name,
            ]
        )
    )

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
                if _canonical_track_token(mapped.name) in accepted_titles and _canonical_track_token(mapped.artist_name) in accepted_artists:
                    mapped.reason_facts = _attach_spotify_recording_facts(
                        _build_reason_facts(name, artist_name),
                        mapped,
                    )
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


def _track_history_key(name: object, artist_name: object) -> str:
    return f"{_canonical_track_token(str(name or ''))}|{_canonical_track_token(str(artist_name or ''))}"


def _score_fallback_candidate(
    candidate: dict[str, object],
    mood: str,
    context_text: str | None,
    recent_track_keys: set[str] | None = None,
) -> int:
    score = 0
    candidate_moods = {str(item) for item in candidate.get("moods", []) if item}
    candidate_tags = {str(item) for item in candidate.get("tags", []) if item}
    candidate_name = str(candidate.get("name") or "")
    candidate_artist = str(candidate.get("artist_name") or "")
    context_tags = set(_extract_context_tags(context_text))
    context_lower = (context_text or "").lower()
    korean_rnb_request = _context_prefers_korean_rnb(context_text)
    punk_request = _context_prefers_punk_rock(context_text)
    korean_band_rock_strength = _korean_band_rock_preference_strength(context_text)
    comfort_request = _context_requests_comfort(context_text)
    sleep_request = _is_sleep_request(context_text)
    long_focus_request = _is_long_focus_request(context_text)
    calm_jazz_instrument_request = _is_calm_jazz_instrument_request(context_text)
    unhurried_flow_request = _requests_unhurried_flow(context_text)
    dawn_sentimental_request = _is_dawn_sentimental_request(context_text)
    dream_pop_synth_request = _is_dream_pop_synth_request(context_text)
    mbti_aesthetic = detect_mbti_aesthetic(context_text)
    family_trip_request = _is_family_trip_request(context_text)
    drive_request = _is_drive_request(context_text)
    explicit_genres, _, _ = _extract_genre_family_matches(context_text)
    explicit_genre_set = set(explicit_genres)
    instrument_preferences = extract_instrument_preferences(context_text)
    requested_instruments = set(instrument_preferences.get("instruments") or [])

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
    if requested_instruments:
        matched_instruments = requested_instruments & candidate_tags
        if requested_instruments.issubset(candidate_tags):
            score += 32
        elif matched_instruments:
            score += 12
        elif instrument_preferences.get("strength") == "strong":
            score -= 24
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
    if korean_band_rock_strength:
        exact_match = {"origin_kr", "artist_band", "rock"}.issubset(candidate_tags)
        if exact_match:
            score += 100 if korean_band_rock_strength in {"hard", "strong"} else 45
        elif korean_band_rock_strength == "hard":
            score -= 100
        elif korean_band_rock_strength == "strong":
            score -= 45
        if mood == "angry":
            if "high_energy" in candidate_tags:
                score += 20
            if "upbeat" in candidate_tags:
                score += 14
            if candidate_tags & {"alternative", "punk", "pop-rock"}:
                score += 8
            if "sad" in candidate_moods and not candidate_tags & {"upbeat", "high_energy"}:
                score -= 14
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
        if candidate_tags & {
            "fusion",
            "bebop",
            "hard-bop",
            "swing",
            "big-band",
            "bossa-nova",
            "latin",
            "high_energy",
            "driving",
        }:
            score -= 28
        if candidate_tags & {"jazz", "standard"}:
            score += 3
    if long_focus_request:
        # Prefer a steady, low-stimulation palette for long listening sessions.
        # Rhythm is a light variation, not a reason to promote high energy.
        focus_compatibility = _focus_feature_role_compatibility(candidate_tags, candidate_moods)
        score += round((focus_compatibility - 0.5) * 48)
        if "focused" in candidate_moods or "focused" in candidate_tags:
            score += 14
        if "calm" in candidate_moods or "calm" in candidate_tags:
            score += 12
        if candidate_tags & {"soft", "ambient", "instrumental", "groove", "rhythmic"}:
            score += 6
        if candidate_tags & {"high_energy", "driving", "aggressive", "busy", "dense", "prominent_vocal"}:
            score -= 24
        if "upbeat" in candidate_tags:
            score -= 8
        if not explicit_genre_set:
            if candidate_tags & {"soft", "ambient", "dreamy", "groove", "instrumental"}:
                score += 8
            if candidate_tags & {"hard-bop", "fusion", "swing", "big-band", "rhythmic_strong", "bebop", "fast"}:
                score -= 16
    if calm_jazz_instrument_request:
        if "jazz" in candidate_tags:
            score += 18
        if {"piano", "saxophone"}.issubset(candidate_tags):
            score += 20
        if candidate_tags & {"low_stimulation", "relaxed", "subdued"}:
            score += 18
        if candidate_tags & {"hard-bop", "fusion", "swing", "big-band", "rhythmic_strong", "high_energy"}:
            score -= 20
        if unhurried_flow_request:
            if candidate_tags & {"low_stimulation", "relaxed", "subdued"}:
                score += 20
            if candidate_tags & {"hard-bop", "fusion", "swing", "big-band", "rhythmic_strong", "high_energy"}:
                score -= 18
    if dream_pop_synth_request:
        # The user named genre and sound conditions explicitly. Apply them
        # before broad calm/dreamy affinity so piano ballads and soft R&B do
        # not substitute for dream-pop or synth-led candidates.
        if "dream-pop" in candidate_tags:
            score += 42
        if candidate_tags & {"synth", "synth-pop"}:
            score += 34
        if "atmospheric" in candidate_tags:
            score += 20
        if "spacious" in candidate_tags:
            score += 18
        if "immersive" in candidate_tags:
            score += 16
        if "dreamy" in candidate_tags:
            score += 10
        if candidate_tags & {"classical", "piano", "rnb", "soul", "soft", "warm"} and not candidate_tags & {
            "dream-pop", "synth", "synth-pop", "electronic", "atmospheric", "spacious", "immersive"
        }:
            score -= 48
    if dawn_sentimental_request:
        # This request seeks mood congruence, not emotional regulation. Favor
        # verified dreamy and sentimental cues while keeping the playlist low-key.
        if "dreamy" in candidate_tags:
            score += 30
        if "emotional" in candidate_tags:
            score += 16
        if candidate_tags & {"soft", "calm", "ambient", "rnb", "soul", "dream-pop", "hip-hop"}:
            score += 8
        if candidate_moods & {"sad", "lonely", "calm"}:
            score += 5
        if candidate_tags & {"high_energy", "driving", "punk", "pop-punk", "rock", "anime", "soundtrack"}:
            score -= 24
        sound_hint = TRACK_SOUND_HINTS.get((candidate_name.lower(), candidate_artist.lower()))
        if sound_hint and any(marker in sound_hint[0] for marker in ("빠른", "속도감", "촘촘")):
            score -= 20
    if mbti_aesthetic:
        # MBTI wording is only a weak aesthetic tie-breaker. Direct context tags,
        # activity, and constraints have already contributed larger scores above.
        matched_aesthetic_tags = candidate_tags & set(mbti_aesthetic["ranking_tags"])
        score += min(6, len(matched_aesthetic_tags) * 2)
    if family_trip_request:
        # This local tag is a reviewed Korean multi-generation familiarity cue;
        # do not substitute global Spotify popularity for it.
        if "broad_familiarity_ko" in candidate_tags:
            score += 10
        score += int(candidate.get("cross_generation_fit") or 0) * 14
        if candidate_tags & {"mainstream", "family_trip"}:
            score += 16
        if "upbeat" in candidate_tags:
            score += 8
        if _current_season() == "summer" and "summer" in candidate_tags:
            score += 6
        if candidate_tags & {"punk", "rock", "anime", "hard-bop", "bebop"}:
            score -= 12
        if "youth_skewed" in candidate_tags:
            score -= 40
    if drive_request and not family_trip_request:
        if candidate_tags & {"driving", "high_energy", "upbeat", "rock", "punk", "pop-punk", "pop"}:
            score += 16
        if candidate_tags & {"calm", "soft", "ambient", "instrumental"} and not candidate_tags & {"upbeat", "driving", "high_energy"}:
            score -= 10
        if candidate_tags & {"mainstream", "prominent_vocal"}:
            score += 4
        if "global_only" in candidate_tags:
            score -= 40
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

    if _track_history_key(candidate_name, candidate_artist) in (recent_track_keys or set()):
        score -= 36

    seed = f"{mood}|{context_text or ''}|{candidate_name}|{candidate_artist}"
    score += int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:4], 16) % 7
    return score


def _select_fallback_catalog(
    mood: str,
    context_text: str | None,
    limit: int,
    selection_guidance: dict[str, Any] | None = None,
    recent_track_keys: set[str] | None = None,
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
    explicit_genres, _, _ = _extract_genre_family_matches(context_text)
    explicit_genre_set = set(explicit_genres)
    if explicit_genres:
        exact_genre = [
            candidate
            for candidate in catalog
            if set(explicit_genres).intersection({str(tag).lower() for tag in candidate.get("tags", []) if tag})
        ]
        # Explicit genre is a candidate-pool constraint, not a late bonus.
        if len(exact_genre) >= limit:
            catalog = exact_genre
        elif exact_genre:
            catalog = exact_genre + [candidate for candidate in catalog if candidate not in exact_genre]
    instrument_preferences = extract_instrument_preferences(context_text)
    requested_instruments = set(instrument_preferences.get("instruments") or [])
    if requested_instruments:
        exact_instruments = [
            candidate
            for candidate in catalog
            if requested_instruments.issubset(
                {str(tag).lower() for tag in candidate.get("tags", []) if tag}
            )
        ]
        if len(exact_instruments) >= limit:
            catalog = exact_instruments
        elif exact_instruments:
            partial_instruments = [
                candidate
                for candidate in catalog
                if requested_instruments.intersection(
                    {str(tag).lower() for tag in candidate.get("tags", []) if tag}
                )
            ]
            catalog = exact_instruments + [candidate for candidate in partial_instruments if candidate not in exact_instruments]
    if _is_long_focus_request(context_text):
        focus_candidates = [
            candidate
            for candidate in catalog
            if (
                {"focused", "calm"}.intersection(set(candidate.get("moods", [])))
                or {"focused", "calm", "soft", "ambient", "groove", "rhythmic"}.intersection(
                    {str(tag).lower() for tag in candidate.get("tags", []) if tag}
                )
            )
            and not {"high_energy", "driving", "aggressive", "busy"}.intersection(
                {str(tag).lower() for tag in candidate.get("tags", []) if tag}
            )
            and not (
                not explicit_genre_set
                and {"hard-bop", "fusion", "swing", "big-band", "rhythmic_strong"}.intersection(
                    {str(tag).lower() for tag in candidate.get("tags", []) if tag}
                )
            )
        ]
        if len(focus_candidates) >= limit:
            catalog = focus_candidates
        elif focus_candidates:
            catalog = focus_candidates + [candidate for candidate in catalog if candidate not in focus_candidates]
    if _is_dawn_sentimental_request(context_text):
        preferred = [
            candidate
            for candidate in catalog
            if "dreamy" in {str(tag) for tag in candidate.get("tags", []) if tag}
            or (
                "emotional" in {str(tag) for tag in candidate.get("tags", []) if tag}
                and {str(tag) for tag in candidate.get("tags", []) if tag} & {"soft", "rnb", "soul"}
            )
        ]
        if preferred:
            catalog = preferred + [candidate for candidate in catalog if candidate not in preferred]
    elif _context_prefers_korean_rnb(context_text):
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
    elif _prefers_korean_band_rock(context_text):
        exact = [
            candidate
            for candidate in catalog
            if {"origin_kr", "artist_band", "rock"}.issubset(
                {str(tag).lower() for tag in candidate.get("tags", []) if tag}
            )
        ]
        # "위주" is a strong majority preference. Do not fill a six-track
        # playlist with overseas rock when the reviewed Korean-band pool is sufficient.
        if len(exact) >= limit or _korean_band_rock_preference_strength(context_text) == "hard":
            catalog = exact
        elif exact:
            catalog = exact + [candidate for candidate in catalog if candidate not in exact]

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
            -_score_fallback_candidate(candidate, mood, context_text, recent_track_keys),
            str(candidate.get("name") or ""),
        ),
    )
    unique: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    seen_artists: set[str] = set()
    generation_counts: dict[str, int] = {}
    diversify_family_trip = _is_family_trip_request(context_text)
    diversify_korean_band_rock = _prefers_korean_band_rock(context_text)
    diversify_focus_genres = _is_long_focus_request(context_text) and not explicit_genre_set
    diversify_categories = not explicit_genre_set and not diversify_family_trip and not diversify_korean_band_rock
    focus_genre_counts: dict[str, int] = {}
    candidate_pool = ranked[: max(limit * 3, limit)]
    genre_coverage_candidates: list[dict[str, object]] = []
    if {"pop", "punk"}.issubset(explicit_genre_set):
        pure_pop = next(
            (
                candidate
                for candidate in ranked
                if "pop" in {str(tag).lower() for tag in candidate.get("tags", []) if tag}
                and not {"punk", "pop-punk", "rock"}.intersection(
                    {str(tag).lower() for tag in candidate.get("tags", []) if tag}
                )
                and (
                    not _is_drive_request(context_text)
                    or {"upbeat", "high_energy", "driving"}.intersection(
                        {str(tag).lower() for tag in candidate.get("tags", []) if tag}
                    )
                )
            ),
            None,
        )
        punk_side = next(
            (
                candidate
                for candidate in ranked
                if {"punk", "rock", "pop-punk"}.intersection(
                    {str(tag).lower() for tag in candidate.get("tags", []) if tag}
                )
                and candidate is not pure_pop
            ),
            None,
        )
        genre_coverage_candidates = [candidate for candidate in (pure_pop, punk_side) if candidate]
    category_counts: dict[str, int] = {}
    for candidate in genre_coverage_candidates + candidate_pool:
        key = (str(candidate.get("name") or ""), str(candidate.get("artist_name") or ""))
        if key in seen:
            continue
        artist_key = str(candidate.get("artist_name") or "").strip().lower()
        if artist_key in seen_artists and not explicit_genre_set:
            continue
        candidate_tags = {str(tag).lower() for tag in candidate.get("tags", []) if tag}
        category = next(
            (value for value in ("jazz", "classical", "ambient", "electronic", "rnb", "rock", "jpop", "pop", "hip-hop") if value in candidate_tags),
            "other",
        )
        if diversify_categories and category_counts.get(category, 0) >= 2 and len(unique) < limit - 1:
            continue
        if diversify_focus_genres:
            candidate_tags = {str(tag).lower() for tag in candidate.get("tags", []) if tag}
            candidate_genre = next(
                (
                    genre
                    for genre in ("jazz", "classical", "rnb", "hip-hop", "ambient", "electronic", "indie", "pop")
                    if genre in candidate_tags
                ),
                "other",
            )
            if focus_genre_counts.get(candidate_genre, 0) >= 3:
                continue
        generation = str(candidate.get("generation") or "unspecified")
        # Family familiarity is playlist-level: do not let a single age group
        # consume most of the six slots merely because its songs score highest.
        generation_limit = 1 if generation == "legacy" else 4 if generation == "bridge" else 2
        if diversify_family_trip and generation != "unspecified" and generation_counts.get(generation, 0) >= generation_limit:
            continue
        seen.add(key)
        seen_artists.add(artist_key)
        selected_candidate = dict(candidate)
        selected_candidate["final_ranking_score"] = _score_fallback_candidate(candidate, mood, context_text, recent_track_keys)
        selected_candidate["selection_category"] = category
        unique.append(selected_candidate)
        category_counts[category] = category_counts.get(category, 0) + 1
        if diversify_focus_genres:
            focus_genre_counts[candidate_genre] = focus_genre_counts.get(candidate_genre, 0) + 1
        generation_counts[generation] = generation_counts.get(generation, 0) + 1
        if len(unique) >= limit:
            break
    return unique


def _fallback_tracks(
    mood: str,
    access_token: str | None = None,
    context_text: str | None = None,
    limit: int = FALLBACK_LIMIT,
    selection_guidance: dict[str, Any] | None = None,
    recent_track_keys: set[str] | None = None,
) -> list[TrackSummary]:
    constraints = extract_hard_constraints(context_text)
    # Album art is a display enhancement, never a reason to replace a more
    # sleep-suitable verified track with a lower-ranked one.
    cover_can_expand_candidates = bool(
        access_token
        and (
            (constraints["instrumental_required"] and not _is_sleep_request(context_text))
            or _prefers_korean_band_rock(context_text)
        )
    )
    # Soft RAG guidance ranks the catalog; it must not shrink the candidate
    # pool below the requested count. Hard constraints are still applied by
    # _select_fallback_catalog and validate_hard_constraints.
    catalog_limit = len(FALLBACK_LIBRARY) if (
        not access_token
        or cover_can_expand_candidates
        or _is_long_focus_request(context_text)
        or _is_dream_pop_synth_request(context_text)
    ) else limit
    catalog = _select_fallback_catalog(mood, context_text, catalog_limit, selection_guidance, recent_track_keys)
    if not access_token:
        tracks = [
            TrackSummary(
                track_id=f"fallback-{mood}-{index + 1}",
                name=str(item["name"]),
                artist_name=str(item["artist_name"]),
                display_title=str(item["name"]),
                spotify_search_title=_spotify_search_title(str(item["name"]), str(item["artist_name"])),
                reason_facts=_build_candidate_reason_facts(item, context_text, mood, recent_track_keys),
                reason=str(item.get("reason") or "지금 분위기에 맞게 골라본 곡이에요."),
                spotify_url=_build_spotify_search_url(str(item["name"]), str(item["artist_name"])),
            )
            for index, item in enumerate(catalog)
        ]
        return _enforce_korean_band_rock_selection(
            validate_hard_constraints(tracks, context_text), context_text, limit
        )

    resolved: list[TrackSummary] = []
    unresolved: list[TrackSummary] = []
    cover_first = bool(cover_can_expand_candidates)
    for index, item in enumerate(catalog):
        try:
            track = _search_track(
                access_token,
                str(item["name"]),
                str(item["artist_name"]),
                str(item.get("reason") or "지금 분위기에 맞게 골라본 곡이에요."),
            )
            if track is not None and (track.album_image_url or not cover_first):
                # Keep the curated Korean display identity. Spotify's canonical
                # title is enrichment metadata only and must not change the UI.
                display_name = str(item["name"])
                display_artist = str(item["artist_name"])
                enriched_track = track.model_copy(
                    update={
                        "name": display_name,
                        "artist_name": display_artist,
                        "display_title": display_name,
                        "spotify_search_title": _spotify_search_title(display_name, display_artist),
                        "spotify_track_name": track.spotify_track_name or track.name,
                        "canonical_recording_identity": track.canonical_recording_identity,
                        "recording_match_confidence": track.recording_match_confidence,
                        "instrumentation_source": track.instrumentation_source,
                        "reason_facts": _attach_spotify_recording_facts(
                            _build_candidate_reason_facts(item, context_text, mood, recent_track_keys),
                            track,
                        ),
                    }
                )
                resolved.append(enriched_track)
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
                    display_title=str(item["name"]),
                    spotify_search_title=_spotify_search_title(str(item["name"]), str(item["artist_name"])),
                    reason_facts=_build_candidate_reason_facts(item, context_text, mood, recent_track_keys),
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
                display_title=str(item["name"]),
                spotify_search_title=_spotify_search_title(str(item["name"]), str(item["artist_name"])),
                reason_facts=_build_candidate_reason_facts(item, context_text, mood, recent_track_keys),
                reason=str(item.get("reason") or "지금 분위기에 맞게 골라본 곡이에요."),
                spotify_url=_build_spotify_search_url(str(item["name"]), str(item["artist_name"])),
            )
        )
        if len(resolved) >= limit and not cover_first:
            break

    if cover_first and len(resolved) < limit:
        resolved.extend(unresolved[: limit - len(resolved)])
    return _enforce_korean_band_rock_selection(
        validate_hard_constraints(resolved[:limit], context_text), context_text, limit
    )


def ensure_recommendation_count(
    tracks: list[TrackSummary],
    mood: str,
    context_text: str | None,
    access_token: str | None,
    target: int = FALLBACK_LIMIT,
    selection_guidance: dict[str, Any] | None = None,
    recent_track_keys: set[str] | None = None,
) -> list[TrackSummary]:
    """Refill only with newly validated ranked candidates; never drop valid tracks for bad copy."""
    valid = validate_hard_constraints(tracks, context_text)
    if len(valid) >= target:
        return valid[:target]
    fallback = _fallback_tracks(
        mood,
        access_token=access_token,
        context_text=context_text,
        limit=target,
        selection_guidance=selection_guidance,
        recent_track_keys=recent_track_keys,
    )
    seen = {(track.name.strip().lower(), track.artist_name.strip().lower()) for track in valid}

    def append_candidates(candidates: list[TrackSummary]) -> None:
        for candidate in validate_hard_constraints(candidates, context_text):
            key = (candidate.name.strip().lower(), candidate.artist_name.strip().lower())
            if key in seen:
                continue
            valid.append(candidate)
            seen.add(key)
            if len(valid) >= target:
                break

    append_candidates(fallback)
    if len(valid) < target:
        # RAG guidance can narrow a soft-preference pool below six tracks. For
        # refill only, widen that soft pool while preserving hard constraints.
        append_candidates(
            _fallback_tracks(
                mood,
                access_token=None,
                context_text=context_text,
                limit=target,
                selection_guidance=None,
                recent_track_keys=recent_track_keys,
            )
        )
    if len(valid) < target:
        return valid[:target]
    return valid[:target]


def recommend_tracks(
    mood: str,
    access_token: str | None = None,
    limit: int = 6,
    context_text: str | None = None,
    selection_guidance: dict[str, Any] | None = None,
    recent_track_keys: set[str] | None = None,
) -> list[TrackSummary]:
    normalized_mood = _normalize_mood(mood)
    constraints = extract_hard_constraints(context_text)
    profile = MOOD_PROFILES.get(normalized_mood, MOOD_PROFILES["calm"])
    mood_label = str(profile["label"])

    # For a strong Korean-band-rock request, start from the reviewed origin/type/
    # genre catalog. Generic Spotify rock recommendations are otherwise mostly
    # overseas artists and can exhaust the six slots before filtering.
    if _korean_band_rock_preference_strength(context_text) in {"hard", "strong"}:
        return _fallback_tracks(
            normalized_mood,
            access_token=access_token or _get_app_access_token(),
            context_text=context_text,
            limit=limit,
            selection_guidance=selection_guidance,
            recent_track_keys=recent_track_keys,
        )

    if constraints["instrumental_required"]:
        # Spotify search/recommendation responses expose no verified vocals field.
        # Stay within the tagged catalog rather than returning an unverified track.
        return _fallback_tracks(
            normalized_mood,
            access_token=access_token or _get_app_access_token(),
            context_text=context_text,
            limit=limit,
            selection_guidance=selection_guidance,
            recent_track_keys=recent_track_keys,
        )

    if not access_token:
        # A client login is not required to retrieve public album artwork for
        # curated fallback tracks; use the app credential when configured.
        return _fallback_tracks(
            normalized_mood,
            access_token=_get_app_access_token(),
            context_text=context_text,
            limit=limit,
            selection_guidance=selection_guidance,
            recent_track_keys=recent_track_keys,
        )

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
                    selected = _select_diverse_track_summaries(curated_tracks, limit, recent_track_keys)
                    return _enforce_korean_band_rock_selection(selected, context_text, limit)

        if len(curated_tracks) >= limit:
            selected = _select_diverse_track_summaries(curated_tracks, limit, recent_track_keys)
            return _enforce_korean_band_rock_selection(selected, context_text, limit)

        response = _spotify_request(SPOTIFY_RECOMMENDATIONS_URL, access_token, params=query)
        tracks = response.get("tracks") or []
        mapped_tracks = [_map_track(track, mood_label, seed_genres) for track in tracks if isinstance(track, dict)]
        if _is_family_trip_request(context_text):
            mapped_tracks.sort(key=lambda track: int(track.reason_facts.get("popularity", 0)), reverse=True)
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
                    recent_track_keys=recent_track_keys,
                )
                for filler in filler_tracks:
                    key = (filler.name, filler.artist_name)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    unique_tracks.append(filler)
                    if len(unique_tracks) >= limit:
                        break
            selected = _select_diverse_track_summaries(unique_tracks, limit, recent_track_keys)
            return _enforce_korean_band_rock_selection(selected, context_text, limit)
    except SpotifyRecommendationError:
        return _fallback_tracks(normalized_mood, access_token=access_token, context_text=context_text, limit=limit, selection_guidance=selection_guidance, recent_track_keys=recent_track_keys)
    except Exception:
        return _fallback_tracks(normalized_mood, access_token=access_token, context_text=context_text, limit=limit, selection_guidance=selection_guidance, recent_track_keys=recent_track_keys)

    return _fallback_tracks(normalized_mood, access_token=access_token, context_text=context_text, limit=limit, selection_guidance=selection_guidance, recent_track_keys=recent_track_keys)
