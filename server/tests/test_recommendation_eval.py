from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.rag.base import KnowledgeChunk, RetrievedKnowledge
from app.rag.knowledge_base import build_recommendation_guidance
from app.services.spotify_service import build_recommendation_message, recommend_tracks


CASES_PATH = Path(__file__).parent / "data" / "recommendation_eval_cases.json"


def _load_cases() -> list[dict[str, object]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _retrieved_context(case: dict[str, object]) -> RetrievedKnowledge:
    chunk_ids = case["retrieved_chunk_ids"]
    assert isinstance(chunk_ids, list)
    return RetrievedKnowledge(
        query=str(case["text"]),
        chunks=tuple(
            KnowledgeChunk(id=str(chunk_id), title=str(chunk_id), content="", keywords=())
            for chunk_id in chunk_ids
        ),
    )


class RecommendationEvaluationTests(unittest.TestCase):
    def test_fallback_recommendations_follow_quality_contracts(self) -> None:
        for case in _load_cases():
            with self.subTest(case=case["id"]):
                mood = str(case["mood"])
                text = str(case["text"])
                vibes = [str(vibe) for vibe in case["selected_vibes"]]
                guidance = build_recommendation_guidance(
                    _retrieved_context(case),
                    mood=mood,
                    selected_vibes=vibes,
                    user_text=text,
                )
                tracks = recommend_tracks(
                    mood,
                    context_text=text,
                    selection_guidance=guidance,
                )
                self.assertEqual(len(tracks), 6)

                all_tags = {
                    str(tag)
                    for track in tracks
                    for tag in (track.reason_facts or {}).get("tags", [])
                }
                expect = case["expect"]
                assert isinstance(expect, dict)
                required_tags = {str(tag) for tag in expect.get("must_include_any_tags", [])}
                forbidden_tags = {str(tag) for tag in expect.get("must_exclude_tags", [])}

                if required_tags:
                    self.assertTrue(
                        all_tags & required_tags,
                        f"{case['id']} expected one of {sorted(required_tags)}, got {sorted(all_tags)}",
                    )
                self.assertFalse(
                    all_tags & forbidden_tags,
                    f"{case['id']} included forbidden tags {sorted(all_tags & forbidden_tags)}",
                )

                message = build_recommendation_message(mood, text, len(tracks), tracks)
                for phrase in expect.get("message_must_include", []):
                    self.assertIn(str(phrase), message, f"{case['id']} summary lost its key context")
