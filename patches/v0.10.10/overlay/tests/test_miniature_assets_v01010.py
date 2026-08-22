from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from app.services.miniature_catalog_service import MiniatureCatalogService
from app.ui.pages.miniatures_page import ASSET_ROOT, UnitArtPanel, _asset_path


EXPECTED_HISTORICAL_ASSETS = {
    "Stormtroopers": "miniatures/products/legion/swq11-stormtroopers.webp",
    "Scout Trooper Strike Team": "miniatures/products/legion/swq12-scout-troopers.webp",
    "Imperial Death Troopers": "miniatures/products/legion/swq205-imperial-death-troopers.webp",
    "74-Z Speeder Bikes": "miniatures/products/legion/swq207-74-z-speeder-bike.webp",
    "Darth Vader, Dark Lord of the Sith": "miniatures/products/legion/swq103-commander-darth-vader-and-general-veers.webp",
}

EXPECTED_SHA256 = {
    "miniatures/products/legion/swq11-stormtroopers.webp": "5cd413e32420023b511049312a2d2e92cf3bb6adec5aa5e0504daf3bc282962d",
    "miniatures/products/legion/swq12-scout-troopers.webp": "4be2c4c0bde42d0a42b2742bab6510cfc165ef70c92e5996328b811bd9c790e4",
    "miniatures/products/legion/swq205-imperial-death-troopers.webp": "e8bca6603c558e4752c5b4f852bea4c6b2541395f900f0d154ec2ae1d3c2abb1",
    "miniatures/products/legion/swq207-74-z-speeder-bike.webp": "d4251b260a1197bdd3939c66a8924651bf404609de2e3b9f546ef9845f8ac645",
    "miniatures/products/legion/swq103-commander-darth-vader-and-general-veers.webp": "6cbda996d933abfed8eff94b3eaf9d42f2ee267e41b190eadc18a6967ed53c10",
}


def _catalog_units() -> dict[str, dict]:
    return {
        unit["name"]: unit
        for game in MiniatureCatalogService.games()
        for faction in game.get("factions", [])
        for unit in faction.get("units", [])
    }


class MiniatureAssetRegressionV01010Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_catalog_keeps_historical_asset_mapping(self):
        units = _catalog_units()
        for name, expected in EXPECTED_HISTORICAL_ASSETS.items():
            self.assertIn(name, units)
            self.assertEqual(units[name].get("image_asset"), expected)

    def test_recovered_historical_assets_exist_with_validated_hashes(self):
        for relative, expected_hash in EXPECTED_SHA256.items():
            path = ASSET_ROOT / relative
            self.assertTrue(path.is_file(), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash)

    def test_representative_assets_load_as_real_pixmaps(self):
        for relative in EXPECTED_SHA256:
            pixmap = QPixmap(str(_asset_path(relative)))
            self.assertFalse(pixmap.isNull(), relative)
            self.assertGreater(pixmap.width(), 1)
            self.assertGreater(pixmap.height(), 1)

    def test_unit_panel_does_not_use_fallback_when_asset_exists(self):
        for relative in EXPECTED_SHA256:
            panel = UnitArtPanel(relative, "miniatures/icons/sw_empire.svg")
            self.assertTrue(panel.has_unit_art, relative)
            self.assertFalse(panel.using_faction_fallback, relative)
            self.assertFalse(panel._pixmap.isNull(), relative)
            panel.close()

    def test_other_faction_historical_asset_is_available(self):
        relative = "miniatures/products/legion/swq15-rebel-troopers.webp"
        path = _asset_path(relative)
        self.assertTrue(path.is_file(), path)
        self.assertFalse(QPixmap(str(path)).isNull())

    def test_build_source_contains_full_recovered_asset_set(self):
        files = [path for path in (ASSET_ROOT / "miniatures").rglob("*") if path.is_file()]
        self.assertEqual(len(files), 128)


if __name__ == "__main__":
    unittest.main()
