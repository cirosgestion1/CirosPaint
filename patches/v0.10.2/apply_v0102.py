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
        raise SystemExit("Usage: apply_v0102.py <build_source>")
    root = Path(sys.argv[1]).resolve()

    replace_once(root / "app/core/config.py", 'APP_VERSION = "0.10.1"', 'APP_VERSION = "0.10.2"')

    favorites = root / "app/ui/pages/favorites_page.py"
    replace_once(
        favorites,
        "from app.services.favorite_paint_analysis_service import FavoritePaintAnalysisService\n",
        "from app.services.favorite_paint_analysis_service import FavoritePaintAnalysisService\n"
        "from app.services.favorite_paint_purchase_service import FavoritePaintPurchaseService\n",
    )
    replace_once(
        favorites,
        "    def _show_paints(self):\n"
        "        if self._analysis_result is None:\n"
        "            return\n"
        "        dialog = PaintAnalysisDialog(self.favorite.title, self._analysis_result, self)\n"
        "        dialog.exec()\n",
        "    def _add_original_paint_to_future_purchases(self, catalog_paint):\n"
        "        with get_session() as session:\n"
        "            return FavoritePaintPurchaseService(session).add_to_future(catalog_paint)\n"
        "\n"
        "    def _show_paints(self):\n"
        "        if self._analysis_result is None:\n"
        "            return\n"
        "        dialog = PaintAnalysisDialog(\n"
        "            self.favorite.title,\n"
        "            self._analysis_result,\n"
        "            self,\n"
        "            on_add_to_future_purchases=self._add_original_paint_to_future_purchases,\n"
        "        )\n"
        "        dialog.exec()\n",
    )

    print("Ciros Paint 0.10.2 integration patches applied")


if __name__ == "__main__":
    main()
