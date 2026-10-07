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


if __name__ == "__main__":
    unittest.main()
