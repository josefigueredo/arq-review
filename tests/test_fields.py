from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.fields import FieldsError, apply_updates, parse_updates


def meta(**extra: str) -> dict:
    base = {"pry": "PRY-2026-0028", "nivel": "simple", "faltantes": "", "componente_debil": "", "senales": "",
            "veredicto": "", "firmante": "", "estado": "en-analisis"}
    base.update(extra)
    return base


class FieldsTest(unittest.TestCase):
    def test_parse_updates(self):
        self.assertEqual(parse_updates(["senales=finops, seguridad", "veredicto="]),
                         {"senales": "finops, seguridad", "veredicto": ""})
        with self.assertRaisesRegex(FieldsError, "campo=valor"):
            parse_updates(["senales"])

    def test_normalizes_lists(self):
        new = apply_updates(meta(), {"faltantes": " hipotesis_medible,,costo_estimado ", "senales": "finops"})
        self.assertEqual((new["faltantes"], new["senales"]), ("hipotesis_medible, costo_estimado", "finops"))

    def test_rejects_unknown_input_id_for_level(self):
        with self.assertRaisesRegex(FieldsError, "rollback"):
            apply_updates(meta(), {"faltantes": "rollback"})  # rollback es solo de nivel complejo

    def test_requires_triage_before_faltantes(self):
        with self.assertRaisesRegex(FieldsError, "arq triage"):
            apply_updates(meta(nivel=""), {"faltantes": "problema"})

    def test_rejects_non_editable_field(self):
        with self.assertRaisesRegex(FieldsError, "estado.*arq state"):
            apply_updates(meta(), {"estado": "cerrado"})

    def test_rejects_unknown_signal_component_and_verdict(self):
        for updates in ({"senales": "legales"}, {"componente_debil": "frontend"}, {"veredicto": "quizas"}):
            with self.assertRaises(FieldsError):
                apply_updates(meta(), updates)

    def test_no_verdict_with_missing_input(self):
        with self.assertRaisesRegex(FieldsError, "input faltante"):
            apply_updates(meta(faltantes="costo_estimado"), {"veredicto": "aprobar"})
        self.assertEqual(apply_updates(meta(), {"veredicto": "aprobar-con-condiciones"})["veredicto"],
                         "aprobar-con-condiciones")

    def test_returns_copy(self):
        original = meta()
        apply_updates(original, {"senales": "finops"})
        self.assertEqual(original["senales"], "")


if __name__ == "__main__":
    unittest.main()
