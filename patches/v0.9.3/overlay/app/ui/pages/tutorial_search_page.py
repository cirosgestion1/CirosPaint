from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.settings_store import SettingsStore
from app.db.database import get_session
from app.repositories.library_repository import LibraryRepository
from app.services.favorite_category_service import FavoriteCategoryService
from app.services.tutorial_query_service import TutorialQueryService
from app.services.youtube_service import TutorialVideo, YouTubeApiError, YouTubeService
from app.ui.dialogs.youtube_player_dialog import YouTubePlayerDialog


def _human_count(value: int) -> str:
    value = max(0, int(value or 0))
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} M".replace(".0", "")
    if value >= 1_000:
        return f"{value / 1_000:.1f} mil".replace(".0", "")
    return str(value)


class SearchThread(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, api_key: str, original_query: str, search_query: str, language_code: str = "", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.original_query = original_query
        self.search_query = search_query
        self.language_code = language_code

    def run(self):
        try:
            results = YouTubeService(self.api_key).search_tutorials(
                self.original_query,
                self.search_query,
                language_code=self.language_code,
            )
        except YouTubeApiError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # keep UI alive on unexpected remote errors
            self.failed.emit(f"No se ha podido completar la búsqueda: {exc}")
            return
        self.succeeded.emit(results)


class RemoteThumbnail(QLabel):
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(224, 126)
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("TutorialThumbnail")
        self.setText("YouTube")
        self.setScaledContents(False)
        self._manager = QNetworkAccessManager(self)
        if url:
            reply = self._manager.get(QNetworkRequest(QUrl(url)))
            reply.finished.connect(partial(self._finished, reply))

    def _finished(self, reply):
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                pixmap = QPixmap()
                if pixmap.loadFromData(reply.readAll()):
                    self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.setText("")
        finally:
            reply.deleteLater()


class TutorialCard(QFrame):
    favorite_added = Signal(str)

    def __init__(self, video: TutorialVideo, source_query: str, parent=None):
        super().__init__(parent)
        self.video = video
        self.source_query = source_query
        self.setObjectName("TutorialCard")

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(14)
        root.addWidget(RemoteThumbnail(video.thumbnail_url, self))

        body = QVBoxLayout()
        body.setSpacing(6)
        title = QLabel(video.title)
        title.setObjectName("TutorialTitle")
        title.setWordWrap(True)
        meta_bits = [video.channel_title]
        if video.duration_text:
            meta_bits.append(video.duration_text)
        if video.published_year:
            meta_bits.append(video.published_year)
        meta = QLabel(" · ".join(bit for bit in meta_bits if bit))
        meta.setObjectName("TutorialMeta")
        stats = QLabel(f"▶ {_human_count(video.view_count)} visitas   ♥ {_human_count(video.like_count)}")
        stats.setObjectName("TutorialMeta")
        body.addWidget(title)
        body.addWidget(meta)
        body.addWidget(stats)
        body.addStretch()

        buttons = QHBoxLayout()
        play = QPushButton("▶ Reproducir")
        play.setObjectName("PrimaryButton")
        play.clicked.connect(self._play)
        open_youtube = QPushButton("Abrir en YouTube")
        open_youtube.setObjectName("SecondaryButton")
        open_youtube.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(video.video_url)))
        self.star = QPushButton("☆")
        self.star.setObjectName("FavoriteStarButton")
        self.star.setToolTip("Añadir a Favoritos")
        self.star.clicked.connect(self._favorite)
        buttons.addWidget(play)
        buttons.addWidget(open_youtube)
        buttons.addStretch()
        buttons.addWidget(self.star)
        body.addLayout(buttons)
        root.addLayout(body, 1)
        self.refresh_favorite_state()

    def refresh_favorite_state(self):
        with get_session() as session:
            favorite = LibraryRepository(session).is_favorite(self.video.video_id)
        self.star.setText("★" if favorite else "☆")
        self.star.setEnabled(not favorite)
        self.star.setToolTip("Ya está en Favoritos" if favorite else "Añadir a Favoritos")

    def _play(self):
        dialog = YouTubePlayerDialog(self.video.video_id, self.video.title, self.video.video_url, self)
        dialog.exec()

    def _favorite(self):
        with get_session() as session:
            LibraryRepository(session).add_favorite(self.video, self.source_query)
        FavoriteCategoryService.save_auto_category(self.video, self.source_query)
        self.refresh_favorite_state()
        self.favorite_added.emit(self.video.video_id)


class TutorialSearchPage(QWidget):
    def __init__(self):
        super().__init__()
        self._search_thread: SearchThread | None = None
        self._cards: list[TutorialCard] = []

        title = QLabel("Buscador de tutoriales")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Búsqueda especializada en pintura de miniaturas, modelismo, dioramas y escenografía.")
        subtitle.setObjectName("Muted")

        search_panel = QFrame()
        search_panel.setObjectName("Card")
        search_layout = QVBoxLayout(search_panel)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ej.: pintar Stormtrooper, hacer un árbol, barro para peanas...")
        self.input.returnPressed.connect(self.search)

        language_label = QLabel("Idioma:")
        language_label.setObjectName("Muted")
        self.language_filter = QComboBox()
        self.language_filter.setObjectName("TutorialLanguageFilter")
        self.language_filter.addItem("Todos", "")
        self.language_filter.addItem("Español", "es")
        self.language_filter.addItem("Inglés", "en")
        self.language_filter.setCurrentIndex(0)
        self.language_filter.setMinimumWidth(120)

        self.search_button = QPushButton("Buscar")
        self.search_button.setObjectName("PrimaryButton")
        self.search_button.clicked.connect(self.search)
        row.addWidget(self.input, 1)
        row.addWidget(language_label)
        row.addWidget(self.language_filter)
        row.addWidget(self.search_button)
        search_layout.addLayout(row)
        self.context_note = QLabel("Las consultas ambiguas se contextualizan automáticamente hacia el hobby antes de buscar en YouTube.")
        self.context_note.setObjectName("Muted")
        self.context_note.setWordWrap(True)
        search_layout.addWidget(self.context_note)

        self.status = QLabel("Escribe una búsqueda para empezar.")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.results_layout = QVBoxLayout(self.content)
        self.results_layout.setContentsMargins(0, 0, 6, 0)
        self.results_layout.setSpacing(10)
        self.results_layout.addStretch()
        self.scroll.setWidget(self.content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(search_panel)
        layout.addWidget(self.status)
        layout.addWidget(self.scroll, 1)

    def refresh(self):
        for card in self._cards:
            card.refresh_favorite_state()

    def _clear_results(self):
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._cards.clear()

    def search(self):
        if self._search_thread and self._search_thread.isRunning():
            return
        decision = TutorialQueryService.contextualize(self.input.text())
        if not decision.valid:
            self.status.setText(decision.reason)
            self._clear_results()
            return
        api_key = SettingsStore.youtube_api_key()
        if not api_key:
            self.status.setText("Falta la clave de YouTube Data API. Añádela en Ajustes y vuelve a buscar.")
            self._clear_results()
            return

        language_code = str(self.language_filter.currentData() or "")
        language_name = self.language_filter.currentText()
        self._clear_results()
        self.search_button.setEnabled(False)
        self.input.setEnabled(False)
        self.language_filter.setEnabled(False)
        self.status.setText(f"Buscando tutoriales para «{decision.original_query}» · idioma: {language_name}…")
        self.context_note.setText(f"Consulta contextualizada internamente: {decision.search_query}")
        thread = SearchThread(api_key, decision.original_query, decision.search_query, language_code, self)
        self._search_thread = thread
        thread.succeeded.connect(partial(self._show_results, decision.original_query, language_name))
        thread.failed.connect(self._show_error)
        thread.finished.connect(self._finish_search)
        thread.start()

    def _finish_search(self):
        self.search_button.setEnabled(True)
        self.input.setEnabled(True)
        self.language_filter.setEnabled(True)
        self.input.setFocus()

    def _show_error(self, message: str):
        self.status.setText(message)

    def _show_results(self, source_query: str, language_name: str, results):
        if not results:
            self.status.setText(f"No se han encontrado tutoriales suficientemente relacionados con el hobby en el filtro «{language_name}».")
            return
        self.status.setText(f"{len(results)} resultados · {language_name} · relevancia → visitas → Me gusta → actualidad")
        for video in results:
            card = TutorialCard(video, source_query, self.content)
            self._cards.append(card)
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)
