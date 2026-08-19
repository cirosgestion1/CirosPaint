from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QMouseEvent, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.settings_store import SettingsStore
from app.db.database import get_session
from app.repositories.library_repository import LibraryRepository
from app.repositories.paint_repository import PaintRepository
from app.services.favorite_category_service import FavoriteCategoryService
from app.services.favorite_paint_analysis_service import FavoritePaintAnalysisService
from app.services.youtube_service import YouTubeApiError
from app.ui.dialogs.paint_analysis_dialog import PaintAnalysisDialog
from app.ui.dialogs.youtube_player_dialog import YouTubePlayerDialog
from app.ui.pages.tutorial_search_page import RemoteThumbnail, _human_count


ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets"
FOLDER_ASSETS = {
    FavoriteCategoryService.MINIATURES: "favorites/miniatures.svg",
    FavoriteCategoryService.GENERAL: "favorites/modeling_general.svg",
}


def _asset_path(relative: str | None) -> Path:
    return ASSET_ROOT / (relative or "")


def _load_banner_pixmap(relative: str | None) -> QPixmap:
    path = _asset_path(relative)
    if not relative or not path.is_file():
        return QPixmap()
    if path.suffix.lower() == ".svg":
        renderer = QSvgRenderer(str(path))
        if not renderer.isValid():
            return QPixmap()
        pixmap = QPixmap(1280, 360)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap
    return QPixmap(str(path))


class FavoriteImageCard(QFrame):
    clicked = Signal()

    def __init__(self, image_asset: str | None, radius: int = 14, parent=None):
        super().__init__(parent)
        self.radius = radius
        self._pixmap = _load_banner_pixmap(image_asset)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), self.radius, self.radius)
        painter.setClipPath(path)
        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor("#172033"))
        painter.fillRect(self.rect(), QColor(4, 8, 14, 92))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class FavoriteFolderBanner(FavoriteImageCard):
    def __init__(self, category: str, image_asset: str | None, parent=None):
        super().__init__(image_asset, radius=14, parent=parent)
        self.category = category
        self.setObjectName("MiniatureGameBanner")
        self.setMinimumHeight(205)
        self.setMaximumHeight(245)

        self.title = QLabel(category, self)
        self.title.setObjectName("MiniatureBannerTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.count = QLabel("0 vídeos", self)
        self.count.setAlignment(Qt.AlignCenter)
        self.count.setStyleSheet("color: #E5E7EB; font-size: 11pt; font-weight: 600;")
        self.count.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addWidget(self.count)
        layout.addStretch()

    def set_count(self, count: int) -> None:
        self.count.setText(f"{count} vídeo{'s' if count != 1 else ''}")


class DescriptionFetchThread(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, api_key: str, video_id: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.video_id = video_id

    def run(self):
        try:
            description = FavoritePaintAnalysisService.fetch_video_description(self.api_key, self.video_id)
        except YouTubeApiError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:
            self.failed.emit(f"No se ha podido leer la descripción del vídeo: {exc}")
            return
        self.succeeded.emit(description)


class FavoriteCard(QFrame):
    def __init__(self, favorite, category: str, on_deleted, on_category_changed, parent=None):
        super().__init__(parent)
        self.favorite = favorite
        self.current_category = category
        self.on_deleted = on_deleted
        self.on_category_changed = on_category_changed
        self._analysis_result = None
        self._analysis_thread: DescriptionFetchThread | None = None
        self.setObjectName("TutorialCard")
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(14)
        root.addWidget(RemoteThumbnail(favorite.thumbnail_url, self))

        body = QVBoxLayout()
        body.setSpacing(6)
        title = QLabel(favorite.title)
        title.setObjectName("TutorialTitle")
        title.setWordWrap(True)
        meta_bits = [favorite.channel_title]
        if favorite.duration_text:
            meta_bits.append(favorite.duration_text)
        if favorite.published_at:
            meta_bits.append(favorite.published_at[:4])
        meta = QLabel(" · ".join(bit for bit in meta_bits if bit))
        meta.setObjectName("TutorialMeta")
        stats = QLabel(f"▶ {_human_count(favorite.view_count)} visitas   ♥ {_human_count(favorite.like_count)}")
        stats.setObjectName("TutorialMeta")
        body.addWidget(title)
        body.addWidget(meta)
        body.addWidget(stats)
        body.addStretch()

        row = QHBoxLayout()
        play = QPushButton("▶ Reproducir")
        play.setObjectName("PrimaryButton")
        play.clicked.connect(self._play)
        open_button = QPushButton("Abrir en YouTube")
        open_button.setObjectName("SecondaryButton")
        open_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(favorite.video_url)))

        row.addWidget(play)
        row.addWidget(open_button)

        self.analyze_paints_button: QPushButton | None = None
        self.view_paints_button: QPushButton | None = None
        if category == FavoriteCategoryService.MINIATURES:
            self.analyze_paints_button = QPushButton("Analizar pinturas")
            self.analyze_paints_button.setObjectName("SecondaryButton")
            self.analyze_paints_button.setToolTip("Analiza únicamente la descripción pública del vídeo")
            self.analyze_paints_button.clicked.connect(self._analyze_paints)

            self.view_paints_button = QPushButton("Ver pinturas")
            self.view_paints_button.setObjectName("SecondaryButton")
            self.view_paints_button.setToolTip("Ver el último análisis de pinturas de este vídeo")
            self.view_paints_button.clicked.connect(self._show_paints)
            self.view_paints_button.setVisible(False)

            row.addWidget(self.analyze_paints_button)
            row.addWidget(self.view_paints_button)

        category_label = QLabel("Carpeta:")
        category_label.setObjectName("TutorialMeta")
        self.category_combo = QComboBox()
        self.category_combo.addItems(FavoriteCategoryService.CATEGORIES)
        self.category_combo.setCurrentText(category)
        self.category_combo.setToolTip("Puedes corregir manualmente la carpeta sugerida")
        self.category_combo.currentTextChanged.connect(self._change_category)

        delete = QPushButton("Eliminar")
        delete.setObjectName("DangerCompactButton")
        delete.clicked.connect(self._delete)
        row.addSpacing(8)
        row.addWidget(category_label)
        row.addWidget(self.category_combo)
        row.addStretch()
        row.addWidget(delete)
        body.addLayout(row)
        root.addLayout(body, 1)

    def _play(self):
        dialog = YouTubePlayerDialog(self.favorite.video_id, self.favorite.title, self.favorite.video_url, self)
        dialog.exec()

    def _analyze_paints(self):
        if self.current_category != FavoriteCategoryService.MINIATURES:
            return
        if self._analysis_thread and self._analysis_thread.isRunning():
            return

        api_key = SettingsStore.youtube_api_key()
        cached_description = str(getattr(self.favorite, "description", "") or "")
        if not api_key:
            if cached_description.strip():
                self._complete_paint_analysis(cached_description, refresh_cache=False)
                return
            QMessageBox.warning(
                self,
                "Analizar pinturas",
                "Falta la clave de YouTube Data API y este favorito no tiene una descripción guardada.",
            )
            return

        if self.analyze_paints_button:
            self.analyze_paints_button.setEnabled(False)
            self.analyze_paints_button.setText("Analizando…")

        thread = DescriptionFetchThread(api_key, self.favorite.video_id, self)
        self._analysis_thread = thread
        thread.succeeded.connect(lambda description: self._complete_paint_analysis(description, refresh_cache=True))
        thread.failed.connect(self._paint_analysis_fetch_failed)
        thread.finished.connect(self._finish_analysis_thread)
        thread.start()

    def _paint_analysis_fetch_failed(self, message: str):
        cached_description = str(getattr(self.favorite, "description", "") or "")
        if cached_description.strip():
            self._complete_paint_analysis(cached_description, refresh_cache=False)
            return
        QMessageBox.warning(self, "Analizar pinturas", message)

    def _finish_analysis_thread(self):
        self._analysis_thread = None
        if self.analyze_paints_button:
            self.analyze_paints_button.setEnabled(True)
            self.analyze_paints_button.setText("Analizar pinturas")

    def _complete_paint_analysis(self, description: str, refresh_cache: bool):
        description = str(description or "")
        try:
            with get_session() as session:
                library = LibraryRepository(session)
                if refresh_cache:
                    stored = library.get_by_video_id(self.favorite.video_id)
                    if stored is not None and stored.description != description:
                        stored.description = description
                        session.commit()
                        self.favorite.description = description
                inventory = PaintRepository(session).list()

            result = FavoritePaintAnalysisService().analyze_description(description, inventory)
        except Exception as exc:
            QMessageBox.warning(self, "Analizar pinturas", f"No se ha podido completar el análisis: {exc}")
            if self.analyze_paints_button:
                self.analyze_paints_button.setEnabled(True)
                self.analyze_paints_button.setText("Analizar pinturas")
            return

        self._analysis_result = result
        if self.view_paints_button:
            self.view_paints_button.setVisible(True)
        if self.analyze_paints_button:
            self.analyze_paints_button.setText("Analizar de nuevo")
            if not (self._analysis_thread and self._analysis_thread.isRunning()):
                self.analyze_paints_button.setEnabled(True)

    def _show_paints(self):
        if self._analysis_result is None:
            return
        dialog = PaintAnalysisDialog(self.favorite.title, self._analysis_result, self)
        dialog.exec()

    def _change_category(self, category: str):
        if category == self.current_category:
            return
        FavoriteCategoryService.set_manual_category(self.favorite.video_id, category)
        self.current_category = category
        self.on_category_changed()

    def _delete(self):
        answer = QMessageBox.question(
            self,
            "Eliminar de Favoritos",
            f"¿Eliminar «{self.favorite.title}» de Favoritos?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        with get_session() as session:
            LibraryRepository(session).remove_favorite(self.favorite.video_id)
        FavoriteCategoryService.clear_category(self.favorite.video_id)
        self.on_deleted()


class FavoritesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_category: str | None = None
        self._categorized_items: dict[str, list] = {category: [] for category in FavoriteCategoryService.CATEGORIES}

        self.views = QStackedWidget()
        self.folders_view = QWidget()
        self.category_view = QWidget()
        self.views.addWidget(self.folders_view)
        self.views.addWidget(self.category_view)

        self._build_folders_view()
        self._build_category_view()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.views)
        self.show_folders()

    def _build_folders_view(self):
        title = QLabel("Favoritos")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Tus tutoriales se organizan automáticamente por tipo de hobby. Puedes corregir la carpeta desde cada vídeo.")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        self.folder_status = QLabel("")
        self.folder_status.setObjectName("Muted")

        banners = QVBoxLayout()
        banners.setSpacing(18)
        self.folder_banners: dict[str, FavoriteFolderBanner] = {}
        for category in FavoriteCategoryService.CATEGORIES:
            banner = FavoriteFolderBanner(category, FOLDER_ASSETS.get(category), self.folders_view)
            banner.clicked.connect(lambda c=category: self.open_category(c))
            banners.addWidget(banner, 1)
            self.folder_banners[category] = banner

        layout = QVBoxLayout(self.folders_view)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.folder_status)
        layout.addLayout(banners, 1)

    def _build_category_view(self):
        top = QHBoxLayout()
        back = QPushButton("← Favoritos")
        back.setObjectName("SecondaryButton")
        back.clicked.connect(self.show_folders)
        self.category_title = QLabel("")
        self.category_title.setObjectName("PageTitle")
        top.addWidget(back)
        top.addSpacing(8)
        top.addWidget(self.category_title)
        top.addStretch()

        self.category_status = QLabel("")
        self.category_status.setObjectName("Muted")
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.cards_layout = QVBoxLayout(self.content)
        self.cards_layout.setContentsMargins(0, 0, 6, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.content)

        layout = QVBoxLayout(self.category_view)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addLayout(top)
        layout.addWidget(self.category_status)
        layout.addWidget(self.scroll, 1)

    def _clear_cards(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _load_categories(self) -> int:
        with get_session() as session:
            items = LibraryRepository(session).list_favorites()
        categorized = {category: [] for category in FavoriteCategoryService.CATEGORIES}
        for item in items:
            category = FavoriteCategoryService.category_for_favorite(item)
            categorized[category].append(item)
        self._categorized_items = categorized
        return len(items)

    def show_folders(self):
        self.current_category = None
        self.views.setCurrentWidget(self.folders_view)
        self.refresh()

    def open_category(self, category: str):
        if category not in FavoriteCategoryService.CATEGORIES:
            return
        self.current_category = category
        self.category_title.setText(category)
        self.views.setCurrentWidget(self.category_view)
        self.refresh()

    def refresh(self):
        total = self._load_categories()
        self.folder_status.setText(
            f"{total} favorito{'s' if total != 1 else ''} guardado{'s' if total != 1 else ''}."
            if total
            else "Todavía no has guardado ningún tutorial."
        )
        for category, banner in self.folder_banners.items():
            banner.set_count(len(self._categorized_items[category]))

        if self.current_category is None:
            return

        self._clear_cards()
        items = self._categorized_items[self.current_category]
        self.category_status.setText(
            f"{len(items)} vídeo{'s' if len(items) != 1 else ''} en esta carpeta."
            if items
            else "Esta carpeta todavía está vacía."
        )
        for item in items:
            card = FavoriteCard(item, self.current_category, self.refresh, self.refresh, self.content)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
