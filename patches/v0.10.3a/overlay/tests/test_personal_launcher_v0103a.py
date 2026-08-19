from __future__ import annotations

from pathlib import Path
import unittest

from app.core.config import APP_VERSION


class PersonalLauncherV0103aTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_version_marker_is_0103a(self):
        self.assertEqual(APP_VERSION, "0.10.3a")

    def test_personal_launcher_uses_local_venv_and_pythonw(self):
        launcher = (self.root / "CirosPaint.cmd").read_text(encoding="utf-8")
        self.assertIn(".venv", launcher)
        self.assertIn("pythonw.exe", launcher)
        self.assertIn("requirements.txt", launcher)
        self.assertIn("py -3.12", launcher)
        self.assertNotIn("CirosPaint_0.10.3a.exe", launcher)

    def test_debug_launcher_and_readme_are_in_package(self):
        self.assertTrue((self.root / "CirosPaint_DEBUG.cmd").is_file())
        self.assertTrue((self.root / "LEEME_0.10.3a.txt").is_file())


if __name__ == "__main__":
    unittest.main()
