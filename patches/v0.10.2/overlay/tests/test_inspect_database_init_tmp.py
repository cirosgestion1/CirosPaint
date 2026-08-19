from __future__ import annotations

import inspect
import unittest

import app.db.database as database


class InspectDatabaseInitTemporaryTest(unittest.TestCase):
    def test_print_database_module(self):
        text = inspect.getsource(database).encode("ascii", errors="backslashreplace").decode("ascii")
        print("\n=== DATABASE_MODULE_START ===")
        print(text)
        print("=== DATABASE_MODULE_END ===\n")
        print("DATABASE_MEMBERS", sorted(name for name in dir(database) if not name.startswith("__")))
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
