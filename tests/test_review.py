from __future__ import annotations

import unittest

import helpers
from arqlib.review import FIELDS, ReviewError, load, new_review, review_path, save


MAIL = "requester@example.com"


class ReviewTest(unittest.TestCase):
    def test_new_review(self):
        repo = helpers.make_repo()
        path = new_review(repo, "PRY-2026-0028", "PoC modelos IA\nLocales", "Habilitar una G6e.xlarge\n", MAIL,
                          "reviewer@example.com")
        self.assertEqual(path, repo / "reviews" / "PRY-2026-0028.md")
        meta, body = load(repo, "PRY-2026-0028")
        self.assertEqual(list(meta), list(FIELDS))
        self.assertEqual((meta["pry"], meta["nombre"], meta["estado"], meta["contacto"], meta["head"]), (
            "PRY-2026-0028", "PoC modelos IA Locales", "recibido", MAIL, "reviewer@example.com"))
        self.assertEqual(body, "## Pedido original\n\nHabilitar una G6e.xlarge\n")

    def test_new_review_refuses_overwrite(self):
        repo = helpers.make_repo()
        new_review(repo, "PRY-2026-0028", "x", "y", MAIL)
        with self.assertRaisesRegex(ReviewError, "ya existe"):
            new_review(repo, "PRY-2026-0028", "x", "y", MAIL)

    def test_invalid_email(self):
        repo = helpers.make_repo()
        for bad in ("pablo", "a@b", "a b@c.d", ""):
            with self.assertRaisesRegex(ReviewError, "email inválido"):
                new_review(repo, "PRY-2026-0028", "x", "y", bad)
        with self.assertRaisesRegex(ReviewError, "email inválido"):
            new_review(repo, "PRY-2026-0028", "x", "y", MAIL, "head")

    def test_malformed_and_traversal_ids_are_rejected(self):
        repo = helpers.make_repo()
        for bad in ("PRY-2026-28", "pry-2026-0028", "../../etc/passwd", "PRY-2026-0028/../x", ""):
            with self.assertRaisesRegex(ReviewError, "PRY inválido"):
                review_path(repo, bad)
        self.assertFalse((repo / "reviews").exists())

    def test_load_missing(self):
        with self.assertRaisesRegex(ReviewError, "arq new"):
            load(helpers.make_repo(), "PRY-2026-0001")

    def test_save_roundtrip(self):
        repo = helpers.make_repo()
        new_review(repo, "PRY-2026-0026", "Product Brain", "Migrar", "user@example.com")
        meta, body = load(repo, "PRY-2026-0026")
        meta["nivel"] = "complejo"
        save(repo, "PRY-2026-0026", meta, body + "\n## Análisis\n")
        self.assertEqual(load(repo, "PRY-2026-0026")[0]["nivel"], "complejo")


if __name__ == "__main__":
    unittest.main()
