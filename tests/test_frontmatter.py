from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib import frontmatter
from arqlib.frontmatter import FrontmatterError


class FrontmatterTest(unittest.TestCase):
    def test_roundtrip(self):
        meta = {"pry": "PRY-2026-0028", "estado": "recibido", "jsm": ""}
        text = frontmatter.dump(meta, "## Pedido original\n\nHola\n")
        self.assertEqual(frontmatter.parse(text), (meta, "## Pedido original\n\nHola\n"))

    def test_value_with_colon_keeps_everything_after_first_colon(self):
        meta, _ = frontmatter.parse("---\ndoc: https://x.y/z?a=b\n---\n\nbody")
        self.assertEqual(meta["doc"], "https://x.y/z?a=b")

    def test_missing_opening_fence(self):
        with self.assertRaisesRegex(FrontmatterError, "empezar con ---"):
            frontmatter.parse("pry: x\n---\n")

    def test_unclosed(self):
        with self.assertRaisesRegex(FrontmatterError, "no cierra"):
            frontmatter.parse("---\npry: x\n")

    def test_line_without_colon(self):
        with self.assertRaisesRegex(FrontmatterError, "línea 2"):
            frontmatter.parse("---\nsin dos puntos\n---\n")

    def test_dump_rejects_newline_in_value(self):
        with self.assertRaisesRegex(FrontmatterError, "nombre"):
            frontmatter.dump({"nombre": "a\nb"}, "")

    def test_as_list(self):
        self.assertEqual(frontmatter.as_list(" finops, seguridad ,,"), ["finops", "seguridad"])
        self.assertEqual(frontmatter.as_list(""), [])


if __name__ == "__main__":
    unittest.main()
