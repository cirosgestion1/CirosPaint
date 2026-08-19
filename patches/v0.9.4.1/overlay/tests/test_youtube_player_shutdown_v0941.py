from __future__ import annotations

import unittest

from PySide6.QtWebEngineCore import QWebEnginePage

from app.ui.dialogs.youtube_player_dialog import dispose_web_engine_view


class _FakePage:
    def __init__(self):
        self.muted = False
        self.visible = True
        self.lifecycle_state = None

    def setAudioMuted(self, value: bool):
        self.muted = value

    def setVisible(self, value: bool):
        self.visible = value

    def setLifecycleState(self, state):
        self.lifecycle_state = state


class _FakeWebView:
    def __init__(self):
        self.page_object = _FakePage()
        self.hidden = False
        self.closed = False
        self.delete_scheduled = False

    def hide(self):
        self.hidden = True

    def page(self):
        return self.page_object

    def close(self):
        self.closed = True

    def deleteLater(self):
        self.delete_scheduled = True


class YouTubePlayerShutdownV0941Tests(unittest.TestCase):
    def test_dispose_mutes_discards_and_deletes_web_view(self):
        web = _FakeWebView()

        dispose_web_engine_view(web)

        self.assertTrue(web.hidden)
        self.assertTrue(web.page_object.muted)
        self.assertFalse(web.page_object.visible)
        self.assertEqual(web.page_object.lifecycle_state, QWebEnginePage.LifecycleState.Discarded)
        self.assertTrue(web.closed)
        self.assertTrue(web.delete_scheduled)

    def test_dispose_accepts_missing_view(self):
        dispose_web_engine_view(None)


if __name__ == "__main__":
    unittest.main()
