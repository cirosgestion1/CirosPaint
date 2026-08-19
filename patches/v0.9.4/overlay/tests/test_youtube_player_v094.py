from __future__ import annotations

import unittest
from urllib.request import urlopen

from app.ui.dialogs.youtube_player_dialog import (
    LoopbackPlayerServer,
    build_loopback_embed_url,
    build_youtube_player_html,
)


class YouTubePlayerV094Tests(unittest.TestCase):
    def test_actual_embed_url_has_no_fabricated_remote_origin(self):
        url = build_loopback_embed_url("dQw4w9WgXcQ")
        self.assertIn("https://www.youtube.com/embed/dQw4w9WgXcQ", url)
        self.assertNotIn("origin=", url)
        self.assertNotIn("widget_referrer=", url)

    def test_loopback_html_uses_referrer_policy(self):
        html = build_youtube_player_html("dQw4w9WgXcQ")
        self.assertIn("<iframe", html)
        self.assertIn("strict-origin-when-cross-origin", html)
        self.assertNotIn("github.com/cirosgestion1/CirosPaint", html)

    def test_loopback_server_serves_real_http_page(self):
        server = LoopbackPlayerServer("dQw4w9WgXcQ")
        server.start()
        try:
            url = server.url.toString()
            self.assertTrue(url.startswith("http://localhost:"))
            with urlopen(url, timeout=3) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
                self.assertIn("youtube.com/embed/dQw4w9WgXcQ", body)
        finally:
            server.stop()

    def test_invalid_video_id_is_rejected(self):
        with self.assertRaises(ValueError):
            build_loopback_embed_url("bad/id")


if __name__ == "__main__":
    unittest.main()
