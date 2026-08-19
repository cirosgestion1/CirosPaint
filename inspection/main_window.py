from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.assistant_page import AssistantPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.favorites_page import FavoritesPage
from app.ui.pages.materials_page import MaterialsPage
from app.ui.pages.miniatures_page import MiniaturesPage
from app.ui.pages.paints_page import PaintsPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.shopping_page import ShoppingPage
from app.ui.pages.tutorial_search_page import TutorialSearchPage
from app.ui.styles import APP_STYLE


class PlaceholderPage(QWidget):
    def __init__(self, title_text: str, description: str):
        super().__init__()
        title = QLabel(title_text)
        title.setObjectName("PageTitle")
        text = QLabel(description)
        text.setWordWrap(True)
        text.setObjectName("Muted")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(text)
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ciros Paint")
        self.resize(1320, 820)
        self.setMinimumSize(1020, 650)
        self.setStyleSheet(APP_STYLE)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 22, 16, 18)
        side_layout.setSpacing(6)

        brand = QLabel("CIROS PAINT")
        brand.setObjectName("BrandTitle")
        subtitle = QLabel("PAINT · MINIATURES · AI")
        subtitle.setObjectName("BrandSubtitle")
        side_layout.addWidget(brand)
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(20)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.shopping = ShoppingPage()
        self.paints = PaintsPage(self.refresh_summary_pages)
        self.materials = MaterialsPage(self.refresh_summary_pages)
        self.miniatures = MiniaturesPage(self.refresh_summary_pages)
        self.recipes = TutorialSearchPage()
        self.saved = FavoritesPage()
        self.assistant = AssistantPage()
        self.settings = SettingsPage()

        pages = [
            ("⌂  Inicio", self.dashboard),
            ("●  Pinturas", self.paints),
            ("◆  Materiales", self.materials),
            ("▣  Compras", self.shopping),
            ("♟  Miniaturas", self.miniatures),
            ("⌕  Buscador de tutoriales", self.recipes),
            ("★  Favoritos", self.saved),
            ("✦  Asistente", self.assistant),
            ("⚙  Ajustes", self.settings),
        ]
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for index, (label, page) in enumerate(pages):
            self.stack.addWidget(page)
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            self.group.addButton(button)
            side_layout.addWidget(button)
            if index == 0:
                button.setChecked(True)
        side_layout.addStretch()
        version = QLabel("v0.9.0 · Local")
        version.setObjectName("Muted")
        version.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(version)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.dashboard.refresh()

    def navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        widget = self.stack.currentWidget()
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()

    def refresh_summary_pages(self):
        self.dashboard.refresh()
        self.shopping.refresh()
