from __future__ import annotations

import re
import unittest

import helpers  # noqa: F401
from arqlib.paths import CONTRACT
from arqlib.triage import QUESTIONS, TriageError, classify, parse_answers

ALL_NO = ",".join(f"{qid}=no" for qid, _ in QUESTIONS)


class TriageTest(unittest.TestCase):
    def test_all_no_is_simple(self):  # PRY-2026-0028
        self.assertEqual(classify(parse_answers(ALL_NO)), "simple")

    def test_one_yes_is_complejo(self):
        self.assertEqual(classify(parse_answers(ALL_NO.replace("migracion=no", "migracion=si"))), "complejo")

    def test_product_brain_case_is_complejo(self):  # PRY-2026-0026
        text = ("multi_cuenta=si,migracion=si,fecha_comprometida=si,otros_equipos=si,"
                "datos_sensibles_o_ia=si,larga_o_productiva=no")
        self.assertEqual(classify(parse_answers(text)), "complejo")

    def test_accepts_sí_with_accent_and_spaces(self):
        answers = parse_answers(ALL_NO.replace("migracion=no", " migracion = Sí "))
        self.assertTrue(answers["migracion"])

    def test_missing_question(self):
        with self.assertRaisesRegex(TriageError, "faltan.*larga_o_productiva"):
            classify(parse_answers(ALL_NO.replace(",larga_o_productiva=no", "")))

    def test_unknown_question(self):
        with self.assertRaisesRegex(TriageError, "desconocidas.*color"):
            classify(parse_answers(ALL_NO + ",color=si"))

    def test_invalid_value(self):
        with self.assertRaisesRegex(TriageError, "si o no"):
            parse_answers("migracion=quizas")

    def test_contract_lists_exactly_the_questions(self):
        text = (CONTRACT / "triage.md").read_text(encoding="utf-8")
        ids = re.findall(r"^\| `(\w+)` \|", text, flags=re.M)
        self.assertEqual(ids, [qid for qid, _ in QUESTIONS])


if __name__ == "__main__":
    unittest.main()
