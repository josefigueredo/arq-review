from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.board import render_board

META = {"pry": "PRY-2026-0028", "nombre": "PoC", "estado": "esperando-info", "nivel": "complejo",
        "vence": "2026-10-21", "epica": "PLATE-614", "jsm": "PEHD-86"}


def issue(key, summary, type_, parent=None, status="Backlog", category="todo", assignee=None):
    return {"key": key, "summary": summary, "type": type_, "status": status, "category": category,
            "parent": parent, "assignee": assignee}


ISSUES = [
    issue("PEHD-86", "PRY-2026-0028 · PoC", "Tarea", status="En curso", category="in_progress"),
    issue("PLATE-614", "[PRY-2026-0028] PoC", "Epic"),
    issue("PLATE-619", "Análisis y opciones", "Story", "PLATE-614"),
    issue("PLATE-615", "Intake y triage", "Story", "PLATE-614", status="Done", category="done"),
    issue("PLATE-616", "Normalizar pedido", "Subtarea", "PLATE-615", status="Done", category="done",
          assignee="Jose Figueredo"),
    issue("PLATE-626", "Abrir ticket del requirente y plazo", "Subtarea", "PLATE-615"),
    issue("PLATE-620", "Gap check de input mínimo", "Subtarea", "PLATE-619", status="En curso",
          category="in_progress"),
]


def url(key):
    return f"https://x.atlassian.net/browse/{key}"


class BoardTest(unittest.TestCase):
    def test_tree_with_status_symbols_and_progress(self):
        text = render_board(META, ISSUES, url)
        lines = text.splitlines()
        self.assertIn("PRY-2026-0028 · PoC — estado: esperando-info · nivel: complejo · vence: 2026-10-21", lines[0])
        self.assertIn("◐ PEHD-86", text)
        self.assertIn("[Tarea · En curso]", text)
        epic = next(i for i, line in enumerate(lines) if "PLATE-614" in line)
        tree = lines[epic:epic + 7]
        self.assertIn("○ PLATE-614", tree[0])
        self.assertTrue(tree[1].lstrip().startswith("├─ ✔ PLATE-615"), tree[1])  # ordenado por número
        self.assertIn("│  ├─ ✔ PLATE-616", tree[2])
        self.assertIn("Jose Figueredo", tree[2])
        self.assertIn("│  └─ ○ PLATE-626", tree[3])
        self.assertTrue(tree[4].lstrip().startswith("└─ ○ PLATE-619"), tree[4])
        self.assertIn("   └─ ◐ PLATE-620", tree[5])
        self.assertIn("Avance de la épica: 2 de 6 hechas · 1 en curso · 3 por hacer", text)
        self.assertNotIn("\x1b", text)

    def test_links_are_terminal_hyperlinks(self):
        text = render_board(META, ISSUES, url, links=True)
        self.assertIn("\x1b]8;;https://x.atlassian.net/browse/PLATE-614\x1b\\PLATE-614\x1b]8;;\x1b\\", text)
        self.assertIn("\x1b]8;;https://x.atlassian.net/browse/PEHD-86\x1b\\PEHD-86", text)

    def test_missing_issues_are_reported_not_hidden(self):
        text = render_board(dict(META, jsm="PEHD-99"), ISSUES[1:], url)
        self.assertIn("PEHD-99 (no se encontró en Jira)", text)
        orphan = render_board(META, ISSUES + [issue("PLATE-700", "Suelta", "Tarea", "PLATE-999")], url)
        self.assertIn("Otros issues con el label", orphan)
        self.assertIn("PLATE-700", orphan)


if __name__ == "__main__":
    unittest.main()
