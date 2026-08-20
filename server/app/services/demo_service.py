from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.favorite import Favorite
from app.models.mood_record import MoodRecord
from app.models.recommendation import Recommendation
from app.schemas.track import TrackSummary
from app.services.spotify_service import _get_app_access_token, _search_track


DEMO_CONTENT_VERSION = 7


def _demo_tracks(preset: str) -> list[TrackSummary]:
    presets: dict[str, list[dict[str, object]]] = {
        "focus": [
            {
                "track_id": "demo-focus-1",
                "name": "Take Five",
                "artist_name": "The Dave Brubeck Quartet",
                "album_name": "Time Out",
                "album_image_url": "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 324000,
                "reason": "재즈 특유의 리듬감이 또렷하면서도 비교적 안정적으로 이어지는 곡이에요. 너무 조용하지 않은 음악을 들으며 집중하고 싶을 때 잘 맞아요.",
            },
            {
                "track_id": "demo-focus-2",
                "name": "Blue in Green",
                "artist_name": "Miles Davis",
                "album_name": "Kind of Blue",
                "album_image_url": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 337000,
                "reason": "차분하고 여유로운 피아노와 트럼펫의 분위기가 이어지는 곡이에요. 생각이 많을 때 배경을 복잡하게 만들지 않는 음악을 듣고 싶다면 잘 어울려요.",
            },
            {
                "track_id": "demo-focus-3",
                "name": "Cantaloupe Island",
                "artist_name": "Herbie Hancock",
                "album_name": "Empyrean Isles",
                "album_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 308000,
                "reason": "재즈의 그루브와 반복되는 리듬이 비교적 선명하게 느껴지는 곡이에요. 집중하는 흐름에 약간의 활기를 더하고 싶을 때 듣기 좋아요.",
            },
            {
                "track_id": "demo-focus-4",
                "name": "Aguas de Março",
                "artist_name": "Elis Regina & Antônio Carlos Jobim",
                "album_name": "Elis & Tom",
                "album_image_url": "https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 212000,
                "reason": "브라질 음악 특유의 부드러운 보컬과 반복되는 리듬이 인상적인 곡이에요. 가볍게 리듬을 느끼면서 작업하고 싶은 순간에 잘 맞아요.",
            },
            {
                "track_id": "demo-focus-5",
                "name": "So What",
                "artist_name": "Miles Davis",
                "album_name": "Kind of Blue",
                "album_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 562000,
                "reason": "여백을 둔 트럼펫과 베이스의 앙상블이 차분한 인상을 주는 곡이에요. 긴 시간 한 가지 일에 머물며 부담 없이 음악을 듣고 싶을 때 어울려요.",
            },
            {
                "track_id": "demo-focus-6",
                "name": "Feather",
                "artist_name": "Nujabes",
                "album_name": "Modal Soul",
                "album_image_url": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 153000,
                "reason": "재즈와 힙합이 섞인 느긋한 그루브가 자연스럽게 이어지는 곡이에요. 너무 무겁지 않은 리듬을 곁에 두고 작업하고 싶을 때 듣기 좋아요.",
            },
        ],
        "jazz": [
            {
                "track_id": "demo-jazz-1",
                "name": "Sing, Sing, Sing",
                "artist_name": "Benny Goodman",
                "album_name": "The Essential Benny Goodman",
                "album_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 515000,
                "reason": "큰 편성의 스윙 리듬과 브라스가 밝고 활기차게 느껴지는 곡이에요. 지친 기분을 가볍게 환기하며 재즈를 듣고 싶을 때 잘 맞아요.",
            },
            {
                "track_id": "demo-jazz-2",
                "name": "Blue Bossa",
                "artist_name": "Joe Henderson",
                "album_name": "Page One",
                "album_image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 250000,
                "reason": "보사노바의 여유로운 리듬과 재즈의 즉흥적인 결이 함께 느껴지는 곡이에요. 복잡하지 않은 분위기에서 잠시 숨을 고르고 싶을 때 어울려요.",
            },
            {
                "track_id": "demo-jazz-3",
                "name": "Birdland",
                "artist_name": "Weather Report",
                "album_name": "Heavy Weather",
                "album_image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 355000,
                "reason": "록에 가까운 추진력과 재즈의 복잡한 앙상블이 함께 느껴지는 퓨전 재즈 곡이에요. 차분한 곡만 이어 듣기보다 조금 더 선명한 변화를 원할 때 듣기 좋아요.",
            },
            {
                "track_id": "demo-jazz-4",
                "name": "My Favorite Things",
                "artist_name": "John Coltrane",
                "album_name": "My Favorite Things",
                "album_image_url": "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 813000,
                "reason": "색소폰의 긴 호흡과 반복되는 선율이 넉넉하게 이어지는 곡이에요. 서두르지 않고 음악을 들으며 천천히 기분을 전환하고 싶을 때 잘 맞아요.",
            },
            {
                "track_id": "demo-jazz-5",
                "name": "In a Sentimental Mood",
                "artist_name": "Duke Ellington & John Coltrane",
                "album_name": "Duke Ellington & John Coltrane",
                "album_image_url": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 289000,
                "reason": "피아노와 색소폰이 낮은 온도의 선율을 주고받는 곡이에요. 말수가 적은 음악과 함께 잠시 생각을 정리하고 싶을 때 어울려요.",
            },
            {
                "track_id": "demo-jazz-6",
                "name": "Moanin'",
                "artist_name": "Art Blakey & The Jazz Messengers",
                "album_name": "Moanin'",
                "album_image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 563000,
                "reason": "블루지한 리듬과 힘 있는 브라스가 곡의 중심을 분명하게 잡아줘요. 지나치게 무겁지 않은 재즈로 분위기를 조금 바꾸고 싶을 때 듣기 좋아요.",
            },
        ],
        "drive": [
            {
                "track_id": "demo-drive-1",
                "name": "Shut Up and Dance",
                "artist_name": "WALK THE MOON",
                "album_name": "TALKING IS HARD",
                "album_image_url": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 199000,
                "reason": "밝은 기타 리프와 반복되는 팝 록 후렴이 경쾌하게 이어지는 곡이에요. 이동을 시작하며 분위기를 가볍게 띄우고 싶을 때 잘 맞아요.",
            },
            {
                "track_id": "demo-drive-2",
                "name": "Uptown Funk",
                "artist_name": "Mark Ronson ft. Bruno Mars",
                "album_name": "Uptown Special",
                "album_image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 270000,
                "reason": "펑키한 베이스와 타이트한 리듬이 선명하게 느껴지는 곡이에요. 함께 듣는 사람들과 차 안의 분위기를 생생하게 만들고 싶을 때 어울려요.",
            },
            {
                "track_id": "demo-drive-3",
                "name": "Blinding Lights",
                "artist_name": "The Weeknd",
                "album_name": "After Hours",
                "album_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 200000,
                "reason": "반복되는 신스팝 비트와 복고적인 질감이 강하게 드러나는 곡이에요. 익숙한 리듬을 따라가며 이동 시간을 즐기고 싶을 때 듣기 좋아요.",
            },
            {
                "track_id": "demo-drive-4",
                "name": "Levitating",
                "artist_name": "Dua Lipa",
                "album_name": "Future Nostalgia",
                "album_image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 203000,
                "reason": "디스코 팝의 탄력 있는 베이스와 밝은 보컬이 돋보이는 곡이에요. 가볍게 따라 부를 수 있는 음악과 함께 이동하고 싶을 때 잘 맞아요.",
            },
            {
                "track_id": "demo-drive-5",
                "name": "Are You Gonna Be My Girl",
                "artist_name": "Jet",
                "album_name": "Get Born",
                "album_image_url": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 213000,
                "reason": "거침없는 기타 리프와 직선적인 록 리듬이 두드러지는 곡이에요. 출발 직후 조금 더 선명한 활기를 느끼고 싶을 때 어울려요.",
            },
            {
                "track_id": "demo-drive-6",
                "name": "On Top of the World",
                "artist_name": "Imagine Dragons",
                "album_name": "Night Visions",
                "album_image_url": "https://images.unsplash.com/photo-1470229722913-7c0e2dbb?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 192000,
                "reason": "밝은 후렴과 손뼉을 부르는 듯한 리듬이 인상적인 곡이에요. 여행길에 가볍고 낙관적인 분위기를 더하고 싶을 때 듣기 좋아요.",
            },
        ],
        "dreamy": [
            {
                "track_id": "demo-dreamy-1",
                "name": "Midnight City",
                "artist_name": "M83",
                "album_name": "Hurry Up, We're Dreaming",
                "album_image_url": "https://images.unsplash.com/photo-1470225636490-405e5d1b5c9b?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 244000,
                "reason": "반짝이는 신스 사운드와 반복되는 리듬이 도시적인 몽환을 만들어내는 곡이에요. 현실의 속도에서 잠시 벗어난 듯한 음악을 듣고 싶을 때 잘 맞아요.",
            },
            {
                "track_id": "demo-dreamy-2",
                "name": "Enjoy the Silence",
                "artist_name": "Depeche Mode",
                "album_name": "Violator",
                "album_image_url": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 252000,
                "reason": "어두운 신스 질감과 절제된 반복 비트가 차분하게 이어지는 곡이에요. 말없이 분위기에 머물며 음악을 듣고 싶을 때 어울려요.",
            },
            {
                "track_id": "demo-dreamy-3",
                "name": "Sweet Disposition",
                "artist_name": "The Temper Trap",
                "album_name": "Conditions",
                "album_image_url": "https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 231000,
                "reason": "점층적으로 커지는 기타와 넓게 펼쳐지는 보컬이 인상적인 곡이에요. 한 장면처럼 천천히 분위기가 변하는 음악을 원할 때 듣기 좋아요.",
            },
            {
                "track_id": "demo-dreamy-4",
                "name": "Space Song",
                "artist_name": "Beach House",
                "album_name": "Depression Cherry",
                "album_image_url": "https://images.unsplash.com/photo-1519608487953-e999c86e7455?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 320000,
                "reason": "느린 드림 팝의 잔향과 겹쳐지는 보컬이 오래 남는 곡이에요. 서두르지 않고 상상에 잠길 수 있는 음악을 찾을 때 잘 맞아요.",
            },
            {
                "track_id": "demo-dreamy-5",
                "name": "Intro",
                "artist_name": "The xx",
                "album_name": "xx",
                "album_image_url": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 147000,
                "reason": "미니멀한 기타와 단순한 비트가 넓은 여백을 남기는 곡이에요. 소리가 많지 않은 몽환적인 배경을 원할 때 어울려요.",
            },
            {
                "track_id": "demo-dreamy-6",
                "name": "Wait",
                "artist_name": "M83",
                "album_name": "Hurry Up, We're Dreaming",
                "album_image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 280000,
                "reason": "천천히 부풀어 오르는 신스와 보컬이 긴 여운을 남기는 곡이에요. 음악의 잔상이 이어지는 분위기 속에서 잠시 쉬고 싶을 때 듣기 좋아요.",
            },
        ],
    }
    guidance = {
        "demo-focus-1": ("재즈 특유의 또렷한 리듬감", "안정적인 리듬과 함께 집중하고 싶은 순간"),
        "demo-focus-2": ("차분하고 여유로운 피아노와 트럼펫의 분위기", "복잡하지 않은 배경 속에서 생각을 정리하고 싶은 순간"),
        "demo-focus-3": ("선명하게 느껴지는 재즈 그루브", "집중하는 흐름에 약간의 활기를 더하고 싶은 순간"),
        "demo-focus-4": ("부드러운 보컬과 반복되는 브라질 리듬", "가볍게 리듬을 느끼며 작업하고 싶은 순간"),
        "demo-focus-5": ("여백을 둔 트럼펫과 베이스의 앙상블", "긴 시간 부담 없이 음악을 곁에 두고 싶은 순간"),
        "demo-focus-6": ("재즈와 힙합이 섞인 느긋한 그루브", "너무 무겁지 않은 리듬과 함께 작업하고 싶은 순간"),
        "demo-jazz-1": ("큰 편성의 스윙 리듬과 브라스", "지친 기분을 가볍게 환기하고 싶은 순간"),
        "demo-jazz-2": ("보사노바의 여유로운 리듬과 재즈의 즉흥적인 결", "복잡하지 않은 분위기에서 잠시 숨을 고르고 싶은 순간"),
        "demo-jazz-3": ("록의 추진력과 재즈의 복잡한 앙상블", "차분한 곡 사이에 선명한 변화를 더하고 싶은 순간"),
        "demo-jazz-4": ("색소폰의 긴 호흡과 반복되는 선율", "서두르지 않고 천천히 기분을 전환하고 싶은 순간"),
        "demo-jazz-5": ("피아노와 색소폰이 주고받는 낮은 온도의 선율", "말수가 적은 음악과 함께 생각을 정리하고 싶은 순간"),
        "demo-jazz-6": ("블루지한 리듬과 힘 있는 브라스", "지나치게 무겁지 않은 재즈로 분위기를 바꾸고 싶은 순간"),
        "demo-drive-1": ("밝은 기타 리프와 반복되는 팝 록 후렴", "이동을 시작하며 분위기를 가볍게 띄우고 싶은 순간"),
        "demo-drive-2": ("펑키한 베이스와 타이트한 리듬", "함께 듣는 사람들과 차 안의 분위기를 생생하게 만들고 싶은 순간"),
        "demo-drive-3": ("복고적인 질감의 반복되는 신스팝 비트", "익숙한 리듬을 따라가며 이동 시간을 즐기고 싶은 순간"),
        "demo-drive-4": ("디스코 팝의 탄력 있는 베이스와 밝은 보컬", "가볍게 따라 부를 수 있는 음악과 함께 이동하고 싶은 순간"),
        "demo-drive-5": ("거침없는 기타 리프와 직선적인 록 리듬", "출발 직후 조금 더 선명한 활기를 느끼고 싶은 순간"),
        "demo-drive-6": ("밝은 후렴과 손뼉을 부르는 듯한 리듬", "여행길에 가볍고 낙관적인 분위기를 더하고 싶은 순간"),
        "demo-dreamy-1": ("반짝이는 신스 사운드와 반복되는 도시적인 리듬", "현실의 속도에서 잠시 벗어나고 싶은 순간"),
        "demo-dreamy-2": ("어두운 신스 질감과 절제된 반복 비트", "말없이 분위기에 머물며 음악을 듣고 싶은 순간"),
        "demo-dreamy-3": ("점층적으로 커지는 기타와 넓게 펼쳐지는 보컬", "한 장면처럼 천천히 변하는 음악을 원하는 순간"),
        "demo-dreamy-4": ("느린 드림 팝의 잔향과 겹쳐지는 보컬", "서두르지 않고 상상에 잠길 수 있는 음악을 찾는 순간"),
        "demo-dreamy-5": ("미니멀한 기타와 단순한 비트가 남기는 여백", "소리가 많지 않은 몽환적인 배경을 원하는 순간"),
        "demo-dreamy-6": ("천천히 부풀어 오르는 신스와 보컬", "음악의 잔상이 이어지는 분위기 속에서 쉬고 싶은 순간"),
    }
    selected_tracks = presets.get(preset, presets["focus"])
    for track in selected_tracks:
        feature, role = guidance.get(track["track_id"], (None, None))
        if feature and role:
            track["reason_facts"] = {
                "primary_feature": feature,
                "recommendation_role": role,
                "tags": ["demo", preset or "focus"],
            }
    tracks = [TrackSummary.model_validate(track) for track in selected_tracks]
    access_token = _get_app_access_token()
    if not access_token:
        return tracks

    enriched_tracks: list[TrackSummary] = []
    for track in tracks:
        spotify_track = _search_track(access_token, track.name, track.artist_name, track.reason or '')
        if spotify_track is None:
            enriched_tracks.append(track)
            continue

        spotify_track.reason = track.reason
        spotify_track.reason_facts = {
            **spotify_track.reason_facts,
            **track.reason_facts,
        }
        enriched_tracks.append(spotify_track)
    return enriched_tracks


def _demo_favorite_tracks(preset: str, tracks: list[TrackSummary] | None = None) -> list[dict[str, object]]:
    tracks = tracks or _demo_tracks(preset)
    return [
        {
            "track_id": track.track_id,
            "track_name": track.name,
            "artist_name": track.artist_name,
            "album_name": track.album_name,
            "album_image_url": track.album_image_url,
            "spotify_url": track.spotify_url,
            "duration_ms": track.duration_ms,
            "mood": "focused" if preset == "focus" else "tired" if preset == "jazz" else "calm" if preset == "dreamy" else "excited",
            "reason": track.reason,
            "is_favorite": True,
        }
        for track in tracks
    ]


def seed_demo_user_content(db: Session, user_id: int, preset: str | None = None) -> None:
    preset_key = (preset or "focus").strip().lower() or "focus"
    existing_record = db.scalar(select(MoodRecord.id).where(MoodRecord.user_id == user_id).limit(1))
    existing_profile = db.scalar(
        select(Recommendation.generation_profile)
        .where(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    if existing_record is not None and isinstance(existing_profile, dict) and existing_profile.get("demo_content_version") == DEMO_CONTENT_VERSION:
        return
    if existing_record is not None:
        db.execute(delete(Favorite).where(Favorite.user_id == user_id))
        db.execute(delete(Recommendation).where(Recommendation.user_id == user_id))
        db.execute(delete(MoodRecord).where(MoodRecord.user_id == user_id))
        db.commit()

    now = datetime.now(timezone.utc)
    mood_sequences = {
        "focus": [
            ("focused", "집중하면서 듣기 좋은 차분한 재즈 음악을 추천해줘.", 0),
            ("calm", "생각을 정리하며 들을 수 있는 여유로운 재즈를 찾고 있어요.", 1),
            ("focused", "너무 조용하지 않고 리듬감이 있는 작업용 음악을 듣고 싶어요.", 2),
        ],
        "jazz": [
            ("tired", "지친 기분에 무리 없이 들을 수 있는 재즈를 추천해줘.", 0),
            ("calm", "피아노와 쿨 재즈로 차분하게 분위기를 바꾸고 싶어요.", 1),
            ("tired", "너무 무겁지 않게 기분을 환기할 수 있는 재즈가 필요해요.", 2),
        ],
        "drive": [
            ("excited", "드라이브하면서 듣기 좋은 신나는 팝을 추천해줘.", 0),
            ("happy", "차 안에서 함께 따라 부르기 좋은 곡을 듣고 싶어요.", 1),
            ("excited", "펑크와 신스팝처럼 리듬감 있는 음악이 필요해요.", 2),
        ],
        "dreamy": [
            ("calm", "현실에서 잠시 벗어난 듯한 몽환적인 신스 음악을 듣고 싶어요.", 0),
            ("calm", "공간감 있고 여운이 긴 곡을 차분하게 듣고 싶어요.", 1),
            ("calm", "드림 팝처럼 천천히 분위기가 변하는 음악을 추천해줘.", 2),
        ],
    }

    for mood, text, offset in mood_sequences.get(preset_key, mood_sequences["focus"]):
        db.add(
            MoodRecord(
                user_id=user_id,
                mood=mood,
                text=text,
                source="demo",
                created_at=now - timedelta(days=offset),
            )
        )

    demo_tracks = _demo_tracks(preset_key)
    recommendation_messages = {
        "focus": "집중이 필요한 시간에 부담스럽지 않게 이어 듣기 좋은 재즈 곡들을 골라봤어요. 차분한 분위기를 유지하면서도 너무 단조롭지 않은 곡들로 구성했어요.",
        "jazz": "스윙, 보사노바, 퓨전 재즈처럼 서로 다른 결을 가진 곡들을 골라봤어요. 지친 기분을 무겁게 만들지 않으면서 재즈의 다양한 리듬을 느낄 수 있어요.",
        "drive": "기타 리프와 펑키한 베이스, 신스팝 리듬이 살아 있는 곡들을 골라봤어요. 이동하는 동안 함께 듣고 따라 부르기 좋은 밝은 분위기로 구성했어요.",
        "dreamy": "신스와 드림 팝의 여운이 천천히 이어지는 곡들을 골라봤어요. 현실의 속도에서 잠시 벗어나 공간감 있는 음악을 듣고 싶을 때 잘 맞아요.",
    }
    recommendation_context = {
        "selected_mood": "focused" if preset_key == "focus" else "tired" if preset_key == "jazz" else "calm" if preset_key == "dreamy" else "excited",
        "user_text": mood_sequences.get(preset_key, mood_sequences["focus"])[0][1],
        "selected_vibes": {
            "focus": ["차분한", "리듬감 있는"],
            "jazz": ["여유로운", "재즈"],
            "drive": ["신나는", "리드미컬한"],
            "dreamy": ["공간감 있는", "신비로운"],
        }.get(preset_key, ["차분한", "리듬감 있는"]),
        "favorite_context": "기존에 좋아요를 누른 곡이 있는 사용자",
        "recent_mood_summary": "최근 감정 기록을 참고한 추천",
        "recent_recommendation_summary": "최근 추천 결과와 선호 곡을 참고한 추천",
        "rag_context": "음악 특징과 감정별 청취 맥락을 참고한 추천 기준",
    }

    for idx, created_days_ago in enumerate([0, 1, 2]):
        db.add(
            Recommendation(
                user_id=user_id,
                mood=recommendation_context["selected_mood"],
                query=recommendation_context["user_text"],
                message=recommendation_messages.get(preset_key, recommendation_messages["focus"]),
                selected_vibes=recommendation_context["selected_vibes"],
                context_snapshot=recommendation_context,
                rag_context=recommendation_context["rag_context"],
                llm_context=recommendation_context["rag_context"],
                generation_profile={
                    "llm_provider": "mock",
                    "demo_mode": True,
                    "demo_content_version": DEMO_CONTENT_VERSION,
                    "scenario": preset_key,
                    "track_count": len(demo_tracks),
                    "reason_source": "demo",
                },
                tracks=[track.model_dump(mode="json", exclude_none=True) for track in demo_tracks],
                created_at=now - timedelta(days=created_days_ago),
            )
        )

    for index, favorite in enumerate(_demo_favorite_tracks(preset_key, demo_tracks)):
        db.add(
            Favorite(
                user_id=user_id,
                created_at=now - timedelta(days=index),
                **favorite,
            )
        )

    db.commit()
