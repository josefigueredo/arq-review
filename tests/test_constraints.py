from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.constraints import lint, parse
from arqlib.paths import CONTRACT

GOOD = """# x

### C-PLAT-01 · Recursos solo vía platform
- **Regla:** r
- **Severidad:** bloqueante
- **Por qué:** p
- **Cómo verificar:** c
- **Excepción:** e
"""


class ConstraintsTest(unittest.TestCase):
    def test_parse(self):
        [c] = parse(GOOD)
        self.assertEqual((c.id, c.titulo, c.severidad, c.como_verificar), (
            "C-PLAT-01", "Recursos solo vía platform", "bloqueante", "c"))

    def test_lint_ok(self):
        self.assertEqual(lint(GOOD), [])

    def test_shipped_contract_is_clean(self):
        text = (CONTRACT / "constraints.md").read_text(encoding="utf-8")
        self.assertEqual(lint(text), [])
        self.assertIn("C-PLAT-01", [c.id for c in parse(text)])

    def test_duplicate_id(self):
        self.assertIn("C-PLAT-01: ID duplicado", lint(GOOD + "\n" + GOOD.split("\n", 2)[2]))

    def test_invalid_severity(self):
        errors = lint(GOOD.replace("bloqueante", "urgente"))
        self.assertEqual(errors, ["C-PLAT-01: severidad inválida 'urgente' (bloqueante, condicionante, recomendación)"])

    def test_missing_field(self):
        self.assertEqual(lint(GOOD.replace("- **Excepción:** e\n", "")), ["C-PLAT-01: falta el campo Excepción"])

    def test_bad_heading(self):
        self.assertEqual(lint("### C-plat-1 · x\n"), ["encabezado inválido: '### C-plat-1 · x' (usar ### C-AREA-NN · título)"])

    def test_empty_file(self):
        self.assertEqual(lint("# nada"), ["no hay constraints"])


if __name__ == "__main__":
    unittest.main()
