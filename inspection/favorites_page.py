from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.db.database import get_session
from app.repositories.library_repository import LibraryRepository
from app.ui.dialogs.youtube_player_dialog import YouTubePlayerDialog
from app.ui.pages.tutorial_search_page import RemoteThumbnail, _human_count


class FavoriteCard(QFrame):
    def __init__(self, favorite, on_deleted, parent=None):
        super().__init__(parent)
        self.favorite = favorite
        self.on_deleted = on_deleted
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
        delete = QPushButton("Eliminar")
        delete.setObjectName("DangerCompactButton")
        delete.clicked.connect(self._delete)
        row.addWidget(play)
        row.addWidget(open_button)
        row.addStretch()
        row.addWidget(delete)
        body.addLayout(row)
        root.addLayout(body, 1)

    def _play(self):
        dialog = YouTubePlayerDialog(self.favorite.video_id, self.favorite.title, self.favorite.video_url, self)
        dialog.exec()

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
        self.on_deleted()


class FavoritesPage(QWidget):
    def __init__(self):
        super().__init__()
        title = QLabel("Favoritos")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Tutoriales guardados para volver a ellos cuando quieras. El análisis inteligente llegará en la siguiente fase.")
        subtitle.setObjectName("Muted")

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.cards_layout = QVBoxLayout(self.content)
        self.cards_layout.setContentsMargins(0, 0, 6, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.status)
        layout.addWidget(self.scroll, 1)
        self.refresh()

    def _clear(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def refresh(self):
        self._clear()
        with get_session() as session:
            items = LibraryRepository(session).list_favorites()
        self.status.setText(f"{len(items)} favorito{'s' if len(items) != 1 else ''}" if items else "Todavía no has guardado ningún tutorial.")
        for item in items:
            card = FavoriteCard(item, self.refresh, self.content)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
