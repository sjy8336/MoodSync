from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.services.mbti_aesthetics import detect_mbti_aesthetic


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
    "instrumental": "연주곡",
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

_LONG_FOCUS_ROLES = [
    ("장시간 틀어두기", "노트북 앞에 오래 앉아 음악을 틀어두고 싶을 때"),
    ("차분한 흐름 유지", "긴 시간 잔잔한 재즈를 이어 듣고 싶을 때"),
    ("가벼운 리듬 더하기", "잔잔함을 유지하면서 리듬감을 조금 더하고 싶을 때"),
    ("낮은 자극으로 배경 유지", "노트북 앞에 오래 앉아 잔잔한 연주를 틀어두고 싶을 때"),
    ("단조로움 줄이기", "너무 단조롭지 않은 배경 음악을 원할 때"),
    ("긴 청취에 맞추기", "오래 이어 들어도 강한 자극을 피하고 싶을 때"),
    ("차분한 배경으로 이어 듣기", "오래 음악을 틀어두고 싶을 때"),
    ("집중 흐름에 무리 없이 맞추기", "긴 시간 잔잔한 곡을 이어 듣고 싶을 때"),
]

_CALM_JAZZ_ROLES = [
    ("지친 상태에서 차분한 재즈 듣기", "오늘 조금 지친 상태에서 자극적인 음악보다 차분하게 듣고 싶을 때"),
    ("피아노와 색소폰의 흐름 듣기", "피아노와 색소폰 연주를 천천히 듣고 싶을 때"),
    ("낮은 강도의 연주 선택", "강한 자극보다 느긋한 재즈를 찾을 때"),
    ("느긋한 재즈로 쉬기", "긴장이 남아 있어 여유 있는 음악을 듣고 싶을 때"),
    ("감성적인 연주에 머물기", "감성적인 재즈를 차분하게 듣고 싶은 순간에"),
    ("재즈의 여백 즐기기", "피아노와 색소폰이 어우러지는 흐름을 부담 없이 듣고 싶을 때"),
]

_CALM_JAZZ_RHYTHMIC_ROLES = [
    ("리듬 변화 듣기", "차분한 곡들 사이에서 리듬이 조금 더 있는 재즈를 듣고 싶을 때"),
    ("재즈의 박자감 느끼기", "느긋한 곡만 이어지지 않도록 박자감에 작은 변화를 주고 싶을 때"),
]

_CATHARTIC_KOREAN_ROCK_ROLES = [
    ("답답한 기분 강하게 환기하기", "답답한 기분을 강한 음악으로 환기하고 싶을 때"),
    ("분노의 에너지와 맞추기", "화가 아직 가라앉지 않았을 때 강한 분위기의 음악을 듣고 싶다면"),
    ("신나는 록으로 방향 바꾸기", "스트레스를 잠시 잊고 분위기를 바꾸고 싶을 때"),
    ("속이 답답할 때 텐션 올리기", "속이 답답할 때 강렬한 록으로 분위기를 바꾸고 싶을 때"),
    ("밴드 사운드에 몰입하기", "강렬한 밴드 음악에 집중해 듣고 싶을 때"),
    ("기분을 확 바꾸기", "지금의 기분을 빠르게 전환하고 싶을 때"),
]

_SLEEP_ROLES = [
    ("긴장 내려놓기", "지금 쌓인 긴장을 조금 내려놓고 싶을 때"),
    ("생각의 속도 늦추기", "생각이 계속 이어져 쉽게 잠들기 어려운 순간"),
    ("감정을 조용히 정리하기", "마음이 쉽게 가라앉지 않을 때"),
    ("생각을 가볍게 정돈하기", "머릿속에 남은 생각을 가볍게 정돈하고 싶을 때"),
    ("복잡한 생각에서 잠시 거리 두기", "여러 생각이 한꺼번에 떠오르는 순간"),
    ("휴식 분위기로 전환하기", "잠시 휴식하는 분위기로 자연스럽게 전환하고 싶을 때"),
]

_DAWN_SENTIMENTAL_ROLES = [
    ("새벽 분위기에 천천히 잠기기", "새벽 특유의 고요한 분위기에 천천히 잠기고 싶을 때"),
    ("혼자 생각에 머물기", "혼자 생각이 길어지는 순간에"),
    ("센치한 감정을 따라가기", "센치해진 감정을 억지로 바꾸지 않고 따라가고 싶을 때"),
    ("몽환적인 분위기 유지하기", "새벽의 센치한 흐름에 더 깊이 잠기고 싶을 때"),
    ("감정의 여운 이어가기", "마음에 남은 여운을 천천히 느끼고 싶을 때"),
    ("새벽의 고요함에 머물기", "새벽에 혼자 조용한 시간을 보내고 싶을 때"),
]

_FAMILY_TRIP_ROLES = [
    ("여행 출발 전 기분 끌어올리기", "여행을 떠나는 설렘을 그대로 이어가고 싶을 때"),
    ("차 안 분위기 밝게 유지하기", "이동하는 동안 차 안 분위기를 밝게 이어가고 싶을 때"),
    ("가족이 함께 즐기기", "가족과 함께 부담 없이 흥겹게 듣고 싶을 때"),
    ("이동 중 분위기 환기하기", "이동이 길어져 분위기를 가볍게 바꾸고 싶을 때"),
    ("여름 드라이브 분위기 살리기", "여름 여행 기분을 가볍게 더하고 싶을 때"),
    ("여행의 설렘 이어가기", "목적지로 향하는 시간을 즐겁게 이어가고 싶을 때"),
]

_DRIVE_ROLES = [
    ("드라이브 시작 분위기 열기", "주말 드라이브를 시작하며 신나는 곡을 듣고 싶을 때"),
    ("차 안에서 따라 부르기", "차 안에서 함께 따라 부르기 좋은 곡을 찾을 때"),
    ("팝 분위기 더하기", "도로 위에서 밝은 팝 분위기를 이어가고 싶을 때"),
    ("펑크 에너지 더하기", "강한 밴드 사운드로 드라이브 분위기를 바꾸고 싶을 때"),
    ("이동 중 리듬 변화", "이동하면서 에너지 있는 곡을 이어 듣고 싶을 때"),
    ("장거리 드라이브 기분 유지", "멀리 이동하는 동안 활기 있는 음악을 듣고 싶을 때"),
    ("조금 더 강한 사운드 듣기", "이동 중 조금 더 강한 밴드 사운드를 원할 때"),
    ("펑크 사운드로 구간 바꾸기", "장거리 이동 중 사운드를 한 번 바꾸고 싶은 구간에"),
]
_DRIVE_POP_ROLES = [
    _DRIVE_ROLES[0],
    _DRIVE_ROLES[2],
    _DRIVE_ROLES[5],
    _DRIVE_ROLES[1],
    _DRIVE_ROLES[4],
    _DRIVE_ROLES[3],
]
_DRIVE_PUNK_ROLES = [
    _DRIVE_ROLES[3],
    _DRIVE_ROLES[4],
    _DRIVE_ROLES[5],
    _DRIVE_ROLES[1],
    _DRIVE_ROLES[0],
    _DRIVE_ROLES[6],
]
_DRIVE_BRIDGE_ROLES = [
    _DRIVE_ROLES[1],
    _DRIVE_ROLES[3],
    _DRIVE_ROLES[4],
    _DRIVE_ROLES[0],
    _DRIVE_ROLES[2],
    _DRIVE_ROLES[5],
]

_DREAM_POP_SYNTH_ROLES = [
    ("몽환적인 시작 열기", "현실과 조금 떨어진 듯한 분위기에서 음악을 시작하고 싶을 때"),
    ("신스 중심 분위기 이어가기", "신스가 어우러진 사운드에 자연스럽게 몰입하고 싶은 순간에"),
    ("공간감 있는 사운드에 머물기", "소리가 넓게 퍼지는 듯한 분위기에 귀를 두고 싶을 때"),
    ("잔잔함에서 한 걸음 벗어나기", "조용하기만 한 곡보다 조금 더 밀도 있는 사운드를 찾을 때"),
    ("감성적인 흐름 이어가기", "몽환적이면서 감성적인 흐름을 이어 듣고 싶을 때"),
    ("몰입감 있는 구간 만들기", "주변과 잠시 거리를 두고 사운드에 집중하고 싶은 순간에"),
]


def _build_listening_request_context(text: str | None, selected_vibes: list[str] | None) -> dict[str, object]:
    """Extract explicit goals and limits without adding another model call."""
    raw_text = text or ""
    lowered = raw_text.lower()
    # "몰입감 있는 음악" is a sound preference, not evidence of study/work.
    # A laptop is a listening setting, not evidence that the user is studying or working.
    is_studying = any(token in raw_text or token in lowered for token in ("공부", "과제", "작업", "업무"))
    is_long_focus = any(token in raw_text or token in lowered for token in ("오래 앉", "오랫동안", "장시간", "노트북 앞")) and any(token in raw_text or token in lowered for token in ("몰입", "집중", "산만하지"))
    avoids_overstimulation = any(
        token in raw_text or token in lowered
        for token in ("소란", "시끄", "방해", "과하지", "너무 강", "자극")
    )
    is_going_well = any(token in raw_text or token in lowered for token in ("잘되고", "잘 되고", "순조", "흐름"))
    is_preparing_sleep = any(
        token in raw_text or token in lowered
        for token in ("수면", "잠들", "잠을", "잠 못", "잠자", "자고 싶", "잘 때")
    )
    is_family_trip = any(token in raw_text for token in ("가족 여행", "가족여행", "여행")) and any(
        token in raw_text for token in ("차", "자동차", "드라이브", "이동")
    )
    is_drive = any(
        token in raw_text or token in lowered
        for token in ("차 타고", "차 안", "드라이브", "도로 위", "운전", "drive", "road trip")
    )
    korean_band_rock = any(token in raw_text or token in lowered for token in ("우리나라 밴드", "국내 밴드", "한국 밴드", "korean band")) and any(
        token in raw_text or token in lowered for token in ("락", "록", "rock")
    )
    is_dawn_sentimental = any(token in raw_text or token in lowered for token in ("새벽", "늦은 밤", "밤공기", "센치")) and any(
        token in raw_text or token in lowered for token in ("감성", "몽환", "센치", "플레이리스트")
    )
    dream_pop_synth = any(token in lowered or token in raw_text for token in ("dream pop", "dream-pop", "드림 팝", "드림팝")) and any(
        token in lowered or token in raw_text for token in ("synth", "신스", "공간감", "공간 감", "atmospheric", "spatial", "immersive", "몰입감")
    )
    instrumental_required = any(
        token in lowered
        for token in ("가사가 없는", "가사 없는", "가사없이", "가사 없이", "무가사", "연주곡", "보컬 없는", "보컬이 없는", "instrumental")
    )
    explicit_jazz = any(token in raw_text or token in lowered for token in ("재즈", "jazz"))
    explicit_genres = []
    is_pop_punk_compound = any(token in lowered or token in raw_text for token in ("pop-punk", "pop punk", "팝펑크", "팝 펑크"))
    if not is_pop_punk_compound and any(token in lowered or token in raw_text for token in ("pop", "팝")):
        explicit_genres.append("pop")
    if not is_pop_punk_compound and any(token in lowered or token in raw_text for token in ("punk", "펑크")):
        explicit_genres.append("punk")
    if is_pop_punk_compound:
        explicit_genres.append("pop-punk")
    instrument_preferences = []
    if any(token in raw_text or token in lowered for token in ("피아노", "piano")):
        instrument_preferences.append("piano")
    if any(token in raw_text or token in lowered for token in ("색소폰", "saxophone", "sax")):
        instrument_preferences.append("saxophone")

    context: dict[str, object] = {
        "context": "공부 또는 작업" if is_studying else "",
        "current_state": [],
        "goal": [],
        "avoid": [],
        "priority": [],
        "hard_constraints": {"instrumental_required": instrumental_required},
        "explicit_genre": "jazz" if explicit_jazz else None,
        "explicit_genres": explicit_genres,
        "instrument_preferences": instrument_preferences,
        "mbti_aesthetic": detect_mbti_aesthetic(raw_text),
    }
    if dream_pop_synth:
        context["context"] = "드림 팝과 신스 중심의 몰입 청취"
        context["current_state"] = ["현실에서 잠시 벗어난 듯한 분위기를 원함"]
        context["goal"] = ["드림 팝과 신스 사운드 듣기", "공간감과 몰입감 있는 흐름 찾기"]
        context["avoid"] = ["공부 또는 업무 맥락", "잔잔하기만 한 피아노 또는 발라드 중심 구성"]
        context["priority"] = ["드림 팝", "신스", "공간감과 대기감", "몰입감", "몽환적·감성적 분위기"]
        context["explicit_genres"] = ["dream-pop"]
    elif explicit_jazz or instrument_preferences:
        context["context"] = "차분하게 재즈를 듣는 시간"
        context["current_state"] = ["오늘 조금 지쳐 있음", "자극적인 음악보다 여유 있는 흐름을 원함"]
        context["goal"] = ["재즈를 들으며 편안하게 쉬기", "남아 있는 긴장을 천천히 내려놓기"]
        context["avoid"] = ["공부 또는 업무 맥락", "지나치게 높은 자극"]
        context["priority"] = ["명시한 재즈 장르", "피아노와 색소폰 메타데이터", "낮은 자극", "차분한 분위기"]
    elif is_preparing_sleep:
        context["context"] = "수면 준비"
        context["current_state"] = ["수면 부족으로 피곤함", "생각이 많아 쉬기 어려움"]
        context["goal"] = ["지금 편안하게 쉬는 분위기", "생각을 잠시 내려놓기"]
        context["avoid"] = ["보컬 또는 가사", "수면에 방해되는 높은 자극"]
        context["priority"] = ["휴식에 어울리는 분위기", "낮은 자극", "연주곡" if instrumental_required else "차분한 분위기"]
    elif is_family_trip:
        context["context"] = "가족 여행의 차 안"
        context["current_state"] = ["여행을 앞두고 설레는 상태"]
        context["goal"] = ["여행 기분 살리기", "차 안 분위기 밝게 만들기", "가족이 함께 즐기기"]
        context["avoid"] = ["지나치게 공격적인 분위기", "특정 취향층에 치우친 곡", "공부 또는 업무 맥락"]
        context["priority"] = ["가족 여행과 차 안 맥락", "대중적인 친숙함", "신나는 분위기", "현재 계절"]
    elif is_drive:
        context["context"] = "주말 장거리 드라이브"
        context["current_state"] = ["주말 외출을 앞두고 설레는 상태", "도로 위에서 활기 있는 음악을 듣고 싶은 상태"]
        context["goal"] = ["차 안 분위기를 신나게 만들기", "따라 부르기 좋은 에너지 있는 음악 듣기"]
        context["avoid"] = ["지나치게 차분하거나 잠 오는 분위기", "공부 또는 업무 맥락"]
        context["priority"] = ["명시한 팝·펑크 장르", "드라이브 적합성", "에너지", "기분 전환"]
    elif korean_band_rock:
        context["context"] = "국내 밴드 록 감정 전환"
        context["current_state"] = ["화나는 일이 있어 답답하고 분노가 남아 있음"]
        context["goal"] = ["강한 음악으로 기분 전환하기", "신나는 록으로 스트레스 받는 감정의 방향 바꾸기"]
        context["avoid"] = ["공부 또는 업무 맥락", "지나치게 잔잔한 곡", "해외 록 중심의 구성"]
        context["priority"] = ["한국 밴드 록", "강렬하고 신나는 분위기", "분노와 스트레스 전환"]
    elif is_dawn_sentimental:
        context["context"] = "새벽 감성 플레이리스트"
        context["current_state"] = ["센치하고 사색적인 감정", "혼자 조용히 음악을 듣고 싶은 상태"]
        context["goal"] = ["새벽의 감성적인 분위기에 머물기", "몽환적이고 감성적인 흐름 이어 듣기"]
        context["avoid"] = ["공부 또는 업무 맥락", "감정을 억지로 바꾸려는 설명", "지나치게 높은 자극"]
        context["priority"] = ["몽환적인 분위기", "감성적인 분위기", "새벽의 고요한 청취 맥락", "사색적인 흐름"]
    elif is_long_focus:
        context["context"] = "장시간 이어 듣는 집중 세션"
        context["current_state"] = ["노트북 앞에 오래 앉아 있을 예정", "장시간 집중이 필요한 상태"]
        context["goal"] = ["긴 시간 음악 듣기", "잔잔함 속에 가벼운 리듬감 듣기"]
        context["avoid"] = ["지나치게 높은 자극", "복잡하거나 공격적인 분위기", "쉬어가기 중심의 설명"]
        context["priority"] = ["낮은 자극", "차분한 분위기", "가벼운 리듬감", "장시간 청취 적합성"]
    elif is_studying and is_going_well:
        context["current_state"] = ["이미 집중 흐름이 이어지고 있음", "기분 좋게 몰입 중"]
        context["goal"] = ["현재 공부 흐름 유지", "적당한 활기 유지"]
    elif is_studying:
        context["goal"] = ["공부 또는 작업 흐름 유지"]
    if avoids_overstimulation:
        context["avoid"] = ["지나치게 높은 자극", "집중을 깨는 소란스러움"]
    if is_studying and avoids_overstimulation:
        context["priority"] = ["몰입 유지", "과하지 않은 활기", "높은 에너지"]
    elif selected_vibes and not context["priority"]:
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

    for key in ("tags", "moods", "sleep_ranking_factors"):
        values = facts.get(key)
        if not isinstance(values, list):
            continue
        labels = [
            _normalize_metadata_text(value)
            for value in values
            if str(value) not in {"mainstream", "family_trip", "summer", "broad_familiarity_ko"}
        ]
        cleaned = list(dict.fromkeys(label for label in labels if label))
        if cleaned:
            normalized[key] = cleaned[:4]
    provenance = facts.get("feature_provenance")
    if isinstance(provenance, dict):
        normalized["feature_provenance"] = {
            str(key): str(value)
            for key, value in provenance.items()
            if key and value
        }
    return normalized


def _family_trip_reason_anchor(facts: object, role_focus: str) -> str | None:
    """Choose one verified playlist signal so family-trip copy does not default to energy."""
    if not isinstance(facts, dict):
        return None

    tags = {str(tag).strip().lower() for tag in facts.get("tags", []) if str(tag).strip()}
    cross_generation_fit = int(facts.get("cross_generation_fit") or 0)
    has_broad_familiarity = "broad_familiarity_ko" in tags
    has_mainstream_popularity = "mainstream" in tags
    if role_focus == "차 안 분위기 밝게 유지하기" and tags & {"mainstream", "broad_familiarity_ko"}:
        return "shared_familiarity"
    if role_focus == "가족이 함께 즐기기" and has_mainstream_popularity:
        return "mainstream_popularity"
    if role_focus == "여름 드라이브 분위기 살리기":
        if cross_generation_fit >= 3:
            return "cross_generational_familiarity"
        if has_broad_familiarity:
            return "shared_familiarity"
        if has_mainstream_popularity:
            return "mainstream_popularity"
        if "summer" in tags:
            return "summer_travel"
        if "family_trip" in tags:
            return "family_travel"
    if role_focus in {"여행 출발 전 기분 끌어올리기", "이동 중 분위기 환기하기"} and tags & {"upbeat", "high_energy"}:
        return "upbeat_moment"
    if role_focus == "여행의 설렘 이어가기" and "summer" in tags:
        return "summer_travel"
    if has_broad_familiarity:
        return "shared_familiarity"
    if has_mainstream_popularity:
        return "mainstream_popularity"
    if "family_trip" in tags:
        return "family_travel"
    if "summer" in tags:
        return "summer_travel"
    if tags & {"upbeat", "high_energy"}:
        return "upbeat_moment"
    return None


def _family_trip_reason_ingredient(facts: object, role: dict[str, str]) -> dict[str, str] | None:
    """Select one playlist-level reason feature before Gemini sees generic tag summaries."""
    anchor = _family_trip_reason_anchor(facts, role.get("focus", ""))
    if not anchor:
        return None

    primary_features = {
        "shared_familiarity": "여러 사람이 비교적 익숙하게 들을 수 있는 대중적인 곡",
        "cross_generational_familiarity": "세대가 달라도 비교적 익숙하게 느낄 수 있는 곡",
        "mainstream_popularity": "대중적으로 익숙한 편인 곡",
        "summer_travel": "여름과 잘 어울리는 밝은 분위기",
        "family_travel": "친숙하게 즐길 수 있는 곡",
        "upbeat_moment": "밝고 신나는 분위기",
    }
    primary_feature = primary_features.get(anchor)
    if not primary_feature:
        return None
    return {
        "primary_feature": primary_feature,
        "feature_source": anchor,
        "secondary_feature": _family_trip_secondary_feature(facts, anchor),
        "recommendation_role": role.get("focus", ""),
    }


def _family_trip_secondary_feature(facts: object, primary_anchor: str) -> str | None:
    """Expose one additional verified signal only when it can distinguish similar reasons."""
    if not isinstance(facts, dict):
        return None

    tags = {str(tag).strip().lower() for tag in facts.get("tags", []) if str(tag).strip()}
    cross_generation_fit = int(facts.get("cross_generation_fit") or 0)
    if primary_anchor == "shared_familiarity" and cross_generation_fit >= 3:
        return "세대 간 친숙함"
    if primary_anchor == "mainstream_popularity" and "upbeat" in tags:
        return "밝고 신나는 분위기"
    if primary_anchor == "upbeat_moment" and "summer" in tags:
        return "여름 적합성"
    if primary_anchor == "summer_travel" and "mainstream" in tags:
        return "대중성"
    return None


def _dawn_sentimental_reason_ingredient(facts: object, role: dict[str, str]) -> dict[str, str] | None:
    """Keep late-night copy anchored to one verified mood feature per track."""
    if not isinstance(facts, dict):
        return None

    tags = {str(tag).strip().lower() for tag in facts.get("tags", []) if str(tag).strip()}
    moods = {str(mood).strip().lower() for mood in facts.get("moods", []) if str(mood).strip()}
    role_focus = role.get("focus", "")
    if {"piano", "instrumental"}.issubset(tags):
        feature = "피아노 중심의 연주"
        source = "piano_instrumental"
    elif {"shoegaze", "dream-pop"}.issubset(tags):
        feature = "드림 팝·슈게이즈 계열의 분위기"
        source = "shoegaze_dream_pop"
    elif {"rnb", "soul"}.issubset(tags):
        feature = "R&B/Soul 계열의 분위기"
        source = "rnb_soul"
    elif {"soft", "emotional"}.issubset(tags):
        feature = "부드럽고 감성적인 분위기"
        source = "soft_emotional"
    elif "soft" in tags:
        feature = "부드러운 분위기"
        source = "soft"
    elif "calm" in tags and role_focus == "혼자 생각에 머물기":
        feature = "차분한 분위기"
        source = "calm"
    elif "ambient" in tags:
        feature = "앰비언트 분위기"
        source = "ambient"
    elif "dreamy" in tags:
        feature = "몽환적인 분위기"
        source = "dreamy"
    elif "emotional" in tags:
        feature = "감성적인 분위기"
        source = "emotional"
    else:
        return None

    secondary_feature = None
    if source == "rnb_soul" and "calm" in moods:
        secondary_feature = "차분한 분위기"
    elif source in {"dreamy", "calm"} and moods & {"sad", "lonely"}:
        secondary_feature = "사색적인 감정"
    elif source in {"emotional", "soft_emotional"} and "soft" in tags:
        secondary_feature = "부드러운 분위기"
    return {
        "primary_feature": feature,
        "feature_source": source,
        "secondary_feature": secondary_feature,
        "feature_provenance": "track_metadata",
        "recommendation_role": role.get("focus", ""),
    }


def _long_focus_reason_ingredient(facts: object, role: dict[str, str]) -> dict[str, str] | None:
    """Choose one concrete focus-track fact before falling back to mood wording."""
    if not isinstance(facts, dict):
        return None

    tags = {str(tag).strip().lower() for tag in facts.get("tags", []) if str(tag).strip()}
    verified_instruments = {
        str(item).strip().lower()
        for item in facts.get("recording_instruments", [])
        if str(item).strip()
    }
    instrumentation_verified = facts.get("instrumentation_verification") == "recording_metadata"
    factual_feature_count = sum(
        tag in tags
        for tag in ("bossa-nova", "jazz", "standard", "piano", "ambient", "instrumental", "rhythmic_light", "groove")
    ) + len(verified_instruments)

    if "bossa-nova" in tags:
        feature = "보사노바 계열의 가벼운 리듬이 이어지는 재즈 연주"
        source = "bossa_nova_light_rhythm"
    elif instrumentation_verified and "jazz" in tags and {"piano", "saxophone"}.issubset(verified_instruments):
        feature = "피아노와 색소폰이 함께하는 재즈 연주"
        source = "verified_piano_sax_jazz"
    elif {"jazz", "standard"}.issubset(tags):
        feature = "스탠더드 재즈 연주"
        source = "jazz_standard"
    elif {"jazz", "instrumental"}.issubset(tags):
        feature = "재즈 연주"
        source = "jazz_instrumental"
    elif {"piano", "instrumental"}.issubset(tags):
        feature = "피아노 중심의 연주"
        source = "piano_instrumental"
    elif {"ambient", "instrumental"}.issubset(tags):
        feature = "앰비언트 연주"
        source = "ambient_instrumental"
    elif "ambient" in tags:
        feature = "앰비언트 분위기"
        source = "ambient"
    elif "rhythmic_light" in tags or "groove" in tags:
        feature = "가벼운 리듬감"
        source = "light_rhythm"
    else:
        return None

    return {
        "primary_feature": feature,
        "feature_source": source,
        "feature_provenance": "recording_metadata" if instrumentation_verified else "track_metadata",
        "factual_feature_count": factual_feature_count,
        "distinctive_feature_available": source not in {"jazz_instrumental", "ambient", "light_rhythm"},
        "recommendation_role": role.get("focus", ""),
    }


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
        (("emotional", "soft"), "감성적이면서 부드럽게 이어지는 분위기"),
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


def _normalize_selected_vibes(selected_vibes: list[str] | None) -> list[str]:
    """Keep requested moods separate from verified track features in copy input."""
    vibe_map = {
        "몽환적인": "dreamy",
        "감성적인": "emotional",
        "잔잔한": "calm",
        "차분한": "calm",
        "따뜻한": "warm",
        "신나는": "upbeat",
        "몰입되는": "focused",
        "위로되는": "comfort",
        "강렬한": "high_energy",
        "기분 전환되는": "upbeat",
    }
    return list(dict.fromkeys(vibe_map.get(vibe, vibe) for vibe in selected_vibes or []))


def _recommendation_role(
    mood: str,
    index: int,
    context_text: str | None = None,
    selected_vibes: list[str] | None = None,
    reason_facts: object | None = None,
) -> dict[str, str]:
    request_context = _build_listening_request_context(context_text, selected_vibes)
    has_study_flow = request_context["context"] in {"공부 또는 작업", "장시간 이어 듣는 집중 세션"}
    is_sleep_context = request_context["context"] == "수면 준비"
    is_family_trip_context = request_context["context"] == "가족 여행의 차 안"
    is_drive_context = request_context["context"] == "주말 장거리 드라이브"
    is_dream_pop_synth_context = request_context["context"] == "드림 팝과 신스 중심의 몰입 청취"
    is_korean_rock_context = request_context["context"] == "국내 밴드 록 감정 전환"
    is_dawn_sentimental_context = request_context["context"] == "새벽 감성 플레이리스트"
    is_long_focus_context = request_context["context"] == "장시간 이어 듣는 집중 세션"
    is_calm_jazz_context = request_context.get("explicit_genre") == "jazz" and bool(request_context.get("instrument_preferences"))
    if is_dream_pop_synth_context:
        roles = _DREAM_POP_SYNTH_ROLES
    elif is_sleep_context:
        raw_tags = reason_facts.get("tags", []) if isinstance(reason_facts, dict) else []
        tags = {str(tag).strip().lower() for tag in raw_tags if str(tag).strip()}
        # Keep all sleep roles distinct while using verified tags to choose the
        # most natural role order for each track's musical character.
        if {"ambient", "dreamy"}.issubset(tags):
            role_order = (1, 5, 4, 0, 3, 2)
        elif {"classical", "piano"}.issubset(tags):
            role_order = (0, 2, 3, 4, 5, 1)
        elif {"jazz", "standard"}.issubset(tags):
            role_order = (4, 0, 3, 1, 5, 2)
        else:
            role_order = tuple(range(len(_SLEEP_ROLES)))
        roles = [_SLEEP_ROLES[role_index] for role_index in role_order]
    elif is_family_trip_context:
        roles = _FAMILY_TRIP_ROLES
    elif is_drive_context:
        raw_tags = reason_facts.get("tags", []) if isinstance(reason_facts, dict) else []
        tags = {str(tag).strip().lower() for tag in raw_tags if str(tag).strip()}
        if "pop-punk" in tags:
            roles = _DRIVE_BRIDGE_ROLES
        elif "punk" in tags or "rock" in tags:
            roles = _DRIVE_PUNK_ROLES
        elif "pop" in tags or tags & {"dance-pop", "synth-pop"}:
            roles = _DRIVE_POP_ROLES
        else:
            roles = _DRIVE_ROLES
    elif is_korean_rock_context:
        roles = _CATHARTIC_KOREAN_ROCK_ROLES
    elif is_dawn_sentimental_context:
        roles = _DAWN_SENTIMENTAL_ROLES
    elif is_long_focus_context:
        raw_tags = reason_facts.get("tags", []) if isinstance(reason_facts, dict) else []
        tags = {str(tag).strip().lower() for tag in raw_tags if str(tag).strip()}
        # Only assign the rhythm-variation role when the selected track has a
        # supplied rhythm/groove fact. Unknown tracks stay in neutral roles.
        if tags & {"groove", "rhythmic", "rhythmic_light", "bossa-nova"}:
            roles = _LONG_FOCUS_ROLES
        else:
            roles = [
                _LONG_FOCUS_ROLES[0],
                _LONG_FOCUS_ROLES[1],
                _LONG_FOCUS_ROLES[3],
                _LONG_FOCUS_ROLES[6],
                _LONG_FOCUS_ROLES[5],
                _LONG_FOCUS_ROLES[7],
            ]
    elif is_calm_jazz_context:
        raw_tags = reason_facts.get("tags", []) if isinstance(reason_facts, dict) else []
        tags = {str(tag).strip().lower() for tag in raw_tags if str(tag).strip()}
        if tags & {"rhythmic_strong", "odd_meter", "hard-bop", "bebop", "fusion", "swing", "big-band"}:
            roles = [_CALM_JAZZ_RHYTHMIC_ROLES[index % len(_CALM_JAZZ_RHYTHMIC_ROLES)]]
        elif tags & {"rhythmic_light", "groove", "bossa-nova"}:
            roles = [("가벼운 재즈 리듬 더하기", "차분한 분위기를 유지하면서 가벼운 리듬을 더하고 싶을 때")]
        else:
            roles = _CALM_JAZZ_ROLES
    elif has_study_flow:
        roles = _STUDY_FLOW_ROLES
    else:
        roles = _RECOMMENDATION_ROLES.get(mood, _RECOMMENDATION_ROLES["focused"])
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

    request_context = _build_listening_request_context(context_text, selected_vibes)
    is_family_trip = request_context["context"] == "가족 여행의 차 안"
    is_dawn_sentimental = request_context["context"] == "새벽 감성 플레이리스트"
    is_long_focus = request_context["context"] == "장시간 이어 듣는 집중 세션"
    track_lines = []
    for index, track in enumerate(tracks):
        role = _recommendation_role(
            mood,
            index,
            context_text,
            selected_vibes,
            track.get("reason_facts"),
        )
        ingredient = (
            _family_trip_reason_ingredient(track.get("reason_facts"), role)
            if is_family_trip
            else _dawn_sentimental_reason_ingredient(track.get("reason_facts"), role)
            if is_dawn_sentimental
            else _long_focus_reason_ingredient(track.get("reason_facts"), role)
            if is_long_focus
            else None
        )
        default_music_feature = _build_music_feature_summary(track.get("reason_facts"))
        track_lines.append(
            {
                "track_id": str(track.get("track_id") or ""),
                "name": str(track.get("name") or ""),
                "artist_name": str(track.get("artist_name") or ""),
                "album_name": str(track.get("album_name") or ""),
                "verified_reason_facts": _normalize_reason_facts(track.get("reason_facts")),
                "track_actual_features": _normalize_reason_facts(track.get("reason_facts")),
                "track_features_for_reason": _normalize_reason_facts(track.get("reason_facts")),
                # Context-specific ingredients prevent a generic tag from
                # dominating every reason in a playlist.
                "music_feature": ingredient["primary_feature"] if ingredient else default_music_feature,
                "recommendation_role": role,
                "family_trip_reason_anchor": ingredient["feature_source"] if ingredient else None,
                "dawn_sentimental_reason_anchor": ingredient["feature_source"] if is_dawn_sentimental and ingredient else None,
                "long_focus_reason_anchor": ingredient["feature_source"] if is_long_focus and ingredient else None,
                "reason_ingredient": ingredient,
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
        "mbti_aesthetic is an optional user-provided aesthetic shorthand, not a personality diagnosis or a factual preference. It is a soft tie-breaker only: never let it override explicit user requests, hard constraints, selected moods, or listening context. Never mention an MBTI type in the summary or reasons.\n"
        "For summaries, prioritize the user's direct situation and selected moods before listening context and MBTI aesthetics. If the user selected dreamy and emotional, keep both ideas represented naturally; do not replace emotional with an MBTI-derived word such as introspective or sentimental. Do not use two overlapping action verbs such as '잠겨 머물기'.\n"
        "Treat explicit limits such as 'too noisy', 'distracting', 'not too much', or 'too stimulating' as hard constraints. For studying, prefer maintaining the current flow and moderate energy over merely saying a track is exciting.\n"
        "When relevant, connect each reason to one distinct goal or avoid condition, such as keeping a study flow, adding modest energy, avoiding excessive stimulation, or preventing a sluggish mood. Do not repeat the same condition for all tracks.\n"
        "For family-trip car requests, preserve the supplied family/travel context in every reason. Use a different role for each track: departure excitement, keeping the car lively, easy shared listening, refreshing a long drive, a seasonal travel mood, or carrying the anticipation toward the destination. Do not reuse study, work, focus, or rest contexts.\n"
        "For a family-trip summary, describe the future trip plainly in two sentences: the service selected bright songs for tomorrow's family trip, then mention summer travel and listening together in the car. Do not say the songs will add to excitement, fill time, complete a mood, or invite the user to enjoy them.\n"
        "For a family-trip playlist, reason_ingredient is code-selected verified planning data. Sentence 1 must use its primary_feature. Use secondary_feature only when present and only to distinguish a repeated primary feature; never make an attribute list or noun chain. Its recommendation_role is for sentence 2 only. shared_familiarity may be described conservatively as '여러 사람이 비교적 익숙하게 들을 수 있는 대중적인 곡'; cross_generational_familiarity as familiarity across generations; mainstream_popularity only as '대중적으로 익숙한 편인 곡'; summer_travel as a summer-compatible mood; family_travel as a family-trip fit; upbeat_moment as a bright or lively moment. Do not force every song to be described as a cross-generational classic. Mention broad familiarity only for its supplied feature source. Do not use upbeat_moment for more than two tracks, and never write '경쾌한 에너지' or create raw metadata combinations such as '높은 에너지가 펼쳐져요'.\n"
        "For every family-trip reason, use this exact separation: sentence 1 describes only the track's verified music_feature or family_trip_reason_anchor and ends with a period. Sentence 2 describes only the user's future travel listening moment through recommendation_role. Never join these clauses with a comma, '이어져', '-면서', or a relative modifier. For example, write '밝고 신나는 분위기가 느껴지는 곡이에요. 이동이 길어질 때 분위기를 가볍게 바꾸고 싶다면 잘 어울려요.' Do not write '밝고 신나는 분위기가 이어져 이동 중...' or '높은 에너지가 느껴지는 여름 여행 기분'.\n"
        "Do not use recommendation_role itself as the first sentence. Also compare the two family-trip sentences before returning: if both describe the same idea such as travel excitement, keeping the car bright, or a summer mood, rewrite sentence 1 with the supplied primary feature instead.\n"
        "In family-trip reasons, do not reuse energy as the default first-sentence feature. Distribute the six verified anchors across shared familiarity, family travel fit, summer travel fit, and at most two upbeat moments. The second sentence must not explain metadata; it must only explain the distinct travel role.\n"
        "If verified metadata says high energy while the user wants less stimulation, do not claim that the track is not stimulating. Describe it only as a fit for a brief refresh or a moment when the user wants to raise the tempo.\n"
        "Do not say that music 'helps immersion' or 'helps concentration'. Never claim that music prevents distraction, maintains concentration, or improves study efficiency.\n"
        "For a long laptop/focus session, the summary must aggregate only supplied playlist facts: low-stimulation or calm anchors, piano or ambient tracks when supplied, and a light-rhythm track only when at least one supplied track has light_rhythm_fit. When the playlist mixes jazz, piano instrumentals, and ambient, do not represent the entire playlist with only a partial pair such as '피아노와 앰비언트 연주곡'. Use a broader natural aggregate such as calm instrumentals, then separately note that a light-rhythm track is included. Never describe the entire playlist as having a steady rhythm. Prefer a two-part summary such as calm instrumentals plus '가벼운 리듬감이 느껴지는 곡도 함께 담았어요'; do not write the awkward phrase '지나치지 않은 리듬감'. Do not write '집중할 수 있도록', '몰입을 유지', '집중력을 높여', '흐름을 유지시켜', or '산만함을 막아'.\n"
        "A laptop alone does not mean study or work. Unless user_text explicitly mentions study, work, assignments, coding, or tasks, do not write 공부, 작업, 업무, 과제, 코딩, or 해야 할 일 in a long-focus summary or reason.\n"
        "For a long laptop/focus reason, sentence 1 must use a verified genre, instrumentation, or rhythm fact before a generic mood. Sentence 2 must describe a direct listening moment such as keeping music on during a long laptop session, wanting a calm instrumental, wanting background music that is not too monotonous, or wanting a little rhythm. Do not write '한 가지 흐름에 머물며', '음악이 앞에 나서지 않는 분위기로', '일정한 간격으로', or '차분하게 가라앉는'. If sentence 1 says '차분한', sentence 2 must not repeat '차분한'.\n"
        "For a long laptop/focus playlist, reason_ingredient is code-selected factual planning data. Sentence 1 must use its primary_feature instead of replacing it with '차분한', '잔잔한', '몽환적인', or '감성적인'. For example, preserve a supplied bossa-nova light-rhythm feature, a jazz-standard feature, a piano-instrumental feature, or an ambient-instrumental feature. Use piano plus saxophone only when the supplied ingredient says that exact instrumentation was verified.\n"
        "For focus reasons, factual accuracy is more important than sentence diversity. If several tracks have only the same verified piano-and-instrumental facts, it is acceptable for their first sentences to be similar. Do not invent dreamy, emotional, warm, lyrical, classical, or other decorative traits merely to vary those sentences; use the distinct listening role only in sentence 2.\n"
        "For focus copy, do not pad simple facts with '연주가 이어지는 곡', '연주가 흐르는 곡', or '분위기가 흐르는 곡'. Write a short direct sentence such as '피아노 중심의 연주곡이에요.' When sentence 1 says ambient, sentence 2 must not repeat the same calm or quiet descriptor; keep it as the current long-listening situation instead.\n"
        "When a long-focus reason_ingredient has distinctive_feature_available=true, do not shorten it to a generic mood or genre sentence. Use the supplied primary_feature naturally. When it is false, stay short and accurate rather than adding poetic or inferred detail.\n"
        "For an ambiguous title such as '1/1', use only the supplied exact identity and verified_reason_facts. Do not infer an artist, album, piano, synthesizer, loop, or recording detail from the title. When exact instrumentation is verified, use its most distinctive one or two facts; otherwise use a short genre or supplied-tag description instead.\n"
        "When user_text contains a concrete life context such as job searching, an interview, a breakup, or exhaustion, name that context naturally in message.\n"
        "Keep the user's timeline accurate. Words such as '어제', '어젯밤', and '지난밤' describe a past cause, not the current time. If the user says they want to rest now, describe the current context as '지금 잠시 쉬려는 상황', never as if it is currently night unless the user explicitly says so.\n"
        "For job-search anxiety, acknowledge the pressure or uncertainty of the job search and focus on settling the mind or regaining a steady pace.\n"
        "Do not describe anxiety as needing speed, driving rhythm, or productivity unless the user explicitly asks for focus, work tempo, or energy.\n"
        "Do not repeat the literal label '원하는 분위기' in the output.\n"
        "Do not quote user_text verbatim or wrap it in quotation marks.\n"
        "Paraphrase the user's intent instead of copying the exact sentence.\n"
        "track_reasons should be an array with the same length as the tracks list.\n"
        "Each track_reason item must be an object with track_id, reason, and used_fact_keys.\n"
        "Each reason must contain exactly 2 natural Korean sentences, specific to the track, and should reflect the user's text. Do not use semicolons, line fragments, or a single long sentence in place of this structure.\n"
        "music_feature is an application-normalized phrase based only on verified metadata. Use it as the musical feature instead of listing individual tags.\n"
        "When sleep_ranking_factors is provided, it contains the verified tags/moods that raised this track in the sleep ranking. Use one relevant factor naturally in the first sentence, not as an internal label or a raw list.\n"
        "For sleep/rest requests, instrumental or jazz alone is never evidence of low stimulation. Describe calmness, ambient, piano, dreamy, or classical qualities only when those facts are supplied. Do not claim low energy, a soft rhythm, or a lack of stimulation unless verified_reason_facts supports it.\n"
        "For sleep/rest requests, do not use the same 'calm instrumental, good for sleep' logic for every track. Let the verified music_feature and the internal recommendation_role form one connected reason: piano can support unwinding or gently organizing remaining thoughts, ambient/dreamy can support slowing racing thoughts or shifting into rest, and calm jazz can support taking a little distance from crowded thoughts only when those facts are supplied.\n"
        "Across the six sleep reasons, vary the second-sentence situation. Do not mechanically repeat '차분한 분위기', '조용히', '잠들기 전', '잠자리를 준비', or '듣기 좋아요'. Never promise that music will make the user sleep or resolve their emotions; describe a fitting listening moment instead.\n"
        "Unless the user explicitly says the current time is night or bedtime, keep sleep/rest reasons time-neutral. Never infer '밤에', '하루의 끝에', '잠들기 전', or '오늘 하루를 마무리하며' from sleep alone. When the user mentions a past night but wants to rest now, use phrases such as '잠시 눈을 감고 쉬고 싶을 때', '편안하게 눈을 붙이고 싶을 때', or '잠시 휴식하는 분위기로 전환하고 싶을 때'.\n"
        "Use only verified metadata and do not expand soft/calm into claims such as '자극이 없다', '집중을 방해하지 않는다', or '잠을 유도한다'. Avoid abstract agentic subjects such as '구성이 분위기를 이끈다' or '특징이 감성을 만든다'; write direct descriptions such as '조용한 분위기의 연주가 자연스럽게 이어지는 곡이에요'.\n"
        "Do not use '자극 없이', '~가 담긴', or '~가 만들어줘요' in track reasons. They either overstate the metadata or sound like a data description. For example, write '부드러운 피아노 선율이 잔잔하게 이어지는 연주곡이에요' instead of '부드러운 피아노 연주가 담긴 클래식 곡이에요'.\n"
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
        "Also avoid mixed duplicate condition forms such as '~하면 ... ~할 때' or '~할 때 ... ~하고 싶을 때'. Use one clear condition, for example: '여러 생각이 한꺼번에 떠오를 때, 잠시 다른 흐름에 마음을 두고 쉬어가고 싶다면 잘 어울려요.'\n"
        "Do not connect a purpose infinitive to an evaluation as in '~하기 위해 듣기 좋아요'. Write '잠시 긴장을 내려놓으며 듣기 좋아요' or '~고 싶을 때 잘 어울려요' instead.\n"
        "When using verbs such as '정리하며' or '가라앉히며', name what is being handled. For example, write '복잡한 마음을 천천히 정리하며 듣기 좋습니다', not just '차분히 정리하며 듣기 좋습니다'.\n"
        "Do not state that music resolves or gives comfort to the user, such as '위로를 받을 수 있어요'. Prefer a listening context like '조용히 쉬어가고 싶은 순간에 잘 어울려요'.\n"
        "The first sentence must be different for every track. Use each track's supplied music_feature rather than copying another track's opening.\n"
        "For family-trip copy, do a final lexical check: never repeat a nearby word such as '기분을 기분 좋게', '밝은 분위기를 밝게', or '이어지는 ... 이어가고'. Do not use '곁들이기 좋아요' more than once across the six reasons. Spread natural endings such as '듣기 좋아요', '잘 맞아요', and '함께 즐기기 좋아요'; do not end every reason with '잘 어울려요'.\n"
        "For drive requests, use only the current road-trip context: driving, car listening, singalong intent, upbeat energy, and the supplied genres. Never use study, work, focus, immersion, task, pace-maintenance, or stale Korean-band-origin roles unless the current text explicitly contains them.\n"
        "Treat '팝과 펑크', '팝, 펑크', and '팝이랑 펑크' as two explicit genre axes, pop and punk. Treat '팝펑크' or 'pop-punk' as the single pop-punk genre. Do not collapse the former into pop-punk.\n"
        "For drive reasons, keep sentence 2 tied to the car/road-trip moment. Use roles such as opening a weekend drive, singalong listening, bright pop on the road, strong punk-band sound, or changing the rhythm during a long drive. Do not mention studying or maintaining a work flow.\n"
        "For drive summaries and reasons, do not claim that music raises the user's tension or mood, fills the drive, or adds excitement. Avoid '텐션을 높여주다', '기분을 끌어올려주다', '흥겨움을 더해주다', '에너지를 더해주다', and '매력을 담은 곡'. Describe the selected sound and the listening moment instead.\n"
        "For an explicit dream-pop + synth + spatial/immersive request, treat dream pop, synth/electronic sound, atmospheric/spacious traits, and immersion as the current request only. Never reuse study, work, task, productivity, focus-maintenance, rest, or sleep contexts. Sentence 1 must use a supplied actual track feature: ambient/electronic for an ambient bridge, dream pop for a dream-pop track, synth-pop/electronic for a synth track, and shoegaze only when supplied. Never call ambient a dream-pop track. Do not copy user_desired_moods into sentence 1 unless the matching trait is in track_actual_features.\n"
        "For that request, use Korean genre names naturally: '앰비언트', never '엠비언트'. Do not use '대기감', '스페이시한 공간감', '깊이감', '감정적인 여운', or phrases that say a sound adds an emotional effect. Do not claim shoegaze, synth, spatial sound, instruments, bass, guitar, keyboard, reverb, layering, or rhythmic details unless the exact feature appears in track_actual_features.\n"
        "For that request, avoid literary copy such as '아스라이 퍼지는', '마음에 스며드는', '곁에 머무는', '깊이 번지는', '감성을 품은', '분위기에 귀를 두다', '흐름에 머물다', '감성적인 흐름', '분위기의 결', or '사운드의 결'. Use plain listening situations in sentence 2 instead. If sentence 1 already says dreamy/dream pop, spacious, calm, emotional, or a genre, sentence 2 must not repeat that same trait; connect it to a different current listening role such as wanting a little distance from daily life or wanting music that is not merely quiet.\n"
        "For that dream-pop request, keep sentence 2 as a distinct listening role: opening an unreal atmosphere, following synth-led sound, staying with spacious sound, moving beyond a merely quiet section, sustaining an emotional dream-pop flow, or entering a denser shoegaze section. Do not write raw pairs such as '감정적인 분위기 및 몽환적인 분위기', and do not use '듣고 싶을 때 듣기 좋아요'.\n"
        "For a dream-pop + synth summary, describe the selected aggregate without promising escape or immersion. Do not say '현실에서 벗어나 몰입할 수 있도록', '깊이 빠져들기 좋은', or any equivalent outcome claim. Mention only the verified playlist mix, such as dream pop plus ambient/electronic or synth-related tracks, and use conversational Korean haeyo체. Never write '채워드릴게요', '들려드릴게요', '선사할게요', or an invitation such as '빠져보세요'.\n"
        "For a dawn-sentimental request, interpret words such as '새벽', '센치', and 'INFP 감성' as a late-night, introspective aesthetic. Do not infer a personality trait or claim that a personality type prefers a genre. This request seeks emotional congruence, not recovery: never use study, work, tasks, focus, productivity, rest, healing, tension relief, or mood-improvement roles. Keep the late-night context even if the current clock is not dawn. Prefer dreamy, emotional, soft, calm, ambient, or R&B/Soul facts only when supplied.\n"
        "For every dawn-sentimental reason, keep two sentences: first only verified track traits, then a distinct role such as lingering in the dawn mood, following a sentimental feeling, or staying with a lingering thought. Do not use '잠시 쉬어가며 듣기 좋아요' in this context. Translate emotional metadata naturally as '감성적인', '여운이 있는', or '차분한' only when verified; never write the unnatural phrase '감정적인 분위기이'.\n"
        "For a dawn-sentimental playlist, reason_ingredient is code-selected verified planning data. Sentence 1 must use its primary_feature as a natural track description. When its secondary_feature is present, combine it only when the two form one natural phrase; never make an attribute list. Sentence 2 must use recommendation_role only as the user's late-night listening moment, never as study, work, recovery, or rest advice.\n"
        "user_desired_moods is a ranking preference, and track_actual_features is factual metadata for one track. Never copy a desired mood into sentence 1 unless that same trait appears in track_actual_features. MBTI aesthetic data is preference-only, never a track fact. Across a late-night playlist, distribute verified features such as R&B/Soul, dream pop/shoegaze, piano/instrumental, ambient, soft, calm, emotional, or dreamy when supplied; do not describe every track as dreamy or quiet.\n"
        "Avoid vague filler such as '감성적으로 다가와요', '은은하게 번져요', '포근하게 이어져요', '마음에 스며들어요', '깊은 결', or '감정의 온도' when a verified genre, mood, or instrumentation can be stated instead. For a verified genre, describe the genre directly and do not soften it with unsupported adjectives.\n"
        "For family-trip familiarity claims, match the supplied feature_source exactly: mainstream_popularity means only '대중적인 곡' or '많은 사람에게 알려진 편인 곡'; shared_familiarity may say '여러 사람이 비교적 익숙하게 들을 수 있는 대중적인 곡'; only cross_generational_familiarity may say '세대가 달라도 비교적 익숙하게 느낄 수 있는 곡'. Never turn these into an analysis report such as '대중성이 돋보여요', and never combine familiarity with mood as '친숙한 분위기' or '대중성 높은 분위기'.\n"
        "Avoid unnatural family-trip collocations including '기분을 더하다', '분위기가 골고루 담겨 있다', and '대중성이 돋보이다'. For an upbeat feature, write a direct phrase such as '밝고 활기찬 분위기가 또렷한 곡이에요.' Keep the feature sentence and the travel-role sentence separate.\n"
        "Before returning family-trip copy, check Korean noun modifiers: write '밝은 분위기의 곡' rather than '밝은 분위기 곡'. Never write malformed compounds such as '분위기 곡', '에너지 곡', or '대중성 곡'. If two upbeat tracks occur in one playlist, keep their first sentences meaningfully distinct: one may use '밝고 신나는 분위기', while another may use '흥겹고 활기찬 분위기'.\n"
        "Before returning, compare the two sentences and remove a repeated core idea. For example, if the first sentence says the study flow should not change, the second must not repeat that same study-flow idea; use a distinct role such as a light refresh instead.\n"
        "Do not use abstract or mechanical phrases such as '에너지가 채워지는 느낌', '~할 때 적당해요', '~하기 알맞아요', or '분위기가 다가와요'.\n"
        "Also avoid '에너지가 분위기를 채워준다', '템포를 살려준다', '에너지가 조화롭게 흘러간다', '분위기를 조화롭게 만든다', and '~할 때 유용하다'. Use direct everyday Korean such as '밝고 경쾌한 분위기가 가볍게 이어지는 곡이에요' or '~하고 싶을 때 잘 어울려요'.\n"
        "Avoid generic reasons that could fit every song. State one supplied music_feature in the first sentence and connect it to the track's distinct recommendation_role in the second, without inventing music details.\n"
        "Do not say '머릿속의 결과'; say '결과에 대한 생각'. Do not say '편안하게 머물며 듣기'; prefer '부담 없이 듣기' or '편안하게 이어 듣기'.\n"
        "Do not use redundant phrases such as '진행되는 전개' or '이어지는 흐름'.\n"
        "Never add arrangement, progression, vocals, rhythm, instruments, lyrics, BPM, or production details unless they appear in verified_reason_facts. With only soft/warm-style metadata, describe only the supplied atmosphere naturally.\n"
        "Keep a natural sentence even if another track uses a similar safe expression; do not force awkward variation.\n"
        "The message is a recommendation summary, not an instruction. Do not tell the user to do something with endings like '보세요', '쉬어가세요', or '들어보세요'. Say that the service selected songs instead.\n"
        "Use conversational Korean haeyo체 throughout every track reason: prefer '곡이에요', '잘 맞아요', and '듣기 좋아요'. Do not mix in formal endings such as '곡입니다', '좋습니다', '어울립니다', or '합니다'.\n"
        "The summary must describe the selected songs, not instruct the user. Never end it with '들어보세요', '즐겨보세요', '채워보세요', '만끽해 보세요', or '느껴보세요'.\n"
        "Keep internal planning separate from user-facing copy. Never mention metadata availability, recording validation, confidence, ranking, candidate filtering, fallback use, penalties, coverage, or the fact that an instrument was not inferred. The summary should say only what kind of songs were selected and how they fit the user's listening situation.\n"
        "For calm jazz requests, describe the playlist naturally with supplied musical facts such as a calm jazz focus or a lighter rhythmic variation. Never explain that some instruments were unverified or that stronger-rhythm tracks were intentionally limited.\n"
        "Do not say the music soothes the user's body or mind, such as '몸과 마음을 달래며'. Describe only the current rest context and the songs selected for it.\n"
        "In the summary, do not use overlapping anxiety words such as '초조' and '조급' together; choose one clear expression.\n"
        "Use only verified_reason_facts as factual grounding for musical claims.\n"
        "used_fact_keys must list the verified_reason_facts keys used in that reason, using only sound_profile, listening_effect, tags, moods, or sleep_ranking_factors.\n"
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
        "user_desired_moods": _normalize_selected_vibes(selected_vibes),
        "user_preferences_for_context": {
            "selected_mood": mood,
            "desired_moods": _normalize_selected_vibes(selected_vibes),
            "listening_context": request_context["context"],
        },
        "mbti_aesthetic_for_ranking": request_context.get("mbti_aesthetic"),
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
        valid_fact_keys = {"sound_profile", "listening_effect", "tags", "moods", "sleep_ranking_factors"}
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
