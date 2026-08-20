from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.graphs.recommendation_graph import (
    _apply_recommendation_copy,
    _mentions_unsupported_music_detail,
    _repeats_time_clause,
    _is_safe_recommendation_message,
    _uses_disallowed_infinitive_pattern,
    _uses_repetitive_or_abstract_language,
    _uses_unnatural_recommendation_language,
    _uses_formal_recommendation_style,
)
from app.schemas.track import TrackSummary
from app.services.gemini_service import (
    _build_music_feature_summary,
    _build_listening_request_context,
    _normalize_reason_facts,
    _parse_json_content,
    _recommendation_role,
    generate_recommendation_copy,
)
from app.services.mbti_aesthetics import MBTI_AESTHETIC_PRESETS, detect_mbti_aesthetic
from app.services.spotify_service import (
    _fallback_tracks,
    _enforce_korean_band_rock_selection,
    _search_track,
    _korean_band_rock_preference_strength,
    _select_fallback_catalog,
    _track_history_key,
    build_selection_debug,
    build_recommendation_message,
    build_track_reason,
    extract_hard_constraints,
    extract_instrument_preferences,
    is_verified_instrumental,
    recommend_tracks,
)


class GeminiRecommendationCopyTests(unittest.TestCase):
    def test_fallback_selection_spreads_categories_within_ranked_pool(self) -> None:
        catalog = _select_fallback_catalog(
            "focused",
            "여러 장르를 섞되 너무 산만하지 않은 집중 음악이 필요해요.",
            6,
        )
        categories = {str(item.get("selection_category")) for item in catalog}

        self.assertEqual(len(catalog), 6)
        self.assertGreaterEqual(len(categories), 3)

    def test_recent_tracks_receive_a_selection_penalty(self) -> None:
        recent = {_track_history_key("Take Five", "The Dave Brubeck Quartet")}
        catalog = _select_fallback_catalog(
            "focused",
            "집중할 때 듣기 좋은 음악을 추천해줘.",
            6,
            recent_track_keys=recent,
        )

        self.assertEqual(len(catalog), 6)
        self.assertNotEqual(catalog[0]["name"], "Take Five")

    def test_focus_request_resets_genre_and_does_not_reuse_jazz_pool(self) -> None:
        text = (
            "오늘은 노트북 앞에서 오래 앉아 있을 예정이라, 너무 산만하지 않고 "
            "몰입이 이어지는 음악이 필요해요. 잔잔하지만 리듬감은 조금 있었으면 좋겠어요."
        )
        catalog = _select_fallback_catalog("focused", text, 6)
        debug = build_selection_debug(text, [])
        jazz_count = sum("jazz" in set(item.get("tags", [])) for item in catalog)

        self.assertIsNone(debug["current_request_genre"])
        self.assertTrue(debug["genre_state_reset"])
        self.assertFalse(debug["previous_candidate_pool_reused"])
        self.assertLessEqual(jazz_count, 3)

    def test_long_focus_request_does_not_use_break_role_or_study_context(self) -> None:
        text = (
            "오늘은 노트북 앞에서 오래 앉아 있을 예정이라, 너무 산만하지 않고 "
            "몰입이 이어지는 음악이 필요해요. 잔잔하지만 리듬감은 조금 있었으면 좋겠어요."
        )
        catalog = _select_fallback_catalog("focused", text, 6)
        self.assertEqual(len(catalog), 6)
        self.assertNotIn("Feel It Still", {str(item["name"]) for item in catalog})
        self.assertNotIn("sleepless in ______", {str(item["name"]) for item in catalog})

    def test_long_focus_demotes_busy_bebop_and_prominent_vocal_tracks(self) -> None:
        text = (
            "오늘은 노트북 앞에서 오래 앉아 있을 예정이라, 너무 산만하지 않고 "
            "몰입이 이어지는 음악이 필요해요. 잔잔하지만 리듬감은 조금 있었으면 좋겠어요."
        )
        catalog = _select_fallback_catalog("focused", text, 6)
        by_name = {str(item["name"]): item for item in catalog}

        self.assertNotIn("Donna Lee", by_name)
        if "Brave Shine" in by_name:
            self.assertLess(float(by_name["Brave Shine"].get("final_ranking_score", 0)), 20)
        if "Into The Night" in by_name:
            self.assertLess(float(by_name["Into The Night"].get("final_ranking_score", 0)), 20)

    def test_long_focus_keeps_a_small_light_rhythm_variation(self) -> None:
        text = (
            "오늘은 노트북 앞에서 오래 앉아 있을 예정이라, 너무 산만하지 않고 "
            "몰입이 이어지는 음악이 필요해요. 잔잔하지만 리듬감은 조금 있었으면 좋겠어요."
        )
        catalog = _select_fallback_catalog("focused", text, 6)
        light_rhythm_count = sum(
            bool({"groove", "rhythmic", "rhythmic_light", "bossa-nova"}.intersection(item.get("tags", [])))
            for item in catalog
        )

        self.assertGreaterEqual(light_rhythm_count, 2)
        self.assertLessEqual(light_rhythm_count, 3)

    def test_explicit_jazz_and_instrument_request_controls_fallback_catalog(self) -> None:
        text = (
            "오늘은 조금 지쳐서 재즈를 듣고 싶어요. 너무 자극적이지 않고, "
            "피아노와 색소폰이 천천히 흐르면서 긴장을 풀어주는 곡이면 좋겠어요."
        )
        catalog = _select_fallback_catalog("tired", text, 6)
        preferences = extract_instrument_preferences(text)

        self.assertEqual(preferences["instruments"], ["piano", "saxophone"])
        self.assertEqual(preferences["strength"], "strong")
        self.assertEqual(len(catalog), 6)
        self.assertTrue(all("jazz" in item.get("tags", []) for item in catalog))
        self.assertTrue(
            all({"piano", "saxophone"}.issubset(set(item.get("tags", []))) for item in catalog)
        )

    def test_jazz_reasons_do_not_claim_unverified_recording_instruments(self) -> None:
        text = (
            "오늘은 조금 지쳐서 재즈를 듣고 싶어요. 너무 자극적이지 않고, "
            "피아노와 색소폰이 천천히 흐르면서 긴장을 풀어주는 곡이면 좋겠어요."
        )
        tracks = recommend_tracks("tired", context_text=text)
        reasons = [
            build_track_reason(track, "tired", text, index, _recommendation_role("tired", index, text, reason_facts=track.reason_facts))
            for index, track in enumerate(tracks)
        ]

        self.assertTrue(all(track.reason_facts.get("instrumentation_verification") is None for track in tracks))
        self.assertTrue(all("피아노와 색소폰" not in reason for reason in reasons))
        self.assertTrue(all(track.reason_facts.get("jazz_ranking_factors") for track in tracks))

    def test_korean_band_rock_request_prefers_verified_local_band_catalog(self) -> None:
        text = "오늘 너무 화나는 일이 있었어서 스트레스 풀고 싶어. 우리나라 밴드 락음악 위주로 추천해줘."
        catalog = _select_fallback_catalog("angry", text, 6)
        exact_matches = [
            {"origin_kr", "artist_band", "rock"}.issubset(set(item.get("tags", [])))
            for item in catalog
        ]

        self.assertEqual(_korean_band_rock_preference_strength(text), "strong")
        self.assertEqual(len(catalog), 6)
        self.assertEqual(sum(exact_matches), 6)
        self.assertNotIn("Green Day", {str(item["artist_name"]) for item in catalog})

    def test_korean_band_rock_roles_do_not_leak_study_context(self) -> None:
        text = "오늘 너무 화나는 일이 있었어서 스트레스 풀고 싶어. 우리나라 밴드 락음악 위주로 추천해줘."
        roles = [_recommendation_role("angry", index, text) for index in range(6)]
        role_text = " ".join(f"{role['focus']} {role['situation_angle']}" for role in roles)

        self.assertIn("분노", role_text)
        self.assertNotIn("공부", role_text)
        self.assertNotIn("해야 할 일", role_text)
        self.assertNotIn("집중이 흔들", role_text)

    def test_strong_korean_band_preference_removes_foreign_tracks_when_exact_pool_is_full(self) -> None:
        text = "오늘 너무 화나는 일이 있었어서 스트레스 풀고 싶어. 우리나라 밴드 락음악 위주로 추천해줘."
        exact = [
            TrackSummary(track_id=str(index), name=f"KR {index}", artist_name="Band", reason_facts={"tags": ["origin_kr", "artist_band", "rock"]})
            for index in range(6)
        ]
        foreign = TrackSummary(track_id="foreign", name="Foreign", artist_name="Overseas", reason_facts={"tags": ["rock"]})

        selected = _enforce_korean_band_rock_selection(exact[:3] + [foreign] + exact[3:], text, 6)

        self.assertEqual(len(selected), 6)
        self.assertTrue(all(track.artist_name == "Band" for track in selected))

    def test_json_parser_keeps_a_valid_object_before_trailing_model_text(self) -> None:
        parsed = _parse_json_content('{"message":"ok","track_reasons":[]}\nGenerated successfully.')

        self.assertEqual(parsed, {"message": "ok", "track_reasons": []})

    def test_internal_seed_or_tag_wording_falls_back_to_a_safe_reason(self) -> None:
        track = TrackSummary(
            track_id="track-1",
            name="Sleepless in Seoul",
            artist_name="10CM",
            reason_facts={"selection_seed_genres": ["sleepless in ______"]},
        )

        tracks, reason_map = _apply_recommendation_copy(
            [track],
            {
                "track_reasons": [
                    {
                        "track_id": "track-1",
                        "reason": "이 곡은 sleepless in ______ 시드 장르를 기반으로 구성되었습니다. 불안을 덜어줘요.",
                        "used_fact_keys": ["selection_seed_genres"],
                    }
                ]
            },
            "anxious",
            "취업 준비가 뜻대로 되지 않아 불안해요.",
        )

        self.assertEqual(reason_map, {})
        self.assertNotIn("시드", tracks[0].reason or "")

    def test_reason_metadata_translates_tags_and_drops_invalid_seed_values(self) -> None:
        facts = _normalize_reason_facts(
            {
                "tags": ["dreamy", "soft", "warm"],
                "moods": ["calm"],
                "selection_seed_genres": ["sleepless in ______"],
            }
        )

        self.assertEqual(facts["tags"], ["몽환적인 분위기", "부드러운 분위기", "따뜻한 분위기"])
        self.assertEqual(facts["moods"], ["차분한 분위기"])
        self.assertNotIn("selection_seed_genres", facts)

    def test_music_feature_combines_related_tags_into_one_natural_phrase(self) -> None:
        summary = _build_music_feature_summary({"tags": ["dreamy", "calm"]})

        self.assertEqual(summary, "몽환적이고 차분하게 가라앉는 분위기")
        self.assertNotIn("분위기와", summary or "")

    def test_study_request_context_prioritizes_flow_over_stimulation(self) -> None:
        context = _build_listening_request_context(
            "오늘 공부가 너무 잘되고 있어. 너무 소란스러우면 방해되니까 적당히 어울리게 추천해줘.",
            ["신나는", "몰입되는"],
        )

        self.assertEqual(context["context"], "공부 또는 작업")
        self.assertIn("현재 공부 흐름 유지", context["goal"])
        self.assertIn("집중을 깨는 소란스러움", context["avoid"])
        self.assertEqual(context["priority"], ["몰입 유지", "과하지 않은 활기", "높은 에너지"])
        self.assertEqual(_build_music_feature_summary({"tags": ["upbeat", "high_energy"]}), "밝고 활기찬 분위기")

    def test_study_flow_request_uses_contextual_roles_instead_of_anxiety_roles(self) -> None:
        text = "오늘 공부가 너무 잘되고 있어. 너무 소란스러우면 방해되니까 적당히 어울리게 추천해줘."
        roles = [_recommendation_role("happy", index, text, ["신나는", "몰입되는"]) for index in range(6)]
        focuses = {role["focus"] for role in roles}

        self.assertIn("현재 공부 흐름 유지", focuses)
        self.assertIn("적당한 활기 더하기", focuses)
        self.assertNotIn("생각의 속도를 늦추기", focuses)
        self.assertNotIn("현실적인 고민에서 거리 두기", focuses)

    def test_family_trip_context_uses_travel_roles_not_study_roles(self) -> None:
        text = "내일 가족 여행을 가요. 지금 계절에 맞는 차에서 듣기 좋은 유명한 신나는 노래 추천해줘."
        context = _build_listening_request_context(text, ["신나는", "기분 전환되는"])
        roles = [_recommendation_role("excited", index, text, ["신나는", "기분 전환되는"]) for index in range(6)]
        role_text = " ".join(role["focus"] for role in roles)

        self.assertEqual(context["context"], "가족 여행의 차 안")
        self.assertIn("대중적인 친숙함", context["priority"])
        self.assertIn("여행 출발 전 기분 끌어올리기", role_text)
        self.assertNotIn("공부", role_text)
        self.assertNotIn("몰입", role_text)

    def test_family_trip_roles_cover_distinct_playlist_moments(self) -> None:
        text = "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘."
        roles = [_recommendation_role("excited", index, text) for index in range(6)]

        self.assertEqual(len({role["focus"] for role in roles}), 6)
        self.assertTrue(all("공부" not in role["situation_angle"] for role in roles))

    def test_family_trip_summary_uses_future_trip_and_plain_language(self) -> None:
        message = build_recommendation_message(
            "excited",
            "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘.",
            6,
        )

        self.assertIn("내일 가족과 함께 떠나는", message)
        self.assertIn("신나는 곡", message)
        self.assertNotIn("채워줄 거예요", message)

    def test_family_trip_summary_rejects_marketing_effect_language(self) -> None:
        text = "내일 가족 여행을 가요. 차에서 들을 신나는 노래 추천해줘."

        self.assertFalse(
            _is_safe_recommendation_message(
                "내일 떠나는 가족 여행의 설렘을 더해줄 밝은 곡들로 채웠습니다.", text
            )
        )

    def test_family_trip_fallback_reasons_do_not_share_one_opening(self) -> None:
        text = "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘."
        reasons = [
            build_track_reason(
                TrackSummary(track_id=str(index), name="Unknown", artist_name="Artist", reason_facts={}),
                "excited",
                text,
                index,
                _recommendation_role("excited", index, text),
            )
            for index in range(6)
        ]
        openings = {reason.split(". ", 1)[0] for reason in reasons}

        self.assertEqual(len(openings), 6)
        self.assertTrue(all("공부" not in reason and "몰입" not in reason for reason in reasons))

    def test_family_trip_fallback_uses_multiple_ranking_signals_before_energy(self) -> None:
        text = "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘."
        tags_by_index = [
            ["upbeat", "high_energy", "family_trip"],
            ["upbeat", "mainstream", "broad_familiarity_ko", "family_trip"],
            ["upbeat", "mainstream", "broad_familiarity_ko", "family_trip"],
            ["upbeat", "high_energy", "family_trip"],
            ["upbeat", "summer", "family_trip"],
            ["upbeat", "mainstream", "family_trip"],
        ]
        reasons = [
            build_track_reason(
                TrackSummary(
                    track_id=str(index),
                    name=f"Song {index}",
                    artist_name="Artist",
                    reason_facts={"tags": tags},
                ),
                "excited",
                text,
                index,
                _recommendation_role("excited", index, text),
            )
            for index, tags in enumerate(tags_by_index)
        ]

        self.assertLessEqual(sum("신나는 분위기" in reason.split(".", 1)[0] for reason in reasons), 2)
        self.assertIn("대중적으로 익숙한 편인 곡", reasons[2])
        self.assertIn("여름의 밝은 분위기", reasons[4])

    def test_single_sentence_gemini_reason_falls_back_to_two_sentence_copy(self) -> None:
        track = TrackSummary(track_id="track-1", name="Song", artist_name="Artist", reason_facts={"tags": ["upbeat"]})
        recommendation_copy = {
            "track_reasons": [
                {
                    "track_id": "track-1",
                    "reason": "밝고 신나는 분위기가 이어져 이동 중 차 안 분위기를 밝게 이어가고 싶을 때 듣기 좋아요.",
                    "used_fact_keys": ["tags"],
                }
            ]
        }

        tracks, reason_map = _apply_recommendation_copy(
            [track], recommendation_copy, "excited", "내일 가족 여행을 가요. 차에서 들을 신나는 노래 추천해줘."
        )

        self.assertFalse(reason_map)
        self.assertEqual(len([sentence for sentence in tracks[0].reason.split(".") if sentence.strip()]), 2)

    def test_malformed_feature_context_compound_falls_back(self) -> None:
        track = TrackSummary(track_id="track-1", name="Song", artist_name="Artist", reason_facts={"tags": ["upbeat"]})
        recommendation_copy = {
            "track_reasons": [
                {
                    "track_id": "track-1",
                    "reason": "높은 에너지를 지닌 여름 여행 기분 좋은 곡이에요. 가족과 이동할 때 잘 어울려요.",
                    "used_fact_keys": ["tags"],
                }
            ]
        }

        _, reason_map = _apply_recommendation_copy(
            [track], recommendation_copy, "excited", "내일 가족 여행을 가요. 차에서 들을 신나는 노래 추천해줘."
        )

        self.assertFalse(reason_map)

    def test_family_trip_rejects_energy_when_primary_feature_is_not_energy(self) -> None:
        track = TrackSummary(
            track_id="track-1",
            name="Song",
            artist_name="Artist",
            reason_facts={"tags": ["upbeat", "mainstream", "broad_familiarity_ko", "family_trip"]},
        )
        recommendation_copy = {
            "track_reasons": [
                {
                    "track_id": "track-1",
                    "reason": "경쾌한 에너지가 돋보이는 곡이에요. 가족과 함께 이동할 때 잘 어울려요.",
                    "used_fact_keys": ["tags"],
                }
            ]
        }
        leading_tracks = [
            TrackSummary(track_id="leading-1", name="Leading 1", artist_name="Artist", reason_facts={"tags": ["upbeat", "family_trip"]}),
            TrackSummary(track_id="leading-2", name="Leading 2", artist_name="Artist", reason_facts={"tags": ["upbeat", "family_trip"]}),
        ]

        _, reason_map = _apply_recommendation_copy(
            [*leading_tracks, track], recommendation_copy, "excited", "내일 가족 여행을 가요. 차에서 들을 신나는 노래 추천해줘."
        )

        self.assertFalse(reason_map)

    def test_family_trip_fallback_prefers_curated_mainstream_summer_tracks(self) -> None:
        text = "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘."
        tracks = recommend_tracks("excited", context_text=text)
        names = {track.name for track in tracks}

        self.assertTrue(names & {"여행을 떠나요", "해변의 여인", "아모르 파티", "붉은 노을"})
        self.assertNotIn("HUMBLE.", names)

    def test_family_trip_playlist_limits_one_generation_to_two_tracks(self) -> None:
        text = "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘."
        catalog = _select_fallback_catalog("excited", text, 6)
        generations = [str(item.get("generation") or "unspecified") for item in catalog]

        self.assertLessEqual(generations.count("legacy"), 1)
        self.assertLessEqual(generations.count("bridge"), 4)
        self.assertLessEqual(generations.count("recent"), 2)
        self.assertGreaterEqual(len(set(generations) - {"unspecified"}), 2)

    def test_family_trip_playlist_has_multiple_artists_and_an_expanded_candidate_pool(self) -> None:
        text = "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘."
        catalog = _select_fallback_catalog("excited", text, 6)

        self.assertEqual(len({str(item["artist_name"]).lower() for item in catalog}), len(catalog))
        names = {str(item["name"]) for item in catalog}
        self.assertTrue({"강남스타일", "붉은 노을", "좋은 날"} & names)
        self.assertNotIn("롤린 (Rollin')", names)
        self.assertNotIn("아주 NICE", names)
        self.assertNotIn("Levitating", names)
        self.assertNotIn("Blinding Lights", names)
        self.assertNotIn("Don't Start Now", names)
        self.assertIn("나는 나비", names)

    @patch("app.services.spotify_service._search_track")
    @patch("app.services.spotify_service._get_app_access_token", return_value="app-token")
    def test_family_trip_fallback_uses_app_token_to_enrich_album_covers(self, _mock_app_token, mock_search) -> None:
        def with_cover(_token, name, artist_name, reason):
            return TrackSummary(
                track_id=f"spotify-{name}",
                name=name,
                artist_name=artist_name,
                album_image_url="https://image.test/cover.jpg",
                reason=reason,
            )

        mock_search.side_effect = with_cover
        text = "내일 가족 여행을 가요. 차에서 다 같이 알 만한 유명한 신나는 노래 추천해줘."
        tracks = recommend_tracks("excited", context_text=text)

        self.assertTrue(tracks)
        self.assertTrue(all(track.album_image_url for track in tracks))
        self.assertTrue(mock_search.called)

    @patch("app.services.spotify_service._spotify_request")
    def test_korean_family_trip_tracks_accept_spotify_title_aliases_for_covers(self, spotify_request) -> None:
        spotify_request.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": "spotify-track",
                        "name": "Gangnam Style (강남스타일)",
                        "artists": [{"name": "PSY"}],
                        "album": {"name": "Album", "images": [{"url": "https://image.test/gangnam.jpg"}]},
                        "external_urls": {"spotify": "https://open.spotify.com/track/spotify-track"},
                    }
                ]
            }
        }

        track = _search_track("app-token", "강남스타일", "싸이", "reason")

        self.assertIsNotNone(track)
        self.assertEqual(track.album_image_url, "https://image.test/gangnam.jpg")

    @patch("app.services.spotify_service._spotify_request")
    def test_amor_fati_accepts_spaced_spotify_title_for_cover_enrichment(self, spotify_request) -> None:
        spotify_request.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": "amor-fati-track",
                        "name": "아모르 파티",
                        "artists": [{"name": "Kim Yeon Ja"}],
                        "album": {"name": "Album", "images": [{"url": "https://image.test/amor-fati.jpg"}]},
                        "external_urls": {"spotify": "https://open.spotify.com/track/amor-fati-track"},
                    }
                ]
            }
        }

        track = _search_track("app-token", "아모르 파티", "김연자", "reason")

        self.assertIsNotNone(track)
        self.assertEqual(track.album_image_url, "https://image.test/amor-fati.jpg")

    @patch("app.services.spotify_service._select_fallback_catalog")
    @patch("app.services.spotify_service._search_track")
    def test_spotify_cover_enrichment_preserves_curated_display_identity(self, mock_search, mock_catalog) -> None:
        mock_catalog.return_value = [
            {"name": "강남스타일", "artist_name": "싸이", "moods": ["happy"], "tags": ["upbeat", "family_trip"]}
        ]
        mock_search.return_value = TrackSummary(
            track_id="spotify-track",
            name="Gangnam Style (강남스타일)",
            artist_name="PSY",
            album_image_url="https://image.test/gangnam.jpg",
            spotify_url="https://open.spotify.com/track/spotify-track",
        )

        tracks = _fallback_tracks(
            "excited",
            access_token="app-token",
            context_text="내일 가족 여행을 가요. 차에서 들을 신나는 노래 추천해줘.",
            limit=1,
        )

        self.assertEqual(tracks[0].name, "강남스타일")
        self.assertEqual(tracks[0].artist_name, "싸이")
        self.assertEqual(tracks[0].display_title, "강남스타일")
        self.assertEqual(tracks[0].spotify_search_title, "Gangnam Style")
        self.assertEqual(tracks[0].spotify_track_name, "Gangnam Style (강남스타일)")
        self.assertEqual(tracks[0].album_image_url, "https://image.test/gangnam.jpg")

    def test_missing_metadata_fallback_uses_current_study_context(self) -> None:
        track = TrackSummary(track_id="track-1", name="Unknown", artist_name="Artist", reason_facts={})
        text = "오늘 공부가 너무 잘되고 있어. 너무 소란스러우면 방해되니까 적당히 어울리게 추천해줘."

        tracks, _ = _apply_recommendation_copy([track], None, "happy", text)
        reason = tracks[0].reason or ""

        self.assertIn("공부 흐름", reason)
        self.assertNotIn("현실적인 고민", reason)
        self.assertNotIn("쉬어가고 싶을 때", reason)

    def test_study_refresh_fallback_does_not_repeat_the_study_flow(self) -> None:
        text = "오늘 공부가 너무 잘되고 있어. 너무 소란스러우면 방해되니까 적당히 어울리게 추천해줘."
        tracks = [TrackSummary(track_id=f"track-{index}", name=f"Song {index}", artist_name="Artist", reason_facts={}) for index in range(6)]

        enriched_tracks, _ = _apply_recommendation_copy(tracks, None, "happy", text)
        refresh_reason = enriched_tracks[5].reason or ""

        self.assertIn("같은 분위기가 조금 지루해질 때", refresh_reason)
        self.assertEqual(refresh_reason.count("공부 흐름"), 1)

    def test_sleep_request_uses_sleep_roles_instead_of_study_roles(self) -> None:
        text = "어제 혼자 고민이 많아서 잠을 못 잤어. 지금 자고 싶은데 가사가 없는 곡으로 추천해줘."
        roles = [_recommendation_role("tired", index, text, ["잔잔한", "차분한"]) for index in range(6)]
        focuses = {role["focus"] for role in roles}

        self.assertIn("긴장 내려놓기", focuses)
        self.assertNotIn("공부 템포 유지", focuses)
        self.assertNotIn("해야 할 일", " ".join(role["situation_angle"] for role in roles))

    @patch("app.services.spotify_service._get_app_access_token", return_value=None)
    def test_sleep_summary_keeps_past_sleep_loss_separate_from_current_rest(self, _mock_app_token) -> None:
        text = "어젯밤 고민이 많아서 잠을 못 잤어. 그래서 지금 조금 자고 싶은데 가사가 없는 곡으로 추천해줘."
        tracks = recommend_tracks("tired", context_text=text)

        summary = build_recommendation_message("tired", text, len(tracks), tracks)

        self.assertIn("지금 잠시", summary)
        self.assertNotIn("잠들기 전", summary)

    def test_sleep_fallback_roles_do_not_assume_current_time_is_night(self) -> None:
        text = "어젯밤 고민이 많아서 잠을 못 잤어. 그래서 지금 조금 자고 싶어."
        roles = [_recommendation_role("tired", index, text) for index in range(6)]
        role_text = " ".join(
            f"{role['focus']} {role['situation_angle']}" for role in roles
        )

        self.assertNotIn("밤", role_text)
        self.assertNotIn("하루의 끝", role_text)
        self.assertNotIn("잠들기 전", role_text)

    def test_sleep_copy_rejects_unsupported_effect_and_data_description_phrases(self) -> None:
        self.assertTrue(_uses_unnatural_recommendation_language("부드러운 피아노 연주가 담긴 클래식 곡이에요."))
        self.assertTrue(_uses_repetitive_or_abstract_language("부드러운 분위기의 연주곡이 자극 없이 흘러가요."))
        self.assertFalse(_is_safe_recommendation_message("몸과 마음을 달래며, 잔잔한 연주곡들을 골라봤어요."))

    def test_sleep_roles_use_verified_track_metadata_without_reusing_one_role(self) -> None:
        text = "어제 고민이 많아서 잠을 못 잤어. 지금 자고 싶은데 가사가 없는 곡으로 추천해줘."
        piano_role = _recommendation_role(
            "tired", 0, text, ["잔잔한"], {"tags": ["classical", "piano", "instrumental"]}
        )
        ambient_role = _recommendation_role(
            "tired", 0, text, ["잔잔한"], {"tags": ["ambient", "dreamy", "instrumental"]}
        )
        jazz_role = _recommendation_role(
            "tired", 0, text, ["잔잔한"], {"tags": ["jazz", "standard", "instrumental"]}
        )

        self.assertEqual(piano_role["focus"], "긴장 내려놓기")
        self.assertEqual(ambient_role["focus"], "생각의 속도 늦추기")
        self.assertEqual(jazz_role["focus"], "복잡한 생각에서 잠시 거리 두기")

    @patch("app.services.spotify_service._get_app_access_token", return_value=None)
    def test_instrumental_request_filters_to_verified_catalog_tracks(self, _mock_app_token) -> None:
        text = "어제 고민이 많아 잠을 못 잤어. 잘 때 어울리는 가사가 없는 곡을 추천해줘."
        tracks = recommend_tracks("tired", context_text=text)

        self.assertTrue(extract_hard_constraints(text)["instrumental_required"])
        self.assertTrue(tracks)
        self.assertTrue(all(is_verified_instrumental(track) for track in tracks))
        self.assertNotIn("보컬", " ".join(track.name for track in tracks))

    @patch("app.services.spotify_service._search_track", return_value=None)
    @patch("app.services.spotify_service._get_app_access_token", return_value="app-token")
    def test_missing_cover_lookup_keeps_all_verified_instrumental_tracks(self, _mock_app_token, _mock_search) -> None:
        text = "잠을 못 자서 잘 때 들을 가사 없는 곡을 추천해줘."
        tracks = recommend_tracks("tired", context_text=text)

        self.assertEqual(len(tracks), 6)
        self.assertTrue(all(is_verified_instrumental(track) for track in tracks))

    @patch("app.services.spotify_service._get_app_access_token", return_value="app-token")
    @patch("app.services.spotify_service._search_track")
    def test_instrumental_request_expands_candidates_until_six_covers_exist(self, mock_search, _mock_app_token) -> None:
        text = "가사가 없는 연주곡을 추천해줘."

        def search_with_missing_initial_covers(_token, name, artist, _reason):
            if name in {"An Ending (Ascent)", "Round Midnight"}:
                return None
            return TrackSummary(
                track_id=f"spotify-{name}",
                name=name,
                artist_name=artist,
                album_image_url=f"https://example.test/{name}.jpg",
                reason_facts={"tags": ["instrumental"]},
            )

        mock_search.side_effect = search_with_missing_initial_covers
        tracks = recommend_tracks("tired", context_text=text)

        self.assertEqual(len(tracks), 6)
        self.assertTrue(all(track.album_image_url for track in tracks))
        self.assertTrue(all(is_verified_instrumental(track) for track in tracks))

    @patch("app.services.spotify_service._get_app_access_token", return_value="app-token")
    @patch("app.services.spotify_service._search_track", return_value=None)
    def test_sleep_ranking_is_not_replaced_by_lower_ranked_cover_candidates(self, _mock_search, _mock_app_token) -> None:
        text = "잠을 못 자서 잘 때 들을 잔잔하고 차분한 가사 없는 곡을 추천해줘."
        tracks = recommend_tracks("tired", context_text=text)
        names = [track.name for track in tracks]

        self.assertEqual(len(tracks), 6)
        self.assertTrue(all(is_verified_instrumental(track) for track in tracks))
        self.assertTrue(
            all(
                {"ambient", "classical", "piano"}.intersection(track.reason_facts.get("tags", []))
                for track in tracks
            )
        )
        self.assertFalse({"So What", "Take Five", "Blue Bossa"}.intersection(names))

    @patch("app.services.spotify_service._get_app_access_token", return_value=None)
    def test_sleep_summary_mentions_instrumentals_only_for_verified_tracks(self, _mock_app_token) -> None:
        text = "어제 고민이 많아 잠을 못 잤어. 잘 때 어울리는 가사가 없는 곡을 추천해줘."
        tracks = recommend_tracks("tired", context_text=text)
        message = build_recommendation_message("tired", text, len(tracks), tracks)

        self.assertIn("연주곡", message)

    @patch("app.services.spotify_service._get_app_access_token", return_value=None)
    def test_sleep_fallback_reasons_do_not_reuse_study_context(self, _mock_app_token) -> None:
        text = "어제 고민이 많아 잠을 못 잤어. 잘 때 어울리는 가사가 없는 곡을 추천해줘."
        tracks = recommend_tracks("tired", context_text=text)
        reasons = [
            build_track_reason(track, "tired", text, index, _recommendation_role("tired", index, text))
            for index, track in enumerate(tracks)
        ]

        self.assertTrue(all("공부" not in reason and "해야 할 일" not in reason for reason in reasons))
        self.assertTrue(all("구성가" not in reason and "리듬와" not in reason for reason in reasons))

    @patch("app.services.spotify_service._get_app_access_token", return_value=None)
    def test_sleep_ranking_demotes_energetic_instrumental_candidates(self, _mock_app_token) -> None:
        text = "잠을 못 자서 잘 때 들을 잔잔하고 차분한 가사 없는 곡을 추천해줘."
        tracks = recommend_tracks("tired", context_text=text)
        names = [track.name for track in tracks]

        self.assertTrue(all(is_verified_instrumental(track) for track in tracks))
        self.assertTrue(
            all(
                {"ambient", "classical", "piano"}.intersection(track.reason_facts.get("tags", []))
                for track in tracks
            )
        )
        self.assertFalse({"Spain", "Birdland", "Cantaloupe Island", "Sing, Sing, Sing", "Donna Lee", "Blue Bossa", "Take Five"}.intersection(names))

        reason = build_track_reason(tracks[0], "tired", text, 0, _recommendation_role("tired", 0, text))
        self.assertNotIn("재즈 계열의 리듬", reason)

        self.assertTrue(all(track.reason_facts.get("sleep_ranking_factors") for track in tracks))

    def test_new_abstract_endings_are_rejected(self) -> None:
        invalid_reasons = [
            "에너지가 채워지는 느낌을 주는 곡이에요.",
            "분위기를 환기하고 싶을 때 적당해요.",
            "가볍게 이어 듣기 알맞아요.",
            "밝은 분위기가 다가와요.",
        ]

        self.assertTrue(all(_uses_repetitive_or_abstract_language(reason) for reason in invalid_reasons))

    def test_additional_abstract_effect_phrases_are_rejected(self) -> None:
        invalid_reasons = [
            "에너지가 분위기를 채워주는 곡이에요.",
            "높은 에너지로 템포를 살려줘요.",
            "경쾌한 에너지가 조화롭게 흘러가요.",
            "해야 할 일을 같은 템포로 이어가고 싶을 때 유용해요.",
        ]

        self.assertTrue(all(_uses_repetitive_or_abstract_language(reason) for reason in invalid_reasons))
        self.assertFalse(_is_safe_recommendation_message("몰입을 도와주는 음악들이에요."))

    def test_anxious_recommendation_roles_are_distinct(self) -> None:
        roles = [_recommendation_role("anxious", index) for index in range(6)]

        self.assertEqual(len({role["focus"] for role in roles}), 6)
        self.assertEqual(len({role["situation_angle"] for role in roles}), 6)

    def test_overstated_psychological_effect_falls_back_to_safe_copy(self) -> None:
        track = TrackSummary(
            track_id="track-1",
            name="Ditto",
            artist_name="NewJeans",
            reason_facts={"tags": ["dreamy", "calm"]},
        )

        tracks, reason_map = _apply_recommendation_copy(
            [track],
            {
                "track_reasons": [
                    {
                        "track_id": "track-1",
                        "reason": "몽환적인 분위기가 마음을 고요하게 이끕니다. 긴장을 느슨하게 풀어줍니다.",
                        "used_fact_keys": ["tags"],
                    }
                ]
            },
            "anxious",
            "취업 준비가 뜻대로 되지 않아 불안해요.",
        )

        self.assertEqual(reason_map, {})
        self.assertIn("몽환적이고 차분하게", tracks[0].reason or "")
        self.assertNotIn("서비스에서", tracks[0].reason or "")

    def test_unnatural_korean_fragment_falls_back_to_readable_copy(self) -> None:
        track = TrackSummary(
            track_id="track-1",
            name="Ditto",
            artist_name="NewJeans",
            reason_facts={"tags": ["dreamy", "calm"]},
        )

        tracks, reason_map = _apply_recommendation_copy(
            [track],
            {
                "track_reasons": [
                    {
                        "track_id": "track-1",
                        "reason": "몽환적이고 차분한 분위기가 이어집니다. 잠시 숨 고르기 어울려요.",
                        "used_fact_keys": ["tags"],
                    }
                ]
            },
            "anxious",
            "취업 준비가 뜻대로 되지 않아 불안해요.",
        )

        self.assertEqual(reason_map, {})
        self.assertIn("몽환적이고 차분하게", tracks[0].reason or "")
        self.assertNotIn("숨 고르기 어울", tracks[0].reason or "")

    def test_fallback_reasons_use_distinct_roles_for_each_track(self) -> None:
        tracks = [
            TrackSummary(
                track_id=f"track-{index}",
                name=f"Track {index}",
                artist_name="Artist",
                reason_facts={"tags": ["dreamy", "calm"]},
            )
            for index in range(6)
        ]

        enriched_tracks, reason_map = _apply_recommendation_copy(tracks, None, "anxious", "취업 준비가 뜻대로 되지 않아 불안해요.")
        reasons = [track.reason or "" for track in enriched_tracks]

        self.assertEqual(reason_map, {})
        self.assertEqual(len(set(reasons)), 6)
        self.assertTrue(all(not reason.startswith("Track ") for reason in reasons))

    def test_disallowed_role_infinitive_patterns_are_rejected(self) -> None:
        invalid_reasons = [
            "생각을 정리하기 잘 맞아요.",
            "긴장을 풀기 어울려요.",
            "숨 고르기 필요할 때 들어보세요.",
            "위로의 시간 만들기 적합해요.",
            "차분하게 몰입하기 좋아요.",
        ]

        self.assertTrue(all(_uses_disallowed_infinitive_pattern(reason) for reason in invalid_reasons))
        self.assertFalse(_uses_disallowed_infinitive_pattern("잠시 숨을 고르고 싶을 때 듣기 좋아요."))

    def test_unnatural_role_paraphrases_and_data_description_are_rejected(self) -> None:
        invalid_reasons = [
            "잔잔하게 감상하기 적절해요.",
            "천천히 귀 기울이기 알맞아요.",
            "조용히 곱씹어 보기 괜찮아요.",
            "몽환적이고 차분하게 가라앉는 분위기로 이루어져 있어요.",
            "미래에 대한 걱정을 곱씹으며 듣기 좋아요.",
            "여러 사람이 비교적 익숙하게 즐길 수 있는 대중성이 돋보여요.",
            "밝고 활기찬 분위기가 골고루 담겨 있어요.",
            "여름과 잘 어울리는 밝은 분위기 곡이에요.",
        ]

        self.assertTrue(all(_uses_unnatural_recommendation_language(reason) for reason in invalid_reasons))
        self.assertFalse(_uses_unnatural_recommendation_language("잠시 생각에서 거리를 두고 쉬어가고 싶을 때 잘 어울려요."))

    def test_recommendation_reasons_keep_haeyo체(self) -> None:
        self.assertTrue(_uses_formal_recommendation_style("차분한 분위기의 곡입니다. 새벽에 잘 맞아요."))
        self.assertFalse(_uses_formal_recommendation_style("차분한 분위기의 곡이에요. 새벽에 잘 맞아요."))

    def test_abstract_dawn_language_and_duplicate_summary_actions_are_rejected(self) -> None:
        self.assertTrue(_uses_repetitive_or_abstract_language("몽환적인 분위기가 감성적으로 다가오는 곡이에요."))
        self.assertTrue(_uses_repetitive_or_abstract_language("부드러운 분위기가 포근하게 이어지는 곡이에요."))
        self.assertTrue(_uses_repetitive_or_abstract_language("차분한 분위기가 깊이감을 더해주는 곡이에요."))
        self.assertTrue(_uses_repetitive_or_abstract_language("부드러운 분위기가 포근하게 펼쳐지는 곡이에요."))
        self.assertFalse(_is_safe_recommendation_message("혼자 조용히 사색에 잠겨 머물기 좋은 곡들이에요."))

    def test_summary_direct_invitation_is_rejected(self) -> None:
        self.assertFalse(_is_safe_recommendation_message("혼자 사색에 잠기기 좋은 음악들과 함께 차분하게 머물러 보세요."))
        self.assertFalse(_is_safe_recommendation_message("화나는 일이 있어 답답한 감정을 털어낼 수 있도록 강렬한 곡들을 골랐어요. 스트레스를 날려보낼 수 있는 곡들이에요."))

    def test_dawn_summary_keeps_explicit_selected_moods(self) -> None:
        selected_vibes = ["몽환적인", "감성적인"]
        missing_mood = "새벽의 센치한 분위기에 어울리는 몽환적인 곡들을 골라봤어요. 혼자 생각이 길어지는 시간에 듣기 좋은 음악들이에요."
        complete_summary = "새벽의 센치한 분위기에 어울리는 몽환적이고 감성적인 곡들을 골라봤어요. 혼자 생각이 길어지는 시간에 듣기 좋은 음악들이에요."

        self.assertFalse(_is_safe_recommendation_message(missing_mood, "새벽에 센치해질 때", selected_vibes))
        self.assertTrue(_is_safe_recommendation_message(complete_summary, "새벽에 센치해질 때", selected_vibes))

    def test_personal_companion_style_summary_is_rejected(self) -> None:
        self.assertFalse(_is_safe_recommendation_message("마음이 조급할 때 곁을 지켜줄게요."))
        self.assertFalse(_is_safe_recommendation_message("마음을 차분히 가라앉혀 보세요."))
        self.assertTrue(_is_safe_recommendation_message("조급해진 마음을 잠시 내려놓을 수 있도록 편안한 곡들을 골라봤어요."))

    def test_repeated_roots_and_abstract_ai_phrases_are_rejected(self) -> None:
        invalid_reasons = [
            "부드럽고 따뜻하게 이어지는 분위기가 부드러운 감성을 전해줘요.",
            "편안하면서 차분한 분위기가 차분하게 머물러요.",
            "편안한 결을 만들어줘요.",
            "포근한 느낌을 채워줘요.",
        ]

        self.assertTrue(all(_uses_repetitive_or_abstract_language(reason) for reason in invalid_reasons))
        self.assertFalse(_uses_repetitive_or_abstract_language("부드럽고 따뜻한 분위기가 편안하게 이어지는 곡이에요."))

    def test_repeated_terms_across_two_sentences_are_rejected(self) -> None:
        self.assertTrue(
            _uses_repetitive_or_abstract_language(
                "편안하게 머물며 듣기 좋은 곡이에요. 여러 생각이 떠오를 때 차분히 정리하며 듣기 좋습니다."
            )
        )
        self.assertTrue(_uses_repetitive_or_abstract_language("차분한 분위기가 차분하게 이어져요."))
        self.assertTrue(_uses_repetitive_or_abstract_language("부드럽고 따뜻하게 진행되는 전개가 펼쳐져요."))
        self.assertFalse(
            _uses_repetitive_or_abstract_language(
                "부드럽고 따뜻한 분위기가 부담 없이 이어지는 곡이에요. 여러 생각이 떠오를 때 잠시 숨을 고르고 싶다면 잘 어울려요."
            )
        )

    def test_summary_rejects_overlapping_anxiety_words(self) -> None:
        self.assertFalse(_is_safe_recommendation_message("초조한 마음과 조급함을 잠시 내려놓을 수 있도록 곡들을 골라봤어요."))

    def test_repeated_time_clause_is_rejected(self) -> None:
        self.assertTrue(_repeats_time_clause("결과를 곱씹고 있을 때 생각의 속도를 늦추고 싶을 때 어울려요."))
        self.assertFalse(_repeats_time_clause("결과에 대한 생각이 계속 머릿속을 맴돌 때, 잠시 생각의 속도를 늦추며 듣기 좋아요."))

    def test_purpose_phrase_and_unexplained_action_are_rejected(self) -> None:
        invalid_reasons = [
            "긴장을 느슨하게 풀기 위해 듣기 좋아요.",
            "여러 생각이 떠오를 때 차분히 정리하며 듣기 좋습니다.",
            "마음을 가라앉히며 듣기 좋아요.",
            "조용히 위로를 받을 수 있어요.",
        ]

        self.assertTrue(all(_uses_repetitive_or_abstract_language(reason) for reason in invalid_reasons))
        self.assertFalse(
            _uses_repetitive_or_abstract_language(
                "여러 생각이 한꺼번에 떠오를 때 복잡한 마음을 천천히 정리하며 듣기 좋습니다."
            )
        )

    def test_unsupported_music_details_and_study_effect_claims_are_rejected(self) -> None:
        track = TrackSummary(track_id="track-1", name="Song", artist_name="Artist", reason_facts={"tags": ["upbeat"]})

        self.assertTrue(_mentions_unsupported_music_detail("선명한 신스 베이스와 드럼이 이어져요.", track))
        self.assertTrue(_uses_repetitive_or_abstract_language("집중력을 흐트러뜨리지 않고 듣기 좋아요."))
        self.assertTrue(_uses_repetitive_or_abstract_language("경쾌한 에너지와 높은 에너지가 경쾌하게 이어져요."))

    def test_duplicate_gemini_openings_fall_back_for_later_tracks(self) -> None:
        tracks = [
            TrackSummary(track_id="track-1", name="A", artist_name="Artist", reason_facts={"tags": ["dreamy", "calm"]}),
            TrackSummary(track_id="track-2", name="B", artist_name="Artist", reason_facts={"tags": ["soft", "warm"]}),
        ]
        shared_opening = "몽환적이고 차분한 분위기가 자연스럽게 이어져요"
        recommendation_copy = {
            "track_reasons": [
                {"track_id": "track-1", "reason": f"{shared_opening}. 결과에 대한 생각이 계속 맴돌 때 잠시 쉬어가며 듣기 좋아요.", "used_fact_keys": ["tags"]},
                {"track_id": "track-2", "reason": f"{shared_opening}. 스스로를 너무 몰아붙이고 있을 때 부담 없이 들을 수 있어요.", "used_fact_keys": ["tags"]},
            ]
        }

        enriched_tracks, reason_map = _apply_recommendation_copy(tracks, recommendation_copy, "anxious", "취업 준비가 뜻대로 되지 않아 불안해요.")

        self.assertEqual(set(reason_map), {"track-1"})
        self.assertNotEqual(enriched_tracks[0].reason, enriched_tracks[1].reason)

    @patch("app.services.gemini_service.is_gemini_configured", return_value=True)
    @patch("app.services.gemini_service._gemini_post")
    def test_recommendation_copy_requests_a_strict_json_schema(self, post, _configured) -> None:
        post.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "message": "마음을 잠시 가라앉힐 수 있는 곡들로 골랐어요.",
                                "track_reasons": [
                                    {
                                        "track_id": "track-1",
                                        "reason": "부드러운 사운드로 분류된 곡이에요. 불안한 마음을 천천히 정리하는 데 어울려요.",
                                        "used_fact_keys": ["sound_profile"],
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }

        result = generate_recommendation_copy(
            "anxious",
            "취업 준비가 마음처럼 풀리지 않아 불안해요.",
            [{"track_id": "track-1", "name": "Ditto", "artist_name": "NewJeans"}],
        )

        self.assertIsNotNone(result)
        payload = post.call_args.args[1]
        self.assertEqual(payload["model"], settings.gemini_copy_model)
        response_format = payload["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(
            response_format["json_schema"]["schema"]["required"],
            ["message", "track_reasons"],
        )

    @patch("app.services.gemini_service.is_gemini_configured", return_value=True)
    @patch("app.services.gemini_service._gemini_post")
    def test_family_trip_payload_uses_diverse_primary_features(self, post, _configured) -> None:
        post.return_value = {"choices": [{"message": {"content": json.dumps({"message": "추천 곡을 골라봤어요.", "track_reasons": []})}}]}
        tracks = [
            {"track_id": "1", "name": "A", "artist_name": "A", "reason_facts": {"tags": ["upbeat", "high_energy", "family_trip", "summer"]}},
            {"track_id": "2", "name": "B", "artist_name": "B", "reason_facts": {"tags": ["upbeat", "mainstream", "broad_familiarity_ko", "family_trip"]}},
            {"track_id": "3", "name": "C", "artist_name": "C", "reason_facts": {"tags": ["upbeat", "mainstream", "broad_familiarity_ko", "family_trip"]}},
            {"track_id": "4", "name": "D", "artist_name": "D", "reason_facts": {"tags": ["upbeat", "high_energy", "family_trip"]}},
            {"track_id": "5", "name": "E", "artist_name": "E", "reason_facts": {"tags": ["upbeat", "summer", "family_trip"]}},
            {"track_id": "6", "name": "F", "artist_name": "F", "reason_facts": {"tags": ["upbeat", "mainstream", "family_trip"]}},
        ]

        generate_recommendation_copy("excited", "내일 가족 여행을 가요. 차에서 들을 신나는 노래 추천해줘.", tracks)

        payload = post.call_args.args[1]
        request_tracks = json.loads(payload["messages"][1]["content"])["tracks"]
        primary_features = [track["reason_ingredient"]["primary_feature"] for track in request_tracks]

        self.assertEqual(sum(feature == "밝고 신나는 분위기" for feature in primary_features), 2)
        self.assertIn("여러 사람이 비교적 익숙하게 들을 수 있는 대중적인 곡", primary_features)
        self.assertIn("여름과 잘 어울리는 밝은 분위기", primary_features)

    def test_dawn_sentimental_context_uses_its_own_roles(self) -> None:
        request = "새벽에 센치해질 때 듣기좋은 infp 감성 플레이리스트 추천해줘."

        context = _build_listening_request_context(request, ["몽환적인", "감성적인"])
        role = _recommendation_role("sad", 0, request, ["몽환적인", "감성적인"], {"tags": ["dreamy"]})

        self.assertEqual(context["context"], "새벽 감성 플레이리스트")
        self.assertNotIn("공부 또는 업무 맥락", context["goal"])
        self.assertIn("새벽", role["focus"])
        self.assertNotIn("집중", role["situation_angle"])

    def test_dawn_sentimental_payload_uses_verified_dreamy_ingredients(self) -> None:
        request = "새벽에 센치해질 때 듣기좋은 infp 감성 플레이리스트 추천해줘."
        tracks = [
            {"track_id": "1", "name": "D (Half Moon)", "artist_name": "DEAN", "reason_facts": {"tags": ["korean", "rnb", "soul", "dreamy"], "moods": ["sad", "lonely"]}},
            {"track_id": "2", "name": "To Build a Home", "artist_name": "The Cinematic Orchestra", "reason_facts": {"tags": ["soft", "dreamy"], "moods": ["sad"]}},
        ]

        with patch("app.services.gemini_service.is_gemini_configured", return_value=True), patch(
            "app.services.gemini_service._gemini_post",
            return_value={"choices": [{"message": {"content": json.dumps({"message": "추천 곡을 골라봤어요.", "track_reasons": []})}}]},
        ) as post:
            generate_recommendation_copy("sad", request, tracks, ["몽환적인", "감성적인"])

        request_tracks = json.loads(post.call_args.args[1]["messages"][1]["content"])["tracks"]
        ingredients = [track["reason_ingredient"] for track in request_tracks]
        self.assertEqual(ingredients[0]["feature_source"], "rnb_soul")
        self.assertEqual(ingredients[1]["feature_source"], "soft")
        self.assertEqual(ingredients[0]["feature_provenance"], "track_metadata")
        self.assertTrue(all("공부" not in ingredient["recommendation_role"] for ingredient in ingredients))
        self.assertEqual(request_tracks[0]["track_actual_features"]["tags"], ["korean", "R&B", "소울", "몽환적인 분위기"])
        payload = json.loads(post.call_args.args[1]["messages"][1]["content"])
        self.assertEqual(payload["user_desired_moods"], ["dreamy", "emotional"])
        self.assertEqual(payload["user_preferences_for_context"]["desired_moods"], ["dreamy", "emotional"])

    def test_dawn_sentimental_ranking_demotes_fast_candidates(self) -> None:
        request = "새벽에 센치해질 때 듣기좋은 infp 감성 플레이리스트 추천해줘."

        tracks = _select_fallback_catalog("sad", request, 6)
        names = [str(track["name"]) for track in tracks]

        self.assertIn("D (Half Moon)", names)
        self.assertNotIn("Fix You", names)
        self.assertNotIn("Lemon", names)
        self.assertNotIn("Into The Night", names)

    def test_mbti_aesthetic_supports_all_presets_and_korean_aliases(self) -> None:
        self.assertEqual(len(MBTI_AESTHETIC_PRESETS), 16)
        self.assertEqual(detect_mbti_aesthetic("ENTP스러운 플리")["mbti"], "ENTP")
        self.assertEqual(detect_mbti_aesthetic("인프피 감성")["mbti"], "INFP")
        self.assertIn("dreamy", detect_mbti_aesthetic("INFP 감성")["ranking_tags"])

    def test_mbti_aesthetic_does_not_turn_a_trip_request_into_dawn_context(self) -> None:
        context = _build_listening_request_context(
            "INFP 감성인데 가족과 여름 여행을 가요. 차에서 신나는 노래 추천해줘.",
            ["신나는", "기분 전환되는"],
        )

        self.assertEqual(context["context"], "가족 여행의 차 안")
        self.assertEqual(context["mbti_aesthetic"]["mbti"], "INFP")
        self.assertEqual(context["priority"][0], "가족 여행과 차 안 맥락")
