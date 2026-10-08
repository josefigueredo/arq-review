from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.structure import StructureError, build_plan, followup_plan, pry_label


def meta(nivel: str) -> dict:
    return {"pry": "PRY-2026-0028", "nombre": "PoC modelos IA Locales", "nivel": nivel}


class StructureTest(unittest.TestCase):
    def test_label(self):
        self.assertEqual(pry_label("PRY-2026-0028"), "pry:2026-0028")

    def test_simple_is_minimal_epic(self):
        plan = build_plan(meta("simple"))
        self.assertEqual(plan["epic"]["summary"], "[PRY-2026-0028] PoC modelos IA Locales")
        self.assertEqual(plan["epic"]["labels"], ["pry:2026-0028", "nivel:simple"])
        [task] = plan["items"]
        self.assertEqual((task["type"], task["summary"]), ("task", "Revisión PRY-2026-0028"))
        self.assertEqual([s["summary"] for s in task["subtasks"]], [
            "Triage y apertura", "Gap check de input mínimo", "Análisis y opciones", "Revisión y firma",
            "Publicar devolución"])
        self.assertEqual(task["subtasks"][0]["labels"], ["pry:2026-0028", "nivel:simple", "track:coordinacion"])

    def test_complejo_has_three_stories_by_default(self):
        plan = build_plan(meta("complejo"))
        self.assertEqual([i["summary"] for i in plan["items"]], [
            "Intake y triage", "Análisis y opciones", "Decisión y comunicación"])
        self.assertTrue(all(i["type"] == "story" for i in plan["items"]))
        self.assertEqual(plan["items"][2]["labels"][-2:], ["track:coordinacion", "track:tecnica"])

    def test_validacion_tecnica_is_opt_in(self):
        plan = build_plan(meta("complejo"), validacion=True)
        self.assertEqual(plan["items"][2]["summary"], "Validación técnica")
        self.assertEqual(len(plan["items"]), 4)

    def test_followup_one_subtask_per_condition(self):
        follow = followup_plan(meta("simple"), ["Apagado fuera de horario", "x" * 300])
        self.assertEqual(follow["parent_summary"], "Revisión PRY-2026-0028")
        self.assertEqual(follow["subtasks"][0]["summary"], "Condición: Apagado fuera de horario")
        self.assertLessEqual(len(follow["subtasks"][1]["summary"]), 240)
        self.assertIn("x" * 300, follow["subtasks"][1]["description"])
        self.assertEqual(follow["subtasks"][0]["labels"], ["pry:2026-0028", "nivel:simple", "track:coordinacion"])
        self.assertEqual(followup_plan(meta("complejo"), ["c"])["parent_summary"], "Decisión y comunicación")

    def test_followup_needs_conditions(self):
        with self.assertRaisesRegex(StructureError, "condición"):
            followup_plan(meta("simple"), ["  "])

    def test_every_issue_carries_pry_and_nivel_and_no_seniority(self):
        plan = build_plan(meta("complejo"), validacion=True)
        nodes = [plan["epic"]] + plan["items"] + [s for i in plan["items"] for s in i["subtasks"]]
        for node in nodes:
            self.assertEqual(node["labels"][:2], ["pry:2026-0028", "nivel:complejo"])
            self.assertFalse(any(word in " ".join(node["labels"]) for word in ("sr", "expert", "lead", "dev")))
            self.assertTrue(node["description"].strip())

    def test_issue_texts_are_channel_neutral(self):
        # the requester's ticket may live in JSM or in a software help desk (canal_requirente)
        plan = build_plan(meta("complejo"), validacion=True)
        nodes = [plan["epic"]] + plan["items"] + [s for i in plan["items"] for s in i["subtasks"]]
        for node in nodes:
            self.assertNotIn("JSM", node["summary"] + node["description"], node["summary"])

    def test_every_node_has_a_unique_stable_id(self):
        plan = build_plan(meta("complejo"), validacion=True)
        nodes = [plan["epic"]] + plan["items"] + [s for i in plan["items"] for s in i["subtasks"]]
        ids = [n["node"] for n in nodes]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(plan["epic"]["node"], "epica")
        self.assertIn("intake/abrir-ticket", ids)

    def test_followup_ids_depend_on_the_condition_not_its_position(self):
        a = followup_plan(meta("simple"), ["Apagado fuera de horario", "Presupuesto"])["subtasks"]
        b = followup_plan(meta("simple"), ["Presupuesto", "Apagado fuera de horario"])["subtasks"]
        self.assertEqual({n["node"] for n in a}, {n["node"] for n in b})
        self.assertTrue(all(n["node"].startswith("condicion/") for n in a))

    def test_every_description_says_why_what_how_and_done(self):
        for nivel in ("simple", "complejo"):
            plan = build_plan(meta(nivel), validacion=True)
            nodes = plan["items"] + [s for i in plan["items"] for s in i["subtasks"]]
            for node in nodes:
                text = node["description"]
                for part in ("Por qué: ", "Qué: ", "Cómo: ", "Terminado cuando: "):
                    self.assertIn(part, text, (node["node"], part))
                self.assertIn("Generado por arq desde reviews/PRY-2026-0028.md", text)

    def test_how_names_the_commands_for_this_pry(self):
        plan = build_plan(meta("complejo"))
        gap = next(s for i in plan["items"] for s in i["subtasks"] if s["node"] == "analisis/gap-check")
        self.assertIn("arq set PRY-2026-0028 faltantes=", gap["description"])

    def test_epic_description_comes_from_the_review(self):
        plan = build_plan(meta("complejo"), review_body="## Lo que entendimos\n\nMigrar PB `[pedido]`.\n")
        self.assertIn("h3. Lo que entendimos", plan["epic"]["description"])

    def test_descriptions_are_jira_wiki_without_ellipsis_placeholders(self):
        full = dict(meta("complejo"), contacto="requester@example.com", head="reviewer@example.com")
        plan = build_plan(full, validacion=True)
        nodes = plan["items"] + [s for i in plan["items"] for s in i["subtasks"]]
        for node in nodes:
            self.assertNotIn("`", node["description"], node["node"])
            self.assertNotIn("...", node["description"], node["node"])
        normalizar = next(s for i in plan["items"] for s in i["subtasks"] if s["node"] == "intake/normalizar")
        self.assertIn('{{arq new PRY-2026-0028 --nombre "PoC modelos IA Locales" --pedido <archivo con el pedido> '
                      '--contacto requester@example.com --head reviewer@example.com}}', normalizar["description"])

    def test_commands_without_known_values_say_what_goes_there(self):
        plan = build_plan(meta("complejo"))  # sin contacto ni head
        normalizar = next(s for i in plan["items"] for s in i["subtasks"] if s["node"] == "intake/normalizar")
        self.assertIn("--contacto <email del contacto>}}", normalizar["description"])
        self.assertNotIn("--head", normalizar["description"])

    def test_requires_triage(self):
        with self.assertRaisesRegex(StructureError, "arq triage"):
            build_plan(meta(""))


if __name__ == "__main__":
    unittest.main()
