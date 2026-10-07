from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.state import StateError, transition


def meta(estado: str, **extra: str) -> dict:
    base = {"estado": estado, "firmante": "", "resultado": "", "veredicto": "", "faltantes": ""}
    base.update(extra)
    return base


class StateTest(unittest.TestCase):
    def test_happy_path(self):
        m = meta("recibido", veredicto="aprobar-con-condiciones")
        for to in ("triado", "esperando-info", "en-analisis", "en-firma"):
            m = transition(m, to)
        m["firmante"] = "edgardo.costilla"
        m = transition(m, "publicado")
        m = transition(m, "cerrado", resultado="condicionado")
        self.assertEqual((m["estado"], m["resultado"]), ("cerrado", "condicionado"))

    def test_same_state_is_a_no_op(self):
        for estado in ("esperando-info", "en-analisis", "triado"):
            self.assertEqual(transition(meta(estado), estado)["estado"], estado)

    def test_returns_copy(self):
        original = meta("recibido")
        transition(original, "triado")
        self.assertEqual(original["estado"], "recibido")

    def test_invalid_transition_lists_valid_ones(self):
        with self.assertRaisesRegex(StateError, r"recibido → publicado.*triado"):
            transition(meta("recibido"), "publicado")

    def test_unknown_current_state(self):
        with self.assertRaisesRegex(StateError, "desconocido"):
            transition(meta("inventado"), "triado")

    def test_en_firma_requires_verdict_and_complete_input(self):
        with self.assertRaisesRegex(StateError, "veredicto"):
            transition(meta("en-analisis"), "en-firma")
        with self.assertRaisesRegex(StateError, "input faltante"):
            transition(meta("en-analisis", veredicto="aprobar", faltantes="rollback"), "en-firma")

    def test_back_to_analysis_clears_the_signature(self):
        back = transition(meta("en-firma", veredicto="aprobar", firmante="juan"), "en-analisis")
        self.assertEqual(back["firmante"], "")

    def test_publicado_requires_firmante(self):
        with self.assertRaisesRegex(StateError, "firmante"):
            transition(meta("en-firma", veredicto="aprobar"), "publicado")

    def test_cerrado_requires_valid_resultado(self):
        with self.assertRaisesRegex(StateError, "resultado"):
            transition(meta("publicado", veredicto="aprobar"), "cerrado", resultado="quizas")

    def test_cerrado_resultado_must_match_verdict(self):
        with self.assertRaisesRegex(StateError, "rechazar.*rechazado"):
            transition(meta("publicado", veredicto="rechazar"), "cerrado", resultado="aprobado")
        closed = transition(meta("publicado", veredicto="rechazar"), "cerrado", resultado="rechazado")
        self.assertEqual(closed["resultado"], "rechazado")

    def test_resultado_only_when_closing(self):
        with self.assertRaisesRegex(StateError, "solo al cerrar"):
            transition(meta("recibido"), "triado", resultado="aprobado")

    def test_propuesta_rechazo_closes_only_as_rechazado(self):
        m = transition(meta("esperando-info"), "propuesta-rechazo")
        with self.assertRaisesRegex(StateError, "rechazado"):
            transition(m, "cerrado", resultado="aprobado")
        self.assertEqual(transition(m, "cerrado", resultado="rechazado")["resultado"], "rechazado")

    def test_cerrado_is_final(self):
        with self.assertRaises(StateError):
            transition(meta("cerrado"), "en-analisis")


if __name__ == "__main__":
    unittest.main()
