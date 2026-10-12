from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.preview import render_html
from arqlib.structure import build_plan


class PreviewTest(unittest.TestCase):
    def test_lists_every_issue_and_labels(self):
        meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": "simple"}
        html = render_html(build_plan(meta), meta)
        self.assertIn("[PRY-2026-0028] PoC", html)
        self.assertIn("Publicar devolución", html)
        self.assertIn("track:coordinacion", html)
        self.assertTrue(html.startswith("<!doctype html>"))

    def test_escapes_user_text(self):
        meta = {"pry": "PRY-2026-0028", "nombre": "<script>alert(1)</script>", "nivel": "simple"}
        html = render_html(build_plan(meta), meta)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_renders_jira_wiki_markup_instead_of_showing_it_raw(self):
        meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": "complejo"}
        html = render_html(build_plan(meta), meta)
        body = html.split("<body>", 1)[1]  # the stylesheet has its own `}}`
        self.assertNotIn("{{", body)
        self.assertNotIn("}}", body)
        self.assertIn("<code>arq timebox PRY-2026-0028</code>", html)
        self.assertIn("<code>jsm_listo: si</code>", html)
        self.assertIn("<em>Generado por arq desde reviews/PRY-2026-0028.md.", html)

    def test_wiki_rendering_keeps_escaping_user_text(self):
        node = {"summary": "s", "labels": [], "description": "{{<b>x</b>}} y *<i>z</i>* \\[a\\]"}
        plan = {"epic": node, "items": []}
        html = render_html(plan, {"pry": "PRY-2026-0028"})
        self.assertNotIn("<b>x", html)
        self.assertIn("<code>&lt;b&gt;x&lt;/b&gt;</code>", html)
        self.assertIn("<strong>&lt;i&gt;z&lt;/i&gt;</strong> [a]", html)


if __name__ == "__main__":
    unittest.main()
