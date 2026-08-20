from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.favorite import Favorite
from app.models.mood_record import MoodRecord
from app.models.recommendation import Recommendation
from app.schemas.track import TrackSummary


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
                "reason": "집중을 깨지 않으면서도 리듬감을 살려줘요.",
            },
            {
                "track_id": "demo-focus-2",
                "name": "Blue in Green",
                "artist_name": "Miles Davis",
                "album_name": "Kind of Blue",
                "album_image_url": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 337000,
                "reason": "과하게 흔들지 않고 몰입을 이어가게 해줘요.",
            },
            {
                "track_id": "demo-focus-3",
                "name": "Cantaloupe Island",
                "artist_name": "Herbie Hancock",
                "album_name": "Empyrean Isles",
                "album_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 308000,
                "reason": "집중 상태를 유지하면서도 그루브를 조금 더해줘요.",
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
                "reason": "스윙의 활기와 큰 편성이 바로 느껴져요.",
            },
            {
                "track_id": "demo-jazz-2",
                "name": "Blue Bossa",
                "artist_name": "Joe Henderson",
                "album_name": "Page One",
                "album_image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 250000,
                "reason": "보사노바와 재즈의 결이 부드럽게 이어져요.",
            },
            {
                "track_id": "demo-jazz-3",
                "name": "Birdland",
                "artist_name": "Weather Report",
                "album_name": "Heavy Weather",
                "album_image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 355000,
                "reason": "퓨전 재즈의 전개를 바로 테스트하기 좋아요.",
            },
        ],
        "calm": [
            {
                "track_id": "demo-calm-1",
                "name": "Clair de Lune",
                "artist_name": "Claude Debussy",
                "album_name": "Suite bergamasque",
                "album_image_url": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 300000,
                "reason": "차분한 밤공기처럼 잔잔하게 내려앉아요.",
            },
            {
                "track_id": "demo-calm-2",
                "name": "Sunset Lover",
                "artist_name": "Petit Biscuit",
                "album_name": "Presence",
                "album_image_url": "https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 195000,
                "reason": "부드러운 전자 질감으로 새벽 감성을 살려줘요.",
            },
            {
                "track_id": "demo-calm-3",
                "name": "Rhubarb",
                "artist_name": "Aphex Twin",
                "album_name": "Selected Ambient Works",
                "album_image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 240000,
                "reason": "앰비언트의 여백이 생각을 천천히 가라앉혀줘요.",
            },
        ],
        "emotional": [
            {
                "track_id": "demo-emotional-1",
                "name": "Someone Like You",
                "artist_name": "Adele",
                "album_name": "21",
                "album_image_url": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 285000,
                "reason": "감정선이 선명해서 테스트하기 쉬워요.",
            },
            {
                "track_id": "demo-emotional-2",
                "name": "Fix You",
                "artist_name": "Coldplay",
                "album_name": "X&Y",
                "album_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 294000,
                "reason": "위로하는 흐름과 고조가 자연스럽게 이어져요.",
            },
            {
                "track_id": "demo-emotional-3",
                "name": "To Build a Home",
                "artist_name": "The Cinematic Orchestra",
                "album_name": "Ma Fleur",
                "album_image_url": "https://images.unsplash.com/photo-1470225636490-405e5d1b5c9b?w=200&q=80",
                "spotify_url": "https://open.spotify.com",
                "duration_ms": 410000,
                "reason": "서정적인 분위기를 더 길게 끌고 가요.",
            },
        ],
    }
    return [TrackSummary.model_validate(track) for track in presets.get(preset, presets["focus"])]


def _demo_favorite_tracks(preset: str) -> list[dict[str, object]]:
    tracks = _demo_tracks(preset)
    return [
        {
            "track_id": track.track_id,
            "track_name": track.name,
            "artist_name": track.artist_name,
            "album_name": track.album_name,
            "album_image_url": track.album_image_url,
            "spotify_url": track.spotify_url,
            "duration_ms": track.duration_ms,
            "mood": "focused" if preset == "focus" else "calm" if preset == "calm" else "sad" if preset == "emotional" else "excited",
            "reason": track.reason,
            "is_favorite": True,
        }
        for track in tracks
    ]


def seed_demo_user_content(db: Session, user_id: int, preset: str | None = None) -> None:
    preset_key = (preset or "focus").strip().lower() or "focus"
    existing_record = db.scalar(select(MoodRecord.id).where(MoodRecord.user_id == user_id).limit(1))
    if existing_record is not None:
        return

    now = datetime.now(timezone.utc)
    mood_sequences = {
        "focus": [
            ("focused", "데모 테스트: 집중 모드로 흘러가는지 확인 중이에요.", 0),
            ("calm", "데모 테스트: 집중과 차분함의 경계도 확인해요.", 1),
            ("focused", "데모 테스트: 재즈와 로파이가 같이 반응하는지 보고 있어요.", 2),
        ],
        "jazz": [
            ("focused", "데모 테스트: 스윙 재즈 반응 확인 중이에요.", 0),
            ("calm", "데모 테스트: 보사노바와 쿨 재즈가 부드럽게 이어지는지 확인해요.", 1),
            ("excited", "데모 테스트: 퓨전 재즈까지 잘 분리되는지 보고 있어요.", 2),
        ],
        "calm": [
            ("calm", "데모 테스트: 밤공기 같은 잔잔함을 보고 있어요.", 0),
            ("lonely", "데모 테스트: 외로움과 위로 사이의 결을 확인해요.", 1),
            ("tired", "데모 테스트: 지친 감정이 너무 무겁지 않게 풀리는지 봐요.", 2),
        ],
        "emotional": [
            ("sad", "데모 테스트: 감정이 바로 드러나는지 확인해요.", 0),
            ("lonely", "데모 테스트: 외로움에서 위로로 넘어가는 흐름을 보고 있어요.", 1),
            ("anxious", "데모 테스트: 불안한 감정도 무리 없이 다루는지 확인해요.", 2),
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
        "focus": "집중 테스트용 데모 추천이에요. 재즈와 로파이를 섞어서 흐름이 보이게 했어요.",
        "jazz": "재즈 테스트용 데모 추천이에요. 스윙, 보사노바, 퓨전의 차이를 볼 수 있게 구성했어요.",
        "calm": "차분한 데모 추천이에요. 잔잔함과 여백 중심으로 구성했어요.",
        "emotional": "감성 테스트용 데모 추천이에요. 감정선이 잘 드러나도록 골랐어요.",
    }
    recommendation_context = {
        "selected_mood": "focused" if preset_key == "focus" else "calm" if preset_key == "calm" else "sad" if preset_key == "emotional" else "focused",
        "user_text": f"{preset_key} 데모 시나리오",
        "selected_vibes": ["데모"],
        "favorite_context": "데모 전용 샘플 데이터",
        "recent_mood_summary": "최근 기록이 자동으로 채워진 데모 상태예요.",
        "recent_recommendation_summary": "데모 추천 흐름이 미리 준비돼 있어요.",
        "rag_context": "데모 지식 베이스: 실제 입력 없이도 흐름을 확인할 수 있어요.",
    }

    for idx, created_days_ago in enumerate([0, 1]):
        db.add(
            Recommendation(
                user_id=user_id,
                mood=recommendation_context["selected_mood"],
                query=recommendation_context["user_text"],
                message=recommendation_messages.get(preset_key, recommendation_messages["focus"]),
                selected_vibes=["데모", preset_key],
                context_snapshot=recommendation_context,
                rag_context=recommendation_context["rag_context"],
                llm_context=recommendation_context["rag_context"],
                generation_profile={
                    "llm_provider": "gemini",
                    "demo_mode": True,
                    "scenario": preset_key,
                    "track_count": len(demo_tracks),
                    "reason_source": "demo",
                },
                tracks=[track.model_dump(mode="json", exclude_none=True) for track in demo_tracks],
                created_at=now - timedelta(days=created_days_ago),
            )
        )

    for index, favorite in enumerate(_demo_favorite_tracks(preset_key)):
        db.add(
            Favorite(
                user_id=user_id,
                created_at=now - timedelta(days=index),
                **favorite,
            )
        )

    db.commit()
