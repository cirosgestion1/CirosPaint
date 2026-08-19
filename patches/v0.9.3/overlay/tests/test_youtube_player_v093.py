from __future__ import annotations

import unittest

from PySide6.QtCore import QByteArray, QUrl

from app.ui.dialogs.youtube_player_dialog import (
    PLAYER_ORIGIN,
    PLAYER_REFERRER,
    YouTubeRequestInterceptor,
    build_youtube_embed_url,
    build_youtube_player_html,
)


class _DummyRequestInfo:
    def __init__(self, url: str):
        self._url = QUrl(url)
        self.headers: dict[bytes, bytes] = {}

    def requestUrl(self):
        return self._url

    def setHttpHeader(self, name, value):
        self.headers[bytes(name)] = bytes(value)


class YouTubePlayerV093Tests(unittest.TestCase):
    def test_embed_uses_public_identity(self):
        url = build_youtube_embed_url("dQw4w9WgXcQ").toString()
        self.assertTrue(PLAYER_ORIGIN.startswith("https://"))
        self.assertTrue(PLAYER_REFERRER.startswith("https://"))
        self.assertIn("origin=", url)
        self.assertIn("widget_referrer=", url)

    def test_html_wrapper_has_referrer_policy_and_iframe(self):
        html = build_youtube_player_html("dQw4w9WgXcQ")
        self.assertIn("<iframe", html)
        self.assertIn("strict-origin-when-cross-origin", html)
        self.assertIn("youtube.com/embed/dQw4w9WgXcQ", html)

    def test_interceptor_sets_referer_on_embed_request(self):
        info = _DummyRequestInfo("https://www.youtube.com/embed/dQw4w9WgXcQ?playsinline=1")
        YouTubeRequestInterceptor().interceptRequest(info)
        self.assertEqual(info.headers[b"Referer"].decode("utf-8"), PLAYER_REFERRER)

    def test_interceptor_does_not_modify_unrelated_request(self):
        info = _DummyRequestInfo("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        YouTubeRequestInterceptor().interceptRequest(info)
        self.assertNotIn(b"Referer", info.headers)


if __name__ == "__main__":
    unittest.main()
