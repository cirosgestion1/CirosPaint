from __future__ import annotations

import unittest

from PySide6.QtCore import QByteArray

from app.ui.dialogs.youtube_player_dialog import (
    PLAYER_ORIGIN,
    PLAYER_REFERRER,
    build_youtube_player_request,
)


class YouTubePlayerRequestTests(unittest.TestCase):
    def test_embed_request_identifies_desktop_client(self):
        request = build_youtube_player_request("dQw4w9WgXcQ")
        self.assertTrue(request.hasHeader(QByteArray(b"Referer")))
        self.assertEqual(
            bytes(request.header(QByteArray(b"Referer"))).decode("utf-8"),
            PLAYER_REFERRER,
        )
        url = request.url().toString()
        self.assertIn("https://www.youtube.com/embed/dQw4w9WgXcQ", url)
        self.assertIn("origin=", url)
        self.assertIn("widget_referrer=", url)
        self.assertTrue(PLAYER_ORIGIN.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
