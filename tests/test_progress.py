from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.progress import done_nodes
from arqlib.structure import build_plan


def meta(estado, nivel="complejo", **extra):
    base = {"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": nivel, "estado": estado, "jsm": "PEHD-86",
            "jsm_listo": "si", "vence": "2026-10-21"}
    base.update(extra)
    return base


def plan(m):
    return build_plan(m, validacion=True)


class ProgressTest(unittest.TestCase):
    def test_after_triage_and_jira(self):
        m = meta("triado")
        self.assertEqual(done_nodes(m, plan(m), info_published=False),
                         {"intake/normalizar", "intake/triage", "intake/abrir-ticket", "intake"})

    def test_ticket_not_ready_keeps_its_task_open(self):
        m = meta("triado", jsm_listo="")
        self.assertNotIn("intake/abrir-ticket", done_nodes(m, plan(m), info_published=False))
        self.assertNotIn("intake", done_nodes(m, plan(m), info_published=False))

    def test_gap_check_needs_the_information_request_published(self):
        m = meta("esperando-info")
        self.assertNotIn("analisis/gap-check", done_nodes(m, plan(m), info_published=False))
        self.assertIn("analisis/gap-check", done_nodes(m, plan(m), info_published=True))

    def test_analysis_done_at_signature_and_story_when_all_children_done(self):
        m = meta("en-firma")
        done = done_nodes(m, plan(m), info_published=True)
        self.assertTrue({"analisis/gap-check", "analisis/constraints", "analisis/opciones", "analisis"} <= done)
        self.assertNotIn("decision/firma", done)

    def test_closed_for_missing_information_does_not_fake_analysis(self):
        m = meta("cerrado", resultado="rechazado")  # cierre por plazo vencido: nunca hubo veredicto
        done = done_nodes(m, plan(m), info_published=True)
        self.assertTrue({"analisis/gap-check", "epica"} <= done)
        self.assertFalse({"analisis/constraints", "analisis/opciones", "decision/firma"} & done)

    def test_closed_marks_everything_but_optional_validation(self):
        m = meta("cerrado", veredicto="aprobar-con-condiciones")
        done = done_nodes(m, plan(m), info_published=True)
        self.assertTrue({"decision/firma", "decision/publicar", "decision", "epica"} <= done)
        self.assertFalse({"validacion", "validacion/prueba"} & done)

    def test_simple_level(self):
        m = meta("publicado", nivel="simple")
        done = done_nodes(m, plan(m), info_published=True)
        self.assertTrue({"revision/triage", "revision/gap-check", "revision/analisis", "revision/firma"} <= done)
        self.assertFalse({"revision/publicar", "revision", "epica"} & done)


if __name__ == "__main__":
    unittest.main()
