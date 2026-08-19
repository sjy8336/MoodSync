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
from app.services.spotify_service import (
    build_recommendation_message,
    build_track_reason,
    extract_hard_constraints,
    is_verified_instrumental,
    recommend_tracks,
)


class GeminiRecommendationCopyTests(unittest.TestCase):
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

        self.assertIn("잠들기 전 긴장 내려놓기", focuses)
        self.assertNotIn("공부 템포 유지", focuses)
        self.assertNotIn("해야 할 일", " ".join(role["situation_angle"] for role in roles))

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
        text = "잠을 못 자서 잘 때 들을 가사 없는 곡을 추천해줘."

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
        self.assertTrue({"An Ending (Ascent)", "Clair de Lune", "Gymnopédie No. 1"}.issubset(names))
        self.assertFalse({"Spain", "Birdland", "Cantaloupe Island", "Sing, Sing, Sing", "Donna Lee"}.intersection(names))

        reason = build_track_reason(tracks[0], "tired", text, 0, _recommendation_role("tired", 0, text))
        self.assertNotIn("재즈 계열의 리듬", reason)

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
        ]

        self.assertTrue(all(_uses_unnatural_recommendation_language(reason) for reason in invalid_reasons))
        self.assertFalse(_uses_unnatural_recommendation_language("잠시 생각에서 거리를 두고 쉬어가고 싶을 때 잘 어울려요."))

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
