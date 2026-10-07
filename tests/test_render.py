from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.render import RenderError, assert_rendered, load_template, matches_template, render

TEMPLATES = ("analisis.md", "comentario-pry.md", "jsm-pedido-info.md", "jsm-devolucion.md", "jsm-cierre.md",
             "escalar-rfc.md")


class RenderTest(unittest.TestCase):
    def test_render(self):
        self.assertEqual(render("Hola {{contacto}} ({{pry}})", {"contacto": "Juan", "pry": "PRY-2026-0028"}),
                         "Hola Juan (PRY-2026-0028)")

    def test_render_lists_missing_values(self):
        with self.assertRaisesRegex(RenderError, "contacto, pry"):
            render("{{contacto}} {{pry}}", {"contacto": "  "})

    def test_assert_rendered(self):
        assert_rendered("todo completo")
        with self.assertRaisesRegex(RenderError, "nombre"):
            assert_rendered("Hola {{nombre}}")

    def test_all_templates_exist(self):
        for name in TEMPLATES:
            self.assertTrue(load_template(name).strip(), name)

    def test_unknown_template(self):
        with self.assertRaisesRegex(RenderError, "no existe"):
            load_template("../constraints.md")

    def test_filled_template_matches_even_reflowed(self):
        template = load_template("jsm-cierre.md")
        text = render(template, {"contacto": "Juan Pablo", "pry": "PRY-2026-0028", "nombre": "PoC",
                                 "vence": "2026-10-21"})
        self.assertTrue(matches_template(template, text))
        self.assertTrue(matches_template(template, " ".join(text.split())))  # otro ajuste de líneas

    def test_multiline_values_match(self):
        template = load_template("jsm-pedido-info.md")
        text = render(template, {"contacto": "Juan", "pry": "PRY-2026-0028", "nombre": "PoC",
                                 "faltantes": "- Fecha de baja\n- Costo mensual", "motivo": "Sin eso no hay caso.",
                                 "vence": "2026-10-21"})
        self.assertTrue(matches_template(template, text))

    def test_free_text_or_other_template_does_not_match(self):
        template = load_template("jsm-devolucion.md")
        self.assertFalse(matches_template(template, "127.0.0.1 localhost"))
        cierre = render(load_template("jsm-cierre.md"), {"contacto": "J", "pry": "P", "nombre": "N", "vence": "V"})
        self.assertFalse(matches_template(template, cierre))


if __name__ == "__main__":
    unittest.main()
