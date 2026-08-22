from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from app.ui.material_visuals import BRAND_LOGO_FILES as MATERIAL_LOGOS, BrandBadge
from app.ui.pages.paints_page import BRAND_LOGO_FILES as PAINT_LOGOS, PaintCard


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(
    (ROOT / "app/assets/runtime_assets_manifest.json").read_text(encoding="utf-8")
)


class RuntimeAssetRegressionV01010Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_brand_mapping_matches_historical_manifest(self):
        expected = {
            "Vallejo": "vallejo.png",
            "Citadel": "citadel.png",
            "AK Interactive": "ak_interactive.png",
        }
        self.assertEqual(PAINT_LOGOS, expected)
        self.assertEqual(MATERIAL_LOGOS, expected)

    def test_required_brand_assets_exist_with_historical_hashes(self):
        for relative, expected_hash in MANIFEST["brand_assets"].items():
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash)

    def test_real_brand_samples_load_valid_pixmaps(self):
        for brand in ("Citadel", "Vallejo", "AK Interactive"):
            path = ROOT / "app/assets/brands" / PAINT_LOGOS[brand]
            self.assertFalse(QPixmap(str(path)).isNull(), brand)

    def test_known_brand_badges_use_images_instead_of_initials(self):
        for brand in ("Citadel", "Vallejo", "AK Interactive"):
            badge = BrandBadge(brand)
            self.assertIsNotNone(badge.pixmap(), brand)
            self.assertFalse(badge.pixmap().isNull(), brand)
            self.assertEqual(badge.text(), "")
            badge.close()

    def test_paint_cards_use_historical_brand_images(self):
        for index, brand in enumerate(("Citadel", "Vallejo", "AK Interactive"), start=1):
            paint = SimpleNamespace(
                id=index,
                brand=brand,
                name="Regression sample",
                primary_color="Otro",
                complementary_colors=[],
                swatch_hex="#334455",
                paint_type="Acrílico",
                total_units=1,
                display_status="Disponible",
            )
            card = PaintCard(paint, [])
            labels = [item for item in card.findChildren(QLabel) if item.objectName() == "BrandLogo"]
            self.assertEqual(len(labels), 1)
            self.assertIsNotNone(labels[0].pixmap(), brand)
            self.assertFalse(labels[0].pixmap().isNull(), brand)
            self.assertEqual(labels[0].text(), "")
            card.close()

    def test_missing_known_asset_keeps_safe_text_fallback(self):
        with patch.dict(MATERIAL_LOGOS, {"Citadel": "missing-historical-logo.png"}, clear=False):
            badge = BrandBadge("Citadel")
            self.assertEqual(badge.text(), "C")
            badge.close()


if __name__ == "__main__":
    unittest.main()
