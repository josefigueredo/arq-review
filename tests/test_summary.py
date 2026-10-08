from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.summary import MAX_DESCRIPTION, md_to_wiki, render_epic

META = {"pry": "PRY-2026-0026", "nombre": "Product Brain", "estado": "esperando-info", "nivel": "complejo",
        "vence": "2026-10-22", "jsm": "PEHD-87", "firmante": "", "veredicto": "", "componente_debil": "datos",
        "senales": "seguridad, cloud", "faltantes": "rollback, dependencias"}

BODY = """## Pedido original

- Tipo: Migración

## Lo que entendimos

Mover PB a ACME Cross Domain `[pedido]`.

## Input faltante

- `rollback`: no hay plan `[C-DAT-04]`.

## Análisis preliminar (sin veredicto)

| Componente | Estado | Hallazgo |
|---|---|---|
| datos | débil | Gemini **sin** clasificación `[C-IA-02]` |

## Señales para otros sectores (sin veredicto)

- ⚠ Seguridad podría observar: datos a Gemini.
"""


class SummaryTest(unittest.TestCase):
    def test_header_has_state_and_key_fields(self):
        text = render_epic(META, BODY)
        self.assertTrue(text.startswith("h3. Revisión de Arquitectura · PRY-2026-0026 · Product Brain"))
        self.assertIn("*Estado:* esperando-info · *Nivel:* complejo · *Vence:* 2026-10-22", text)
        self.assertIn("*Veredicto:* — (sin veredicto)", text)
        self.assertIn("*Ticket del requirente:* PEHD-87", text)
        self.assertIn("*Input faltante:* rollback, dependencias", text)
        self.assertIn("*Componente más débil:* datos · *Señales:* seguridad, cloud", text)

    def test_review_sections_in_jira_wiki_format(self):
        text = render_epic(META, BODY)
        self.assertIn("h3. Lo que entendimos", text)
        self.assertIn("* {{rollback}}: no hay plan \\[C-DAT-04\\].", text)
        self.assertIn("|| Componente || Estado || Hallazgo ||", text)
        self.assertIn("| datos | débil | Gemini *sin* clasificación \\[C-IA-02\\] |", text)
        self.assertNotIn("|---|", text)
        self.assertLess(text.index("h3. Lo que entendimos"), text.index("h3. Pedido original"))  # el pedido va al final

    def test_footer_says_it_is_generated(self):
        self.assertIn("Generado por arq desde reviews/PRY-2026-0026.md", render_epic(META, ""))

    def test_md_to_wiki_escapes_macros_and_numbered_lists(self):
        self.assertEqual(md_to_wiki("1. uno {x}\n   - sub"), "# uno \\{x\\}\n** sub")

    def test_wrapped_paragraphs_and_bullets_become_single_lines(self):
        text = md_to_wiki("Primera parte del párrafo\ny su continuación.\n\n- Viñeta larga\n  que sigue acá.\n- Otra")
        self.assertEqual(text, "Primera parte del párrafo y su continuación.\n\n* Viñeta larga que sigue acá.\n* Otra")

    def test_long_reviews_are_truncated_under_jira_limit(self):
        text = render_epic(META, "## Lo que entendimos\n\n" + "x" * 50000)
        self.assertLessEqual(len(text), MAX_DESCRIPTION)
        self.assertIn("(recortado: el análisis completo está en reviews/PRY-2026-0026.md)", text)


if __name__ == "__main__":
    unittest.main()
