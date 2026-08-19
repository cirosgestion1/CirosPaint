from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.database import get_session
from app.repositories.miniature_repository import MiniatureRepository
from app.services.miniature_catalog_service import MiniatureCatalogService
from app.ui.dialogs.miniature_dialogs import AddFactionDialog, AddMiniatureDialog, MiniatureDetailDialog


ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets"

STATE_VIEW = {
    None: {"label": "Todo", "field": "total_count", "color": "#E5E7EB", "button": "MiniStateAll"},
    "Sin montar": {"label": "Sin montar", "field": "unassembled_count", "color": "#9CA3AF", "button": "MiniStateUnassembled"},
    "Montado": {"label": "Montado", "field": "assembled_count", "color": "#EAB308", "button": "MiniStateAssembled"},
    "Pintado": {"label": "Pintado", "field": "painted_count", "color": "#3B82F6", "button": "MiniStatePainted"},
    "Terminado": {"label": "Terminado", "field": "finished_count", "color": "#22C55E", "button": "MiniStateFinished"},
}


def _asset_path(relative: str | None) -> Path:
    return ASSET_ROOT / (relative or "")


class ImageCard(QFrame):
    clicked = Signal()

    def __init__(self, image_asset: str | None, radius: int = 12, parent=None):
        super().__init__(parent)
        self.image_asset = image_asset
        self.radius = radius
        self.setCursor(Qt.PointingHandCursor)
        self._pixmap = QPixmap(str(_asset_path(image_asset))) if image_asset and _asset_path(image_asset).is_file() else QPixmap()

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
            painter.fillRect(self.rect(), QColor("#1c2635"))
        painter.fillRect(self.rect(), QColor(4, 8, 14, 78))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class GameBanner(ImageCard):
    def __init__(self, game: dict):
        super().__init__(game.get("image_asset"), radius=14)
        self.setObjectName("MiniatureGameBanner")
        self.setMinimumHeight(245)
        self.game = game
        title = QLabel(game["name"], self)
        title.setObjectName("MiniatureBannerTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.addStretch()
        layout.addWidget(title)
        layout.addStretch()


class FactionCard(ImageCard):
    def __init__(self, faction: dict):
        # Faction cards always use their own faction-specific miniature scene.
        super().__init__(faction.get("image_asset"), radius=12)
        self.setObjectName("MiniatureFactionCard")
        self.setMinimumHeight(168)
        self.setMaximumHeight(210)
        self.setMinimumWidth(260)
        title = QLabel(faction["name"], self)
        title.setObjectName("MiniatureFactionTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addStretch()
        layout.addWidget(title)


class FactionIcon(QLabel):
    def __init__(self, image_asset: str | None, size: int = 36):
        super().__init__()
        self.setFixedSize(size, size)
        self.setObjectName("FactionIcon")
        self.setAlignment(Qt.AlignCenter)
        path = _asset_path(image_asset)
        if image_asset and path.is_file():
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.setPixmap(pix.scaled(size - 5, size - 5, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            self.setText("◆")


class UnitArtPanel(ImageCard):
    """Image region for a collection unit.

    Legion keeps its individual official unit/product image and never falls back
    to faction artwork. Age of Sigmar deliberately reuses the faction miniature
    scene for units, avoiding hundreds of individual unit assets.
    """

    def __init__(self, image_asset: str | None, faction_fallback: str | None = None):
        self.unit_image_asset = image_asset
        self.faction_fallback = faction_fallback
        unit_path = _asset_path(image_asset)
        self.has_unit_art = bool(image_asset and unit_path.is_file())
        resolved = image_asset if self.has_unit_art else faction_fallback
        super().__init__(resolved, radius=10)
        self.setObjectName("MiniatureUnitArt")
        self.using_faction_fallback = bool(not self.has_unit_art and faction_fallback and _asset_path(faction_fallback).is_file())


class UnitCard(QFrame):
    clicked_entry = Signal(int)

    def __init__(self, entry, unit: dict, faction: dict, display_state: str | None = None):
        super().__init__()
        self.entry_id = entry.id
        self.entry = entry
        self.unit_image_asset = unit.get("image_asset")
        self.faction_icon_asset = faction.get("icon_asset")

        # Legion factions carry a dedicated icon_asset. Their units keep the
        # v0.8.1 rule: no scenic faction fallback. AoS units reuse faction art.
        is_legion = bool(self.faction_icon_asset)
        faction_fallback = None if is_legion else faction.get("image_asset")
        self.art = UnitArtPanel(self.unit_image_asset, faction_fallback)

        self.setObjectName("MiniatureUnitCard")
        self.setFixedHeight(164)
        self.setMinimumWidth(190)
        self.setMaximumWidth(245)
        self.setCursor(Qt.PointingHandCursor)

        icon = FactionIcon(self.faction_icon_asset, 32)
        name = QLabel(entry.unit_name)
        name.setObjectName("MiniatureUnitName")
        name.setWordWrap(True)
        name.setAttribute(Qt.WA_TransparentForMouseEvents)
        top = QHBoxLayout()
        top.addWidget(icon)
        top.addWidget(name, 1)

        self.qty = QLabel()
        self.qty.setObjectName("MiniatureUnitCount")
        self.qty.setAttribute(Qt.WA_TransparentForMouseEvents)
        role = QLabel(unit.get("primary_role", "Sin clasificar"))
        role.setObjectName("MiniatureUnitRole")
        role.setAttribute(Qt.WA_TransparentForMouseEvents)

        overlay = QVBoxLayout(self.art)
        overlay.setContentsMargins(10, 9, 10, 9)
        overlay.addLayout(top)
        overlay.addStretch()
        overlay.addWidget(role, 0, Qt.AlignLeft)
        overlay.addWidget(self.qty, 0, Qt.AlignLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.art)
        self.art.clicked.connect(lambda: self.clicked_entry.emit(self.entry_id))
        self.set_display_state(display_state)

    def set_display_state(self, state: str | None) -> None:
        config = STATE_VIEW.get(state, STATE_VIEW[None])
        field = config["field"]
        value = getattr(self.entry, field, 0)
        self.qty.setText(str(value))
        self.qty.setStyleSheet(f"color: {config['color']};")
        self.qty.setToolTip(config["label"])


class SummaryStat(QFrame):
    def __init__(self, label: str, value: int):
        super().__init__()
        self.setObjectName("MiniSummaryStat")
        v = QLabel(str(value))
        v.setObjectName("MiniSummaryNumber")
        v.setAlignment(Qt.AlignCenter)
        t = QLabel(label)
        t.setObjectName("MiniSummaryLabel")
        t.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(1)
        layout.addWidget(v)
        layout.addWidget(t)


class MiniaturesPage(QWidget):
    def __init__(self, on_changed=None):
        super().__init__()
        self.on_changed = on_changed
        self.current_game: str | None = None
        self.current_faction: str | None = None
        self.active_state_filter: str | None = None

        self.views = QStackedWidget()
        self.game_view = QWidget()
        self.faction_view = QWidget()
        self.collection_view = QWidget()
        self.views.addWidget(self.game_view)
        self.views.addWidget(self.faction_view)
        self.views.addWidget(self.collection_view)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.views)
        self._build_game_view()
        self._build_faction_view()
        self._build_collection_view()
        self.show_games()

    def _build_game_view(self):
        title = QLabel("Miniaturas")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Selecciona el universo de tu colección.")
        subtitle.setObjectName("Muted")
        banners = QVBoxLayout()
        banners.setSpacing(18)
        self.game_banners = []
        for game in MiniatureCatalogService.games():
            banner = GameBanner(game)
            banner.clicked.connect(lambda g=game["name"]: self.open_game(g))
            banners.addWidget(banner, 1)
            self.game_banners.append(banner)

        layout = QVBoxLayout(self.game_view)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addLayout(banners, 1)

    def _build_faction_view(self):
        self.faction_title = QLabel()
        self.faction_title.setObjectName("PageTitle")
        self.faction_subtitle = QLabel("Añade únicamente las facciones que formen parte de tu colección.")
        self.faction_subtitle.setObjectName("Muted")
        back = QPushButton("← Miniaturas")
        back.setObjectName("SecondaryButton")
        back.clicked.connect(self.show_games)
        add = QPushButton("+ Añadir facción")
        add.setObjectName("PrimaryButton")
        add.clicked.connect(self.add_faction)
        actions = QHBoxLayout()
        actions.addWidget(back)
        actions.addStretch()
        actions.addWidget(add)

        self.faction_host = QWidget()
        self.faction_grid = QGridLayout(self.faction_host)
        self.faction_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.faction_grid.setSpacing(14)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.faction_host)

        layout = QVBoxLayout(self.faction_view)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(12)
        layout.addLayout(actions)
        layout.addWidget(self.faction_title)
        layout.addWidget(self.faction_subtitle)
        layout.addWidget(scroll, 1)

    def _build_collection_view(self):
        back = QPushButton("← Facciones")
        back.setObjectName("SecondaryButton")
        back.clicked.connect(self.back_to_factions)

        self.state_buttons: dict[str | None, QPushButton] = {}
        state_actions = QHBoxLayout()
        state_actions.setSpacing(6)
        for state, config in STATE_VIEW.items():
            button = QPushButton(config["label"])
            button.setObjectName(config["button"])
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, value=state: self._toggle_state(value))
            self.state_buttons[state] = button
            state_actions.addWidget(button)

        self.add_unit_btn = QPushButton("+ Añadir miniatura")
        self.add_unit_btn.setObjectName("PrimaryButton")
        self.add_unit_btn.clicked.connect(self.add_unit)
        self.delete_faction_btn = QPushButton("Eliminar facción")
        self.delete_faction_btn.setObjectName("DangerCompactButton")
        self.delete_faction_btn.setMaximumWidth(126)
        self.delete_faction_btn.clicked.connect(self.delete_current_faction)

        right_actions = QVBoxLayout()
        right_actions.setContentsMargins(0, 0, 0, 0)
        right_actions.setSpacing(5)
        right_actions.setAlignment(Qt.AlignRight | Qt.AlignTop)
        right_actions.addWidget(self.delete_faction_btn, 0, Qt.AlignRight)
        right_actions.addWidget(self.add_unit_btn, 0, Qt.AlignRight)

        actions = QHBoxLayout()
        actions.addWidget(back)
        actions.addSpacing(6)
        actions.addLayout(state_actions)
        actions.addStretch()
        actions.addLayout(right_actions)

        self.collection_title = QLabel()
        self.collection_title.setObjectName("PageTitle")
        self.collection_subtitle = QLabel()
        self.collection_subtitle.setObjectName("Muted")
        self.summary_row = QHBoxLayout()
        self.summary_row.setSpacing(8)

        self.collection_host = QWidget()
        self.collection_layout = QVBoxLayout(self.collection_host)
        self.collection_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.collection_layout.setSpacing(14)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.collection_host)

        layout = QVBoxLayout(self.collection_view)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(10)
        layout.addLayout(actions)
        layout.addWidget(self.collection_title)
        layout.addWidget(self.collection_subtitle)
        layout.addLayout(self.summary_row)
        layout.addWidget(scroll, 1)
        self._sync_state_buttons()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child = item.layout()
            if widget:
                widget.deleteLater()
            elif child:
                MiniaturesPage._clear_layout(child)

    def show_games(self):
        self.current_game = None
        self.current_faction = None
        self.views.setCurrentWidget(self.game_view)

    def open_game(self, game_name: str):
        self.current_game = game_name
        self.current_faction = None
        self.faction_title.setText(game_name)
        self.views.setCurrentWidget(self.faction_view)
        self.refresh_factions()

    def back_to_factions(self):
        if self.current_game:
            self.views.setCurrentWidget(self.faction_view)
            self.refresh_factions()
        else:
            self.show_games()

    def refresh_factions(self):
        if not self.current_game:
            return
        self._clear_layout(self.faction_grid)
        game = MiniatureCatalogService.game(self.current_game) or {}
        with get_session() as session:
            stored = MiniatureRepository(session).list_factions(self.current_game)
        by_name = {f.get("name"): f for f in game.get("factions", [])}
        columns = max(2, min(4, max(700, self.width() - 280) // 310))
        for index, item in enumerate(stored):
            meta = by_name.get(item.faction, {"name": item.faction, "image_asset": None})
            card = FactionCard(meta)
            card.clicked.connect(lambda name=item.faction: self.open_faction(name))
            self.faction_grid.addWidget(card, index // columns, index % columns, Qt.AlignTop | Qt.AlignLeft)
        self.faction_grid.setColumnStretch(columns, 1)
        if not stored:
            empty = QLabel("Todavía no has añadido ninguna facción. Usa «Añadir facción» para empezar.")
            empty.setObjectName("Muted")
            empty.setWordWrap(True)
            self.faction_grid.addWidget(empty, 0, 0, 1, max(1, columns))

    def add_faction(self):
        game = MiniatureCatalogService.game(self.current_game or "")
        if not game:
            return
        with get_session() as session:
            repo = MiniatureRepository(session)
            existing = {f.faction for f in repo.list_factions(self.current_game)}
        dialog = AddFactionDialog(game, existing, self)
        if not dialog.exec():
            return
        data = dialog.data()
        if not data:
            return
        with get_session() as session:
            MiniatureRepository(session).add_faction(
                self.current_game, data["name"], data.get("grand_alliance")
            )
        self.refresh_factions()
        self._changed()

    def open_faction(self, faction_name: str):
        self.current_faction = faction_name
        self.active_state_filter = None
        self._sync_state_buttons()
        self.views.setCurrentWidget(self.collection_view)
        self.refresh_collection()

    def _toggle_state(self, state: str | None) -> None:
        if state is None:
            self.active_state_filter = None
        elif self.active_state_filter == state:
            # Second click on the active state returns to the default Todo view.
            self.active_state_filter = None
        else:
            self.active_state_filter = state
        self._sync_state_buttons()
        self.refresh_collection()

    def _sync_state_buttons(self) -> None:
        if not hasattr(self, "state_buttons"):
            return
        for state, button in self.state_buttons.items():
            button.blockSignals(True)
            button.setChecked(state == self.active_state_filter)
            button.blockSignals(False)

    def refresh_collection(self):
        if not self.current_game or not self.current_faction:
            return
        faction = MiniatureCatalogService.faction(self.current_game, self.current_faction) or {
            "name": self.current_faction, "units": []
        }
        self.collection_title.setText(self.current_faction)
        ga = faction.get("grand_alliance")
        self.collection_subtitle.setText(
            f"{self.current_game}" + (f" · Gran Alianza {ga}" if ga else "")
        )
        with get_session() as session:
            repo = MiniatureRepository(session)
            entries = repo.list_entries(self.current_game, self.current_faction)
            summary = repo.summary(self.current_game, self.current_faction)

        self._clear_layout(self.summary_row)
        for label, key in [
            ("Total", "total"), ("Sin montar", "unassembled"), ("Montado", "assembled"),
            ("Pintado", "painted"), ("Terminado", "finished")
        ]:
            self.summary_row.addWidget(SummaryStat(label, summary[key]), 1)

        unit_by_name = {u.get("name"): u for u in faction.get("units", [])}
        visible = []
        for entry in entries:
            unit = unit_by_name.get(entry.unit_name, {
                "name": entry.unit_name,
                "primary_role": "Sin clasificar",
                "secondary_tags": [],
                "image_asset": None,
            })
            visible.append((entry, unit))

        self._clear_layout(self.collection_layout)
        if not visible:
            empty = QLabel("Esta facción está vacía. Añade tu primera miniatura.")
            empty.setObjectName("Muted")
            empty.setWordWrap(True)
            self.collection_layout.addWidget(empty)
        else:
            grouped = defaultdict(list)
            for entry, unit in visible:
                grouped[unit.get("primary_role", "Sin clasificar")].append((entry, unit))
            role_order = [
                "Comandante", "Operativo", "Tropas", "Fuerzas especiales", "Apoyo", "Pesado",
                "Héroe", "Infantería", "Caballería", "Bestia", "Monstruo", "Máquina de guerra",
                "Sin clasificar",
            ]
            for role in role_order:
                items = grouped.get(role)
                if not items:
                    continue
                section = QLabel(role.upper())
                section.setObjectName("MiniSectionTitle")
                self.collection_layout.addWidget(section)
                self.collection_layout.addLayout(self._cards_grid(items, faction))

    def _cards_grid(self, items, faction):
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        columns = max(3, min(5, max(740, self.width() - 290) // 220))
        for index, (entry, unit) in enumerate(items):
            card = UnitCard(entry, unit, faction, self.active_state_filter)
            card.clicked_entry.connect(self.edit_entry)
            grid.addWidget(card, index // columns, index % columns, Qt.AlignTop | Qt.AlignLeft)
        grid.setColumnStretch(columns, 1)
        return grid

    def add_unit(self):
        faction = MiniatureCatalogService.faction(self.current_game or "", self.current_faction or "")
        if not faction:
            return
        with get_session() as session:
            repo = MiniatureRepository(session)
            existing = {e.unit_name for e in repo.list_entries(self.current_game, self.current_faction)}
        dialog = AddMiniatureDialog(self.current_faction, faction.get("units", []), existing, self)
        if not dialog.exec():
            return
        data = dialog.data()
        if not data:
            return
        unit = data.pop("unit")
        with get_session() as session:
            MiniatureRepository(session).upsert_entry(
                self.current_game, self.current_faction, unit["name"], **data
            )
        self.refresh_collection()
        self._changed()

    def edit_entry(self, entry_id: int):
        with get_session() as session:
            repo = MiniatureRepository(session)
            entry = repo.get_entry(entry_id)
            if not entry:
                return
            unit = MiniatureCatalogService.unit(entry.game, entry.faction, entry.unit_name) or {
                "name": entry.unit_name, "primary_role": "Sin clasificar", "secondary_tags": []
            }
            dialog = MiniatureDetailDialog(entry, unit, self)
            if not dialog.exec():
                return
            if dialog.delete_requested:
                repo.delete_entry(entry_id)
            else:
                repo.upsert_entry(entry.game, entry.faction, entry.unit_name, **dialog.data())
        self.refresh_collection()
        self._changed()

    def delete_current_faction(self):
        if not self.current_game or not self.current_faction:
            return
        answer = QMessageBox.question(
            self,
            "Eliminar facción",
            f"¿Eliminar {self.current_faction} y todas sus miniaturas de tu colección?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        with get_session() as session:
            repo = MiniatureRepository(session)
            item = next((f for f in repo.list_factions(self.current_game) if f.faction == self.current_faction), None)
            if item:
                repo.delete_faction(item.id)
        self.current_faction = None
        self.back_to_factions()
        self._changed()

    def refresh(self):
        if self.views.currentWidget() == self.faction_view:
            self.refresh_factions()
        elif self.views.currentWidget() == self.collection_view:
            self.refresh_collection()

    def _changed(self):
        if self.on_changed:
            self.on_changed()
