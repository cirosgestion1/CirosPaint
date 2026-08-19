from __future__ import annotations

import inspect
import sys
import unittest

import app.models.paint as paint_models
import app.repositories.shopping_repository as shopping_repository


def safe_print(text: str) -> None:
    data = text.encode("ascii", errors="backslashreplace").decode("ascii")
    print(data)


class InspectPurchaseApiTemporaryTest(unittest.TestCase):
    def test_print_future_purchase_source(self):
        safe_print("\n=== PAINT_MODELS_SOURCE_START ===")
        safe_print(inspect.getsource(paint_models))
        safe_print("=== PAINT_MODELS_SOURCE_END ===\n")
        safe_print("\n=== SHOPPING_REPOSITORY_SOURCE_START ===")
        safe_print(inspect.getsource(shopping_repository))
        safe_print("=== SHOPPING_REPOSITORY_SOURCE_END ===\n")
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
