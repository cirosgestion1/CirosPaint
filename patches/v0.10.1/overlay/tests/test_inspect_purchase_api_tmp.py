from __future__ import annotations

import inspect
import unittest

from app.repositories.paint_repository import PaintRepository


class InspectPurchaseApiTemporaryTest(unittest.TestCase):
    def test_print_paint_repository_source(self):
        print("\n=== PAINT_REPOSITORY_SOURCE_START ===")
        print(inspect.getsource(PaintRepository))
        print("=== PAINT_REPOSITORY_SOURCE_END ===\n")
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
