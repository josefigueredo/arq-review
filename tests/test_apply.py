from __future__ import annotations

import unittest

import helpers
from arqlib.apply import apply_followups, apply_plan, ensure_request, known_from_journal
from arqlib.config import DEFAULT_CONFIG
from arqlib.jira import JiraError
from arqlib.structure import build_plan, followup_plan

TYPES = DEFAULT_CONFIG["issue_types"]


def plan(nivel: str = "simple") -> dict:
    return build_plan({"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": nivel})


class ApplyTest(unittest.TestCase):
    def test_creates_epic_task_and_subtasks_with_parents(self):
        jira = helpers.FakeJira()
        result = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual(result["epica"], "ARQ-1")
        self.assertEqual(len(result["created"]), 7)  # épica + task + 5 sub-tasks
        self.assertEqual(jira.issues["ARQ-2"]["parent"], "ARQ-1")
        self.assertEqual({jira.issues[k]["parent"] for k in ("ARQ-3", "ARQ-7")}, {"ARQ-2"})
        self.assertEqual(jira.issues["ARQ-3"]["type"], "Subtask")

    def test_rerun_is_idempotent(self):
        jira = helpers.FakeJira()
        apply_plan(plan(), jira, "ARQ", TYPES)
        again = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual((again["created"], len(again["reused"])), ([], 7))
        self.assertEqual(len(jira.issues), 7)

    def test_resumes_after_partial_failure_without_duplicates(self):
        jira = helpers.FakeJira(fail_on_create=4)
        with self.assertRaises(helpers.FailingJira):
            apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual(len(jira.issues), 3)
        jira.fail_on_create = None
        result = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual((len(result["reused"]), len(result["created"])), (3, 4))
        self.assertEqual(len(jira.issues), 7)

    def test_complejo_creates_epic_three_stories_and_their_subtasks(self):
        jira = helpers.FakeJira()
        apply_plan(plan("complejo"), jira, "ARQ", TYPES)
        self.assertEqual(len(jira.issues), 1 + 3 + 8)
        self.assertEqual(sum(1 for i in jira.issues.values() if i["type"] == "Story"), 3)

    def test_created_issues_carry_their_stable_id(self):
        jira = helpers.FakeJira()
        apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual(jira.get_property("ARQ-1", "arq.node"), {"id": "epica"})
        self.assertEqual(jira.get_property("ARQ-2", "arq.node"), {"id": "revision"})

    def test_renamed_issue_is_not_duplicated(self):
        jira = helpers.FakeJira()
        apply_plan(plan(), jira, "ARQ", TYPES)
        jira.rename("ARQ-3", "Triage (renombrado a mano)")
        jira.rename("ARQ-1", "Épica con otro nombre")
        again = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual((again["created"], again["epica"], len(jira.issues)), ([], "ARQ-1", 7))

    def test_legacy_issues_without_id_are_matched_by_text_once_and_migrated(self):
        jira = helpers.FakeJira()
        apply_plan(plan(), jira, "ARQ", TYPES)
        jira.properties.clear()  # creados por una versión anterior de arq
        again = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual((again["created"], len(jira.issues)), ([], 7))
        self.assertEqual(jira.get_property("ARQ-3", "arq.node"), {"id": "revision/triage"})
        jira.rename("ARQ-3", "otro texto")
        self.assertEqual(apply_plan(plan(), jira, "ARQ", TYPES)["created"], [])

    def test_followup_survives_rename(self):
        jira = helpers.FakeJira()
        meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": "simple"}
        apply_plan(plan(), jira, "ARQ", TYPES)
        follow = followup_plan(meta, ["Apagado fuera de horario"])
        [key] = apply_followups(follow, "pry:2026-0028", jira, "ARQ", TYPES)["created"]
        jira.rename(key, "Condición cumplida")
        jira.rename("ARQ-2", "Revisión (renombrada)")
        self.assertEqual(apply_followups(follow, "pry:2026-0028", jira, "ARQ", TYPES)["created"], [])

    def test_journal_covers_search_lag(self):
        jira = helpers.FakeJira(fail_on_create=4)
        with self.assertRaises(helpers.FailingJira):
            apply_plan(plan(), jira, "ARQ", TYPES)
        jira.fail_on_create = None
        jira.hidden = set(jira.issues)  # la búsqueda todavía no ve lo recién creado
        known = [{"key": k, "summary": i["summary"], "parent": i["parent"]} for k, i in jira.issues.items()]
        result = apply_plan(plan(), jira, "ARQ", TYPES, known=known)
        self.assertEqual((len(result["reused"]), len(result["created"])), (3, 4))
        self.assertEqual(len(jira.issues), 7)

    def test_journal_entry_for_a_deleted_issue_is_ignored(self):
        jira = helpers.FakeJira()
        known = [{"key": "ARQ-99", "summary": "[PRY-2026-0028] PoC", "parent": None}]
        self.assertEqual(apply_plan(plan(), jira, "ARQ", TYPES, known=known)["epica"], "ARQ-1")

    def test_known_from_journal(self):
        entries = [
            {"action": "create", "key": "ARQ-1", "fields": {"summary": "E", "labels": ["pry:2026-0028"]}},
            {"action": "create", "key": "ARQ-2", "fields": {"summary": "T", "labels": ["pry:2026-0028"],
                                                            "parent": {"key": "ARQ-1"}}},
            {"action": "create", "key": "ARQ-3", "fields": {"summary": "otro", "labels": ["pry:2026-0001"]}},
            {"action": "jsm-request", "key": "SD-4", "summary": "PRY-2026-0028 · PoC"},
            {"action": "jsm-request", "key": "SD-5", "summary": "PRY-2026-0001 · otro"},
        ]
        issues, jsm = known_from_journal(entries, "pry:2026-0028", "PRY-2026-0028")
        self.assertEqual(issues, [{"key": "ARQ-1", "summary": "E", "parent": None},
                                  {"key": "ARQ-2", "summary": "T", "parent": "ARQ-1"}])
        self.assertEqual(jsm, ["SD-4"])

    def test_followups_hang_from_the_review_task_and_are_idempotent(self):
        jira = helpers.FakeJira()
        meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": "simple"}
        apply_plan(plan(), jira, "ARQ", TYPES)
        follow = followup_plan(meta, ["Apagado fuera de horario"])
        first = apply_followups(follow, "pry:2026-0028", jira, "ARQ", TYPES)
        again = apply_followups(follow, "pry:2026-0028", jira, "ARQ", TYPES)
        [key] = first["created"]
        self.assertEqual(jira.issues[key]["parent"], "ARQ-2")  # la task "Revisión PRY-2026-0028"
        self.assertEqual(again["created"], [])

    def test_followups_need_the_epic_structure(self):
        follow = followup_plan({"pry": "PRY-2026-0028", "nivel": "simple"}, ["c"])
        with self.assertRaisesRegex(ValueError, "arq jira"):
            apply_followups(follow, "pry:2026-0028", helpers.FakeJira(), "ARQ", TYPES)

    def test_same_subtask_summary_under_different_parents_is_not_confused(self):
        jira = helpers.FakeJira()
        def sub(parent):
            return {"node": f"{parent}/firma", "summary": "Revisión y firma", "labels": ["pry:2026-0028"],
                    "description": "d"}
        custom = {"epic": {"node": "epica", "summary": "E", "labels": ["pry:2026-0028"], "description": "d"},
                  "items": [{"node": s, "type": "story", "summary": s, "labels": ["pry:2026-0028"], "description": "d",
                             "subtasks": [sub(s)]} for s in ("A", "B")]}
        apply_plan(custom, jira, "ARQ", TYPES)
        again = apply_plan(custom, jira, "ARQ", TYPES)
        self.assertEqual(len(jira.issues), 5)  # épica + 2 stories + 2 sub-tasks con el mismo nombre
        self.assertEqual(again["created"], [])


LABELS = ["pry:2026-0028", "nivel:simple"]
SOFT = dict(DEFAULT_CONFIG, canal_requirente="software", helpdesk_project="PEHD", helpdesk_issue_type="Tarea")
CONFIG = dict(DEFAULT_CONFIG, jsm_project="JSM", jsm_service_desk_id="3", jsm_request_type_id="41")


def request_meta(**extra: str) -> dict:
    meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "epica": "ARQ-1", "jsm": "", "jsm_listo": "",
            "contacto": "requester@example.com", "head": "reviewer@example.com"}
    meta.update(extra)
    return meta


class EnsureRequestTest(unittest.TestCase):
    def call(self, jira, meta, known_jsm=()):
        saved, ready = [], []
        result = ensure_request(meta, jira, CONFIG, "desc", LABELS, saved.append, lambda: ready.append(True),
                                known_jsm=known_jsm)
        return result, saved, ready

    def test_creates_on_behalf_of_requester_with_labels_head_and_link(self):
        jira = helpers.FakeJira()
        (key, created), saved, ready = self.call(jira, request_meta())
        self.assertEqual((key, created, saved, ready), ("JSM-1", True, ["JSM-1"], [True]))
        self.assertEqual(jira.issues["JSM-1"]["reporter"], "acc-pablo")
        self.assertEqual(jira.issues["JSM-1"]["labels"], LABELS)
        self.assertEqual(jira.participants, [("JSM-1", "acc-felipe")])
        self.assertEqual(jira.links, [("JSM-1", "ARQ-1", "Relates")])

    def test_unknown_requester_creates_nothing(self):
        jira = helpers.FakeJira()
        with self.assertRaisesRegex(JiraError, "cliente del Service Desk"):
            self.call(jira, request_meta(contacto="user@example.com"))
        self.assertEqual(jira.requests, [])

    def test_ready_request_is_skipped(self):
        jira = helpers.FakeJira()
        (key, created), saved, ready = self.call(jira, request_meta(jsm="JSM-9", jsm_listo="si"))
        self.assertEqual((key, created, jira.requests, saved, ready), ("JSM-9", False, [], [], []))

    def test_rerun_after_link_failure_finishes_the_link(self):
        jira = helpers.FakeJira()
        jira.fail_link = True
        meta = request_meta()
        with self.assertRaises(JiraError):
            self.call(jira, meta)
        jira.fail_link = False
        (key, created), _, ready = self.call(jira, request_meta(jsm="JSM-1"))
        self.assertEqual((key, created, ready, jira.requests), ("JSM-1", False, [True], ["JSM-1"]))
        self.assertEqual(jira.links, [("JSM-1", "ARQ-1", "Relates")])

    def test_existing_request_found_by_label_is_not_duplicated(self):
        jira = helpers.FakeJira(project="JSM")
        jira.create_request("3", "41", "PRY-2026-0028 · PoC", "d")
        jira.add_labels("JSM-1", LABELS)
        (key, created), saved, _ = self.call(jira, request_meta())
        self.assertEqual((key, created, saved, jira.requests), ("JSM-1", False, ["JSM-1"], ["JSM-1"]))

    def test_existing_request_from_journal_covers_search_lag(self):
        jira = helpers.FakeJira()
        jira.create_request("3", "41", "PRY-2026-0028 · PoC", "d")  # creado, pero sin labels todavía
        (key, created), _, _ = self.call(jira, request_meta(), known_jsm=["JSM-1"])
        self.assertEqual((key, created, jira.requests), ("JSM-1", False, ["JSM-1"]))

    def soft(self, jira, meta, known_jsm=()):
        saved, ready = [], []
        result = ensure_request(meta, jira, SOFT, "desc", LABELS, saved.append, lambda: ready.append(True),
                                known_jsm=known_jsm)
        return result, saved, ready

    def test_software_canal_creates_helpdesk_issue_with_reporter_watcher_and_link(self):
        jira = helpers.FakeJira()
        (key, created), saved, ready = self.soft(jira, request_meta())
        self.assertEqual((key, created, saved, ready), ("PEHD-1", True, ["PEHD-1"], [True]))
        self.assertEqual(jira.issues["PEHD-1"]["reporter"], "acc-pablo")
        self.assertEqual(jira.issues["PEHD-1"]["type"], "Tarea")
        self.assertEqual(jira.issues["PEHD-1"]["labels"], LABELS)
        self.assertEqual(jira.watchers, [("PEHD-1", "acc-felipe")])
        self.assertEqual((jira.participants, jira.links), ([], [("PEHD-1", "ARQ-1", "Relates")]))

    def test_software_canal_rejected_reporter_creates_nothing(self):
        jira = helpers.FakeJira()
        jira.reject_reporter = True
        with self.assertRaisesRegex(JiraError, "Modify reporter"):
            self.soft(jira, request_meta())
        self.assertEqual(jira.requests, [])

    def test_software_canal_finds_existing_ticket_by_label(self):
        jira = helpers.FakeJira()
        jira.create_helpdesk_issue("PEHD", "Tarea", "PRY-2026-0028 · PoC", "d", LABELS, "acc-pablo")
        (key, created), _, _ = self.soft(jira, request_meta())
        self.assertEqual((key, created, jira.requests), ("PEHD-1", False, ["PEHD-1"]))

    def test_known_from_journal_reads_helpdesk_issues(self):
        entries = [{"action": "helpdesk-issue", "key": "PEHD-7", "summary": "PRY-2026-0028 · PoC"}]
        self.assertEqual(known_from_journal(entries, "pry:2026-0028", "PRY-2026-0028")[1], ["PEHD-7"])

    def test_without_head_there_are_no_participants(self):
        jira = helpers.FakeJira()
        self.call(jira, request_meta(head=""))
        self.assertEqual(jira.participants, [])


if __name__ == "__main__":
    unittest.main()
