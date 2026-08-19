from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
from threading import Thread
from urllib.parse import quote

from PySide6.QtCore import QByteArray, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEngineHttpRequest, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


# Compatibility identity retained for callers/tests from 0.9.2/0.9.3. The
# actual 0.9.4 player does NOT pretend to be hosted at this URL: it is served
# from a genuine loopback HTTP page so Chromium creates a normal Referer.
PLAYER_ORIGIN = "https://cirospaint"
PLAYER_REFERRER = f"{PLAYER_ORIGIN}/"
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")


def _clean_video_id(video_id: str) -> str:
    value = (video_id or "").strip()
    if not _VIDEO_ID_RE.fullmatch(value):
        raise ValueError("YouTube video id no válido")
    return value


def build_youtube_embed_url(video_id: str) -> QUrl:
    """Compatibility URL used by the legacy request helper."""
    safe_video_id = quote(_clean_video_id(video_id), safe="-_")
    origin = quote(PLAYER_ORIGIN, safe="")
    referrer = quote(PLAYER_REFERRER, safe="")
    return QUrl(
        f"https://www.youtube.com/embed/{safe_video_id}"
        f"?playsinline=1&rel=0&origin={origin}&widget_referrer={referrer}"
    )


def build_youtube_player_request(video_id: str) -> QWebEngineHttpRequest:
    """Compatibility helper retained from 0.9.2.

    0.9.4 no longer navigates the real player with this request. It remains so
    older callers/tests do not break while the dialog uses LoopbackPlayerServer.
    """
    request = QWebEngineHttpRequest(build_youtube_embed_url(video_id))
    request.setHeader(QByteArray(b"Referer"), QByteArray(PLAYER_REFERRER.encode("utf-8")))
    return request


def build_loopback_embed_url(video_id: str) -> str:
    safe_video_id = quote(_clean_video_id(video_id), safe="-_")
    # No fake origin/widget_referrer: this iframe is genuinely embedded inside
    # the loopback page and Chromium supplies its HTTP Referer naturally.
    return f"https://www.youtube.com/embed/{safe_video_id}?playsinline=1&rel=0"


def build_youtube_player_html(video_id: str) -> str:
    src = build_loopback_embed_url(video_id)
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
    """Legacy compatibility interceptor from 0.9.3.

    It is intentionally NOT installed by the 0.9.4 dialog. The previous forced
    cross-origin identity caused Chromium to block the generated page on the
    user's Windows machine.
    """

    def interceptRequest(self, info) -> None:
        url = info.requestUrl()
        host = url.host().lower()
        if host in {"youtube.com", "www.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"} and url.path().startswith("/embed/"):
            info.setHttpHeader(QByteArray(b"Referer"), QByteArray(PLAYER_REFERRER.encode("utf-8")))


class _LoopbackHandler(BaseHTTPRequestHandler):
    server_version = "CirosPaintPlayer/0.9.4"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path not in {"/", "/player"}:
            self.send_error(404)
            return
        body = self.server.player_html.encode("utf-8")  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; frame-src https://www.youtube.com https://www.youtube-nocookie.com",
        )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        # Keep the desktop application console/log clean.
        return


class LoopbackPlayerServer:
    """Tiny local-only HTTP host for one embedded player page.

    Binding to 127.0.0.1 means the page is never exposed on the LAN. Loading a
    real http://localhost page lets Chromium generate the iframe Referer itself,
    avoiding both the empty-Referer Error 153 and the synthetic-origin blocking
    seen in 0.9.3.
    """

    def __init__(self, video_id: str):
        self.video_id = _clean_video_id(video_id)
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _LoopbackHandler)
        self._httpd.daemon_threads = True
        self._httpd.player_html = build_youtube_player_html(self.video_id)  # type: ignore[attr-defined]
        self._thread: Thread | None = None

    @property
    def port(self) -> int:
        return int(self._httpd.server_address[1])

    @property
    def url(self) -> QUrl:
        return QUrl(f"http://localhost:{self.port}/player")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._httpd.serve_forever, name="CirosPaintYouTubeLoopback", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._httpd.shutdown()
            self._thread.join(timeout=1.5)
        self._httpd.server_close()
        self._thread = None


class YouTubePlayerDialog(QDialog):
    def __init__(self, video_id: str, title: str, video_url: str, parent=None):
        super().__init__(parent)
        self.video_id = _clean_video_id(video_id)
        self.video_url = video_url
        self._player_server = LoopbackPlayerServer(self.video_id)
        self._player_server.start()
        self.finished.connect(lambda _result: self._stop_player_server())

        self.setWindowTitle(title or "YouTube")
        self.resize(980, 680)
        self.setMinimumSize(760, 520)

        heading = QLabel(title or "YouTube")
        heading.setObjectName("TutorialTitle")
        heading.setWordWrap(True)

        self.web = QWebEngineView(self)
        self.web.setMinimumHeight(420)
        # Important: load a genuine local HTTP page. Do not use setHtml() with a
        # fabricated remote base URL and do not force a Referer interceptor.
        self.web.load(self._player_server.url)

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

    def _stop_player_server(self) -> None:
        server = getattr(self, "_player_server", None)
        if server is not None:
            server.stop()
            self._player_server = None

    def _open_youtube(self) -> None:
        QDesktopServices.openUrl(QUrl(self.video_url))
