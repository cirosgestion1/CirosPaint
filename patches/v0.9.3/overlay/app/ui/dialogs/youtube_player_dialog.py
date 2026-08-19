from __future__ import annotations

from urllib.parse import quote

from PySide6.QtCore import QByteArray, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEngineHttpRequest, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


# Use a real, public HTTPS identity for the desktop client. The previous
# pseudo-domain (cirospaint.local) still produced YouTube error 153 on Windows.
PLAYER_ORIGIN = "https://github.com"
PLAYER_REFERRER = "https://github.com/cirosgestion1/CirosPaint/"


def build_youtube_embed_url(video_id: str) -> QUrl:
    safe_video_id = quote((video_id or "").strip(), safe="-_")
    origin = quote(PLAYER_ORIGIN, safe="")
    referrer = quote(PLAYER_REFERRER, safe="")
    return QUrl(
        f"https://www.youtube.com/embed/{safe_video_id}"
        f"?playsinline=1&rel=0&origin={origin}&widget_referrer={referrer}"
    )


def build_youtube_player_request(video_id: str) -> QWebEngineHttpRequest:
    """Compatibility helper retained from 0.9.2.

    The 0.9.3 player no longer navigates with this request directly; the actual
    iframe request is handled by YouTubeRequestInterceptor below. Keeping this
    helper avoids breaking earlier tests and callers while preserving the new
    playback strategy.
    """
    request = QWebEngineHttpRequest(build_youtube_embed_url(video_id))
    request.setHeader(QByteArray(b"Referer"), QByteArray(PLAYER_REFERRER.encode("utf-8")))
    return request


def build_youtube_player_html(video_id: str) -> str:
    src = build_youtube_embed_url(video_id).toString()
    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <meta name=\"referrer\" content=\"strict-origin-when-cross-origin\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; background: #111; overflow: hidden; }}
    iframe {{ border: 0; width: 100%; height: 100%; display: block; }}
  </style>
</head>
<body>
  <iframe
    src=\"{src}\"
    title=\"YouTube video player\"
    referrerpolicy=\"strict-origin-when-cross-origin\"
    allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\"
    allowfullscreen>
  </iframe>
</body>
</html>"""


class YouTubeRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Identify the actual YouTube iframe request before Chromium sends it.

    QWebEngineHttpRequest only affected the top-level navigation in 0.9.2.
    In 0.9.3 the player lives in an HTML wrapper and the interceptor injects
    Referer specifically into the /embed/ iframe request that YouTube checks.
    """

    def interceptRequest(self, info) -> None:
        url = info.requestUrl()
        host = url.host().lower()
        if host in {"youtube.com", "www.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"} and url.path().startswith("/embed/"):
            info.setHttpHeader(QByteArray(b"Referer"), QByteArray(PLAYER_REFERRER.encode("utf-8")))


class YouTubePlayerDialog(QDialog):
    def __init__(self, video_id: str, title: str, video_url: str, parent=None):
        super().__init__(parent)
        self.video_id = video_id
        self.video_url = video_url
        self.setWindowTitle(title or "YouTube")
        self.resize(980, 680)
        self.setMinimumSize(760, 520)

        heading = QLabel(title or "YouTube")
        heading.setObjectName("TutorialTitle")
        heading.setWordWrap(True)

        self.web = QWebEngineView(self)
        self.web.setMinimumHeight(420)
        self._request_interceptor = YouTubeRequestInterceptor(self.web)
        self.web.page().setUrlRequestInterceptor(self._request_interceptor)
        self.web.setHtml(build_youtube_player_html(video_id), QUrl(PLAYER_REFERRER))

        open_youtube = QPushButton("Abrir en YouTube")
        open_youtube.setObjectName("SecondaryButton")
        open_youtube.clicked.connect(self._open_youtube)

        close_button = QPushButton("Cerrar")
        close_button.setObjectName("PrimaryButton")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(open_youtube)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addWidget(self.web, 1)
        layout.addLayout(buttons)

    def _open_youtube(self) -> None:
        QDesktopServices.openUrl(QUrl(self.video_url))
