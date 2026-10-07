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
        self.issues[key] = {"summary": fields["summary"], "labels": list(fields.get("labels", [])),
                            "type": fields["issuetype"]["name"], "parent": (fields.get("parent") or {}).get("key")}
        return key

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
