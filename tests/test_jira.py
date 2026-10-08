from __future__ import annotations

import io
import json
import unittest
import urllib.error

import helpers  # noqa: F401
from arqlib.jira import Jira, JiraError


class FakeOpener:
    """Records every request and answers from a queue of JSON bodies (or exceptions)."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, request, timeout=None):
        body = json.loads(request.data) if request.data else None
        self.calls.append((request.get_method(), request.full_url, body))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return io.BytesIO(json.dumps(response).encode() if response is not None else b"")


def client(opener, log=None):
    return Jira("https://x.atlassian.net/", "a@b", "t", opener=opener, journal=(log.append if log is not None else None))


class JiraTest(unittest.TestCase):
    def test_search_label_paginates_and_flattens(self):
        opener = FakeOpener(
            {"issues": [{"key": "ARQ-1", "fields": {"summary": "[PRY-2026-0028] x", "parent": None}}],
             "nextPageToken": "p2"},
            {"issues": [{"key": "ARQ-2", "fields": {"summary": "Revisión PRY-2026-0028", "parent": {"key": "ARQ-1"}}}]},
        )
        found = client(opener).search_label("pry:2026-0028")
        self.assertEqual(found, [{"key": "ARQ-1", "summary": "[PRY-2026-0028] x", "parent": None},
                                 {"key": "ARQ-2", "summary": "Revisión PRY-2026-0028", "parent": "ARQ-1"}])
        method, url, body = opener.calls[0]
        self.assertEqual((method, url), ("POST", "https://x.atlassian.net/rest/api/3/search/jql"))
        self.assertEqual(body["jql"], 'labels = "pry:2026-0028" ORDER BY key')
        self.assertEqual(opener.calls[1][2]["nextPageToken"], "p2")

    def test_search_label_rejects_jql_injection(self):
        with self.assertRaisesRegex(JiraError, "label inválido"):
            client(FakeOpener()).search_label('x" OR project = SECRET')

    def test_create_journals(self):
        log = []
        key = client(FakeOpener({"key": "ARQ-7"}), log).create({"summary": "s"})
        self.assertEqual(key, "ARQ-7")
        self.assertEqual(log, [{"action": "create", "key": "ARQ-7", "fields": {"summary": "s"}}])

    def test_link(self):
        opener, log = FakeOpener(None), []
        client(opener, log).link("JSM-1", "ARQ-1", "Relates")
        self.assertEqual(opener.calls[0], ("POST", "https://x.atlassian.net/rest/api/2/issueLink", {
            "type": {"name": "Relates"}, "inwardIssue": {"key": "JSM-1"}, "outwardIssue": {"key": "ARQ-1"}}))
        self.assertEqual(log[0]["action"], "link")

    def test_create_request_on_behalf_of_requester(self):
        opener = FakeOpener({"issueKey": "JSM-12"})
        key = client(opener).create_request("3", "41", "PRY-2026-0028 · x", "desc", on_behalf_of="acc-juan")
        self.assertEqual(key, "JSM-12")
        self.assertEqual(opener.calls[0][2], {"serviceDeskId": "3", "requestTypeId": "41",
                                              "requestFieldValues": {"summary": "PRY-2026-0028 · x",
                                                                     "description": "desc"},
                                              "raiseOnBehalfOf": "acc-juan"})

    def test_create_without_key_in_response_is_a_jira_error(self):
        with self.assertRaisesRegex(JiraError, "sin clave"):
            client(FakeOpener({})).create({"summary": "s"})

    def test_find_user_exact_email(self):
        opener = FakeOpener([{"accountId": "a1", "emailAddress": "user@example.com"},
                             {"accountId": "a2", "emailAddress": "requester@example.com"}])
        self.assertEqual(client(opener).find_user("requester@example.com"), "a2")
        self.assertIn("/rest/api/3/user/search?query=requester%40example.com", opener.calls[0][1])

    def test_find_user_hidden_email_fails_closed(self):
        # user/search matches by prefix: a single hit with a hidden email may be someone else (ana@corp.com.ar)
        with self.assertRaisesRegex(JiraError, "no se puede confirmar"):
            client(FakeOpener([{"accountId": "a9"}])).find_user("ana@corp.com")

    def test_find_user_none_or_only_other_people(self):
        with self.assertRaisesRegex(JiraError, "cliente del Service Desk"):
            client(FakeOpener([])).find_user("x@y.com")
        with self.assertRaisesRegex(JiraError, "cliente del Service Desk"):
            client(FakeOpener([{"accountId": "a", "emailAddress": "x@y.com.ar"}])).find_user("x@y.com")
        with self.assertRaisesRegex(JiraError, "no se puede confirmar"):
            client(FakeOpener([{"accountId": "a"}, {"accountId": "b"}])).find_user("x@y.com")

    def test_participants_and_labels(self):
        opener, log = FakeOpener({}, None), []
        jira = client(opener, log)
        jira.add_participants("JSM-12", ["acc-head"])
        jira.add_labels("JSM-12", ["pry:2026-0028", "nivel:simple"])
        self.assertEqual(opener.calls[0], ("POST", "https://x.atlassian.net/rest/servicedeskapi/request/JSM-12/participant",
                                           {"accountIds": ["acc-head"]}))
        self.assertEqual(opener.calls[1], ("PUT", "https://x.atlassian.net/rest/api/2/issue/JSM-12",
                                           {"update": {"labels": [{"add": "pry:2026-0028"}, {"add": "nivel:simple"}]}}))
        self.assertEqual([e["action"] for e in log], ["jsm-participants", "labels"])

    def test_create_helpdesk_issue_with_reporter_and_labels(self):
        opener, log = FakeOpener({"key": "PEHD-90"}), []
        key = client(opener, log).create_helpdesk_issue("PEHD", "Tarea", "PRY-2026-0028 · x", "desc",
                                                        ["pry:2026-0028", "nivel:simple"], "acc-pablo")
        self.assertEqual(key, "PEHD-90")
        self.assertEqual(opener.calls[0], ("POST", "https://x.atlassian.net/rest/api/2/issue", {"fields": {
            "project": {"key": "PEHD"}, "issuetype": {"name": "Tarea"}, "summary": "PRY-2026-0028 · x",
            "description": "desc", "labels": ["pry:2026-0028", "nivel:simple"], "reporter": {"id": "acc-pablo"}}}))
        self.assertEqual(log[0]["action"], "helpdesk-issue")

    def test_rejected_reporter_names_the_missing_permission(self):
        error = urllib.error.HTTPError("u", 400, "Bad", {}, io.BytesIO(
            b'{"errors":{"reporter":"Field \'reporter\' cannot be set."}}'))
        with self.assertRaisesRegex(JiraError, "Modify reporter"):
            client(FakeOpener(error)).create_helpdesk_issue("PEHD", "Tarea", "s", "d", [], "acc-pablo")

    def test_watcher_and_plain_comment(self):
        opener, log = FakeOpener(None, {}), []
        jira = client(opener, log)
        jira.add_watcher("PEHD-90", "acc-felipe")
        jira.add_comment("PEHD-90", "hola")
        self.assertEqual(opener.calls[0], ("POST", "https://x.atlassian.net/rest/api/2/issue/PEHD-90/watchers",
                                           "acc-felipe"))
        self.assertEqual(opener.calls[1], ("POST", "https://x.atlassian.net/rest/api/2/issue/PEHD-90/comment",
                                           {"body": "hola"}))
        self.assertEqual([(e["action"], e.get("public")) for e in log], [("watcher", None), ("comment", True)])

    def test_entity_properties(self):
        opener, log = FakeOpener(None, {"key": "arq.node", "value": {"id": "epica"}}), []
        jira = client(opener, log)
        jira.set_property("PLATE-614", "arq.node", {"id": "epica"})
        self.assertEqual(jira.get_property("PLATE-614", "arq.node"), {"id": "epica"})
        self.assertEqual(opener.calls[0], ("PUT", "https://x.atlassian.net/rest/api/2/issue/PLATE-614/properties/arq.node",
                                           {"id": "epica"}))
        self.assertEqual(opener.calls[1][:2], ("GET", "https://x.atlassian.net/rest/api/2/issue/PLATE-614/properties/arq.node"))
        self.assertEqual(log[0]["action"], "property")
        missing = urllib.error.HTTPError("u", 404, "Not Found", {}, io.BytesIO(b"{}"))
        self.assertIsNone(client(FakeOpener(missing)).get_property("PLATE-614", "arq.node"))

    def test_search_board_reads_status_and_assignee(self):
        opener = FakeOpener({"issues": [
            {"key": "PLATE-616", "fields": {"summary": "Normalizar pedido", "issuetype": {"name": "Subtarea"},
                                            "status": {"name": "Done", "statusCategory": {"key": "done"}},
                                            "parent": {"key": "PLATE-615"},
                                            "assignee": {"displayName": "Jose Figueredo"}}},
            {"key": "PLATE-614", "fields": {"summary": "E", "issuetype": {"name": "Epic"},
                                            "status": {"name": "Backlog", "statusCategory": {"key": "new"}},
                                            "parent": None, "assignee": None}}]})
        jira = client(opener)
        board = jira.search_board("pry:2026-0028")
        self.assertEqual(board[0], {"key": "PLATE-616", "summary": "Normalizar pedido", "type": "Subtarea",
                                    "status": "Done", "category": "done", "parent": "PLATE-615",
                                    "assignee": "Jose Figueredo"})
        self.assertEqual((board[1]["category"], board[1]["assignee"]), ("todo", None))
        self.assertEqual(opener.calls[0][2]["fields"], ["summary", "issuetype", "status", "parent", "assignee"])
        self.assertEqual(jira.browse_url("PLATE-614"), "https://x.atlassian.net/browse/PLATE-614")

    def test_get_brief(self):
        opener = FakeOpener({"key": "ARQ-2", "fields": {"summary": "s", "parent": {"key": "ARQ-1"}}})
        self.assertEqual(client(opener).get_brief("ARQ-2"), {"key": "ARQ-2", "summary": "s", "parent": "ARQ-1"})
        missing = urllib.error.HTTPError("u", 404, "Not Found", {}, io.BytesIO(b"{}"))
        self.assertIsNone(client(FakeOpener(missing)).get_brief("ARQ-9"))

    def test_keys_are_validated_before_building_urls(self):
        jira = client(FakeOpener())
        for call in (lambda: jira.comment("../../rest/api/2/issue/X", "b", public=True),
                     lambda: jira.link("JSM-1", "ARQ-1/../x", "Relates"),
                     lambda: jira.add_labels("jsm-1", ["l"]),
                     lambda: jira.get_brief("")):
            with self.assertRaisesRegex(JiraError, "clave de Jira inválida"):
                call()

    def test_comment_public_and_internal_are_distinct(self):
        opener, log = FakeOpener({}, {}), []
        jira = client(opener, log)
        jira.comment("JSM-12", "hola", public=True)
        jira.comment("JSM-12", "debate", public=False)
        self.assertEqual(opener.calls[0][1], "https://x.atlassian.net/rest/servicedeskapi/request/JSM-12/comment")
        self.assertEqual([c[2]["public"] for c in opener.calls], [True, False])
        self.assertEqual([e["public"] for e in log], [True, False])

    def test_http_error(self):
        error = urllib.error.HTTPError("u", 400, "Bad", {}, io.BytesIO(b'{"errors":{"summary":"required"}}'))
        with self.assertRaisesRegex(JiraError, "HTTP 400.*summary"):
            client(FakeOpener(error)).create({})

    def test_network_error(self):
        with self.assertRaisesRegex(JiraError, "no se pudo conectar"):
            client(FakeOpener(urllib.error.URLError("dns"))).create({})


if __name__ == "__main__":
    unittest.main()
