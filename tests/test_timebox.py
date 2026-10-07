from __future__ import annotations

import unittest
from datetime import date

import helpers  # noqa: F401
from arqlib.timebox import TimeboxError, add_business_days, is_overdue


class TimeboxTest(unittest.TestCase):
    def test_ten_business_days_from_wednesday(self):
        self.assertEqual(add_business_days(date(2026, 10, 7), 10), date(2026, 10, 21))

    def test_friday_plus_one_is_monday(self):
        self.assertEqual(add_business_days(date(2026, 10, 9), 1), date(2026, 10, 12))

    def test_saturday_start_plus_one_is_monday(self):
        self.assertEqual(add_business_days(date(2026, 10, 10), 1), date(2026, 10, 12))

    def test_days_must_be_positive(self):
        with self.assertRaises(TimeboxError):
            add_business_days(date(2026, 10, 7), 0)

    def test_overdue_only_after_the_due_day(self):
        self.assertFalse(is_overdue("2026-10-21", date(2026, 10, 21)))
        self.assertTrue(is_overdue("2026-10-21", date(2026, 10, 22)))

    def test_invalid_date(self):
        with self.assertRaisesRegex(TimeboxError, "fecha inválida"):
            is_overdue("21/10/2026", date(2026, 10, 22))


if __name__ == "__main__":
    unittest.main()
