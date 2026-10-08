from __future__ import annotations

import json
import unittest
from pathlib import Path

import helpers
from arqlib import frontmatter
from arqlib.constraints import parse
from arqlib.evaluate import evaluate, evaluate_files
from arqlib.fields import COMPONENTES, SENALES
from arqlib.inputs import all_ids
from arqlib.paths import CONTRACT

GOLDEN = helpers.ROOT / "tests" / "golden"
REF = GOLDEN / "PRY-2026-0028" / "reference.md"


def cases():
    return sorted(p for p in GOLDEN.iterdir() if p.is_dir())


class GoldenContractTest(unittest.TestCase):
    def test_every_case_is_consistent_with_the_contract(self):
        constraint_ids = {c.id for c in parse((CONTRACT / "constraints.md").read_text(encoding="utf-8"))}
        self.assertEqual([p.name for p in cases()], ["PRY-2026-0026", "PRY-2026-0028"])
        for case in cases():
            self.assertTrue((case / "input.md").read_text(encoding="utf-8").strip(), case.name)
            expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
            self.assertTrue(set(expected["debe_pedir"]) <= set(all_ids()), case.name)
            self.assertTrue(set(expected["debe_citar"]) <= constraint_ids, case.name)
            self.assertIn(expected["componente_debil"], COMPONENTES, case.name)
            self.assertTrue(set(expected["senales"]) <= set(SENALES), case.name)


class EvaluateTest(unittest.TestCase):
    def setUp(self):
        self.expected = json.loads((GOLDEN / "PRY-2026-0028" / "expected.json").read_text(encoding="utf-8"))
        self.meta, self.body = frontmatter.parse(REF.read_text(encoding="utf-8"))

    def test_reference_passes(self):
        self.assertEqual(evaluate(self.expected, self.meta, self.body), [])
        self.assertEqual(evaluate_files(GOLDEN / "PRY-2026-0028", REF), [])

    def test_verdict_with_missing_input_fails(self):
        self.meta["veredicto"] = "aprobar"
        self.assertEqual(evaluate(self.expected, self.meta, self.body),
                         ["no debe emitir veredicto con input faltante"])

    def test_missing_citation_and_request_fail(self):
        self.meta["faltantes"] = "hipotesis_medible"
        failures = evaluate(self.expected, self.meta, self.body.replace("[C-PLAT-01]", ""))
        self.assertIn("debe citar [C-PLAT-01]", failures)
        self.assertIn("debe pedir costo_estimado", failures)

    def test_wrong_level_and_missing_signal_fail(self):
        self.meta.update(nivel="simple", senales="")
        failures = evaluate(self.expected, self.meta, self.body)
        self.assertIn("nivel: esperado 'complejo', obtenido 'simple'", failures)
        self.assertIn("debe señalar finops", failures)


if __name__ == "__main__":
    unittest.main()
