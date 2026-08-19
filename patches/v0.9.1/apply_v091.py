from __future__ import annotations

import sys
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v091.py <build_source>")
    root = Path(sys.argv[1]).resolve()

    tutorial = root / "app/ui/pages/tutorial_search_page.py"
    replace_once(
        tutorial,
        "from app.repositories.library_repository import LibraryRepository\n",
        "from app.repositories.library_repository import LibraryRepository\n"
        "from app.services.favorite_category_service import FavoriteCategoryService\n",
    )
    replace_once(
        tutorial,
        "        with get_session() as session:\n"
        "            LibraryRepository(session).add_favorite(self.video, self.source_query)\n"
        "        self.refresh_favorite_state()\n",
        "        with get_session() as session:\n"
        "            LibraryRepository(session).add_favorite(self.video, self.source_query)\n"
        "        FavoriteCategoryService.save_auto_category(self.video, self.source_query)\n"
        "        self.refresh_favorite_state()\n",
    )

    main_window = root / "app/ui/main_window.py"
    replace_once(
        main_window,
        "from app.ui.pages.assistant_page import AssistantPage\n",
        "from app.core.config import APP_VERSION\n"
        "from app.ui.pages.assistant_page import AssistantPage\n",
    )
    replace_once(
        main_window,
        '        version = QLabel("v0.9.0 · Local")\n',
        '        version = QLabel(f"v{APP_VERSION} · Local")\n',
    )

    dashboard = root / "app/ui/pages/dashboard_page.py"
    replace_once(
        dashboard,
        "from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget\n\n",
        "from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget\n\n"
        "from app.core.config import APP_VERSION\n\n",
    )
    replace_once(
        dashboard,
        '        info_title = QLabel("Ciros Paint 0.8.3.1")\n',
        '        info_title = QLabel(f"Ciros Paint {APP_VERSION}")\n',
    )
    replace_once(
        dashboard,
        '            "Inventario de pinturas rediseñado para colecciones grandes: tarjetas compactas, filtros combinables, "\n'
        '            "colores principales/complementarios y reposición automática por estado real de stock."\n',
        '            "Favoritos organizados en Miniaturas y Modelismo general, con clasificación automática al guardar "\n'
        '            "y corrección manual de carpeta cuando quieras."\n',
    )

    print("Ciros Paint 0.9.1 integration patches applied")


if __name__ == "__main__":
    main()
