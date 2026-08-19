from __future__ import annotations

from urllib.parse import quote

from PySide6.QtCore import QByteArray, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEngineHttpRequest
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


# YouTube requires desktop/WebView clients to identify embedded-player requests
# with an HTTP Referer (or equivalent client identity). A stable app-local
# origin is used only as an identifier; it is never contacted by the player.
PLAYER_ORIGIN = "https://cirospaint.local"
PLAYER_REFERRER = f"{PLAYER_ORIGIN}/"


def build_youtube_embed_url(video_id: str) -> QUrl:
    safe_video_id = quote((video_id or "").strip(), safe="-_")
    origin = quote(PLAYER_ORIGIN, safe="")
    referrer = quote(PLAYER_REFERRER, safe="")
    return QUrl(
        f"https://www.youtube.com/embed/{safe_video_id}"
        f"?playsinline=1&rel=0&origin={origin}&widget_referrer={referrer}"
    )


def build_youtube_player_request(video_id: str) -> QWebEngineHttpRequest:
    request = QWebEngineHttpRequest(build_youtube_embed_url(video_id))
    request.setHeader(QByteArray(b"Referer"), QByteArray(PLAYER_REFERRER.encode("utf-8")))
    return request


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
        self.web.load(build_youtube_player_request(video_id))

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
