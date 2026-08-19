from __future__ import annotations

import inspect
import unittest

import app.ui.dialogs.paint_basket_dialog as paint_basket_dialog


class InspectPurchaseApiTemporaryTest(unittest.TestCase):
    def test_print_future_purchase_source(self):
        print("\n=== PAINT_BASKET_DIALOG_SOURCE_START ===")
        print(inspect.getsource(paint_basket_dialog))
        print("=== PAINT_BASKET_DIALOG_SOURCE_END ===\n")
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
