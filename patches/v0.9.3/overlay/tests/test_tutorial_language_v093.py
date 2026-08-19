from __future__ import annotations

import unittest

from app.services.youtube_service import detect_video_language


class TutorialLanguageV093Tests(unittest.TestCase):
    def test_metadata_spanish_wins(self):
        self.assertEqual(
            detect_video_language("Miniature painting tutorial", "", default_audio_language="es-ES"),
            "es",
        )

    def test_metadata_english_wins(self):
        self.assertEqual(
            detect_video_language("Cómo pintar una miniatura", "", default_language="en-US"),
            "en",
        )

    def test_spanish_text_fallback(self):
        self.assertEqual(
            detect_video_language("Cómo pintar una miniatura fácil", "Tutorial paso a paso para pintar miniaturas"),
            "es",
        )

    def test_english_text_fallback(self):
        self.assertEqual(
            detect_video_language("How to paint miniatures", "Easy step by step miniature painting tutorial"),
            "en",
        )

    def test_unknown_text_remains_unknown(self):
        self.assertEqual(detect_video_language("Darth Vader LED conversion", "Star Wars Legion"), "")


if __name__ == "__main__":
    unittest.main()
