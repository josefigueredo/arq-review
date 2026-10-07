from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.inputs import InputsError, all_ids, input_ids


class InputsTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(input_ids("simple"), ["problema", "hipotesis_medible", "recursos", "duracion_y_baja",
                                               "costo_estimado", "responsable", "via_aprovisionamiento"])

    def test_complejo_includes_simple(self):
        ids = input_ids("complejo")
        self.assertEqual(ids[:7], input_ids("simple"))
        self.assertIn("rollback", ids)

    def test_ids_unique(self):
        self.assertEqual(len(all_ids()), len(set(all_ids())))

    def test_unknown_nivel(self):
        with self.assertRaisesRegex(InputsError, "nivel"):
            input_ids("medio")


if __name__ == "__main__":
    unittest.main()
