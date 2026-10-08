from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def make_repo() -> Path:
    """An empty team reviews repo in a temp dir."""
    return Path(tempfile.mkdtemp(prefix="arq-test-"))
from typing import Dict, List, Optional, Set  # noqa: E402

from arqlib.jira import JiraError  # noqa: E402

USERS = {"requester@example.com": "acc-pablo", "reviewer@example.com": "acc-felipe"}


class FailingJira(RuntimeError):
    pass


class FakeJira:
    """In-memory Jira + JSM with the same surface as arqlib.jira.Jira."""

    def __init__(self, project: str = "ARQ", fail_on_create: Optional[int] = None):
        self.project = project
        self.fail_on_create = fail_on_create  # the Nth create (1-based) raises, like a rejected issue
        self.creates = 0
        self.seq = 1
        self.issues: Dict[str, dict] = {}
        self.links: List[tuple] = []
        self.comments: List[tuple] = []
        self.requests: List[str] = []
        self.participants: List[tuple] = []
        self.users: Dict[str, str] = dict(USERS)
        self.hidden: Set[str] = set()  # created but not yet visible to search (eventual consistency)
        self.fail_link = False
        self.reject_reporter = False
        self.properties: Dict[tuple, dict] = {}
        self.watchers: List[tuple] = []

    def search_label(self, label: str) -> List[dict]:
        return [{"key": k, "summary": i["summary"], "parent": i["parent"]}
                for k, i in self.issues.items() if label in i["labels"] and k not in self.hidden]

    def get_brief(self, key: str) -> Optional[dict]:
        issue = self.issues.get(key)
        return {"key": key, "summary": issue["summary"], "parent": issue["parent"]} if issue else None

    def create(self, fields: dict) -> str:
        self.creates += 1
        if self.fail_on_create is not None and self.creates == self.fail_on_create:
            raise FailingJira(f"HTTP 400 en el alta #{self.creates}")
        key = f"{self.project}-{self.seq}"
        self.seq += 1
        self.issues[key] = {"summary": fields["summary"], "description": fields.get("description", ""),
                            "labels": list(fields.get("labels", [])),
                            "type": fields["issuetype"]["name"], "parent": (fields.get("parent") or {}).get("key")}
        return key

    def browse_url(self, key: str) -> str:
        return f"https://example.atlassian.net/browse/{key}"

    def search_board(self, label: str) -> List[dict]:
        return [{"key": k, "summary": i["summary"], "type": i["type"], "status": i.get("status", "Backlog"),
                 "category": i.get("category", "todo"), "parent": i["parent"], "assignee": i.get("assignee")}
                for k, i in self.issues.items() if label in i["labels"] and k not in self.hidden]

    def transition_done(self, key: str) -> Optional[str]:
        if self.issues[key].get("no_done"):
            return None
        self.issues[key].update(status="Done", category="done")
        return "Done"

    def transition_in_progress(self, key: str) -> Optional[str]:
        if self.issues[key].get("no_progress"):
            return None
        self.issues[key].update(status="En curso", category="in_progress")
        return "En curso"

    def update_description(self, key: str, text: str) -> None:
        self.issues[key]["description"] = text

    def rename(self, key: str, summary: str) -> None:
        """What a person does by hand in Jira."""
        self.issues[key]["summary"] = summary

    def set_property(self, key: str, name: str, value: dict) -> None:
        self.properties[(key, name)] = value

    def get_property(self, key: str, name: str) -> Optional[dict]:
        return self.properties.get((key, name))

    def link(self, inward: str, outward: str, link_type: str) -> None:
        if self.fail_link:
            raise JiraError("POST /rest/api/2/issueLink: HTTP 404")
        if (inward, outward, link_type) not in self.links:
            self.links.append((inward, outward, link_type))

    def find_user(self, email: str) -> str:
        if email not in self.users:
            raise JiraError(f"no se encontró a {email} en Jira: pedir que lo den de alta como cliente del Service Desk")
        return self.users[email]

    def create_request(self, service_desk_id: str, request_type_id: str, summary: str, description: str,
                       on_behalf_of: str = "") -> str:
        key = f"JSM-{len(self.requests) + 1}"
        self.requests.append(key)
        self.issues[key] = {"summary": summary, "labels": [], "type": "request", "parent": None,
                            "reporter": on_behalf_of}
        return key

    def add_participants(self, key: str, account_ids: List[str]) -> None:
        self.participants += [(key, a) for a in account_ids if (key, a) not in self.participants]

    def add_labels(self, key: str, labels: List[str]) -> None:
        current = self.issues[key]["labels"]
        current += [label for label in labels if label not in current]

    def comment(self, key: str, body: str, public: bool) -> None:
        self.comments.append((key, body, public))

    def create_helpdesk_issue(self, project: str, issue_type: str, summary: str, description: str,
                              labels: List[str], reporter: str) -> str:
        if self.reject_reporter:
            raise JiraError(f"Jira rechazó el reporter en {project}: darle a la cuenta el permiso Modify reporter")
        key = f"{project}-{len(self.requests) + 1}"
        self.requests.append(key)
        self.issues[key] = {"summary": summary, "labels": list(labels), "type": issue_type, "parent": None,
                            "reporter": reporter}
        return key

    def add_watcher(self, key: str, account_id: str) -> None:
        if (key, account_id) not in self.watchers:
            self.watchers.append((key, account_id))

    def add_comment(self, key: str, body: str) -> None:
        self.comments.append((key, body, True))
