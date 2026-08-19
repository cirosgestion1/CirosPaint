from __future__ import annotations

import unittest

from app.services.tutorial_query_service import TutorialQueryService
from app.services.youtube_service import TutorialVideo, build_language_search_plan, detect_video_language


class TutorialLanguageV094Tests(unittest.TestCase):
    def test_english_filter_translates_hobby_query_instead_of_sending_spanish_query(self):
        query = TutorialQueryService.localized_search_query("pintar Darth Vader", "en")
        self.assertIn("paint", query)
        self.assertIn("darth", query)
        self.assertIn("vader", query)
        self.assertIn("miniature", query)
        self.assertNotIn("pintar", query)

    def test_spanish_filter_translates_common_english_hobby_terms(self):
        query = TutorialQueryService.localized_search_query("paint Darth Vader", "es")
        self.assertIn("pintar", query)
        self.assertIn("darth", query)
        self.assertIn("vader", query)
        self.assertIn("miniaturas", query)

    def test_all_filter_runs_two_discovery_queries(self):
        plan = build_language_search_plan("pintar Darth Vader", "")
        self.assertEqual([language for _query, language in plan], ["es", "en"])
        self.assertIn("pintar", plan[0][0])
        self.assertIn("paint", plan[1][0])

    def test_specific_english_title_can_match_spanish_user_query(self):
        english_score = TutorialQueryService.relevance_score(
            "pintar Darth Vader",
            "How to paint Darth Vader - Star Wars Legion miniature painting",
            "Step by step guide",
            0,
        )
        generic_score = TutorialQueryService.relevance_score(
            "pintar Darth Vader",
            "Star Wars news and collectibles",
            "Darth Vader discussion",
            0,
        )
        self.assertGreater(english_score, generic_score)

    def test_video_language_properties_are_ready_for_badge(self):
        video = TutorialVideo(
            video_id="dQw4w9WgXcQ",
            title="How to paint miniatures",
            channel_title="Test",
            description="",
            thumbnail_url="",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            duration_text="1:00",
            published_at="2026-01-01T00:00:00Z",
            view_count=1,
            like_count=1,
            language_code="en",
        )
        self.assertEqual(video.language_tag, "EN")
        self.assertEqual(video.language_name, "Inglés")

    def test_youtube_audio_metadata_still_has_priority(self):
        self.assertEqual(
            detect_video_language(
                "Cómo pintar una miniatura",
                "Tutorial en español",
                default_audio_language="en-US",
                default_language="es-ES",
            ),
            "en",
        )


if __name__ == "__main__":
    unittest.main()
