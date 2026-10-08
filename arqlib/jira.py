"""Small Jira Cloud + JSM client, stdlib only. Reads are never journaled; every successful write is."""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Dict, List, Optional

_LABEL = re.compile(r"[\w:.-]+")
_KEY = re.compile(r"[A-Z][A-Z0-9]+-\d+")


class JiraError(RuntimeError):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def check_key(key: str) -> str:
    if not _KEY.fullmatch(key or ""):
        raise JiraError(f"clave de Jira inválida {key!r}")
    return key


class Jira:
    def __init__(self, base_url: str, email: str, token: str, opener: Optional[Callable] = None,
                 timeout: float = 20.0, journal: Optional[Callable[[dict], None]] = None):
        self.base = base_url.rstrip("/")
        self._auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        self._open = opener or urllib.request.urlopen
        self._timeout = timeout
        self._journal = journal or (lambda entry: None)

    def _send(self, method: str, path: str, body: object = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": f"Basic {self._auth}", "Accept": "application/json", "Content-Type": "application/json"})
        try:
            with self._open(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise JiraError(f"{method} {path}: HTTP {exc.code} {exc.read()[:300].decode(errors='replace')}",
                            status=exc.code) from exc
        except urllib.error.URLError as exc:
            raise JiraError(f"{method} {path}: no se pudo conectar ({exc.reason})") from exc
        return json.loads(raw) if raw else {}

    def search_label(self, label: str) -> List[Dict[str, Optional[str]]]:
        if not _LABEL.fullmatch(label):
            raise JiraError(f"label inválido {label!r}")
        body: dict = {"jql": f'labels = "{label}" ORDER BY key', "fields": ["summary", "parent"], "maxResults": 100}
        found: List[Dict[str, Optional[str]]] = []
        while True:
            page = self._send("POST", "/rest/api/3/search/jql", body)
            for issue in page.get("issues", []):
                fields = issue.get("fields") or {}
                found.append({"key": issue["key"], "summary": fields.get("summary"),
                              "parent": (fields.get("parent") or {}).get("key")})
            token = page.get("nextPageToken")
            if not token:
                return found
            body = dict(body, nextPageToken=token)

    def get_brief(self, key: str) -> Optional[Dict[str, Optional[str]]]:
        check_key(key)
        try:
            issue = self._send("GET", f"/rest/api/2/issue/{key}?fields=summary,parent")
        except JiraError as exc:
            if exc.status == 404:
                return None
            raise
        fields = issue.get("fields") or {}
        return {"key": issue.get("key", key), "summary": fields.get("summary"),
                "parent": (fields.get("parent") or {}).get("key")}

    def create(self, fields: dict) -> str:
        key = self._send("POST", "/rest/api/2/issue", {"fields": fields}).get("key")
        if not key:
            raise JiraError("Jira respondió el alta sin clave de issue")
        self._journal({"action": "create", "key": key, "fields": fields})
        return key

    def link(self, inward: str, outward: str, link_type: str) -> None:
        check_key(inward)
        check_key(outward)
        self._send("POST", "/rest/api/2/issueLink", {"type": {"name": link_type}, "inwardIssue": {"key": inward},
                                                     "outwardIssue": {"key": outward}})
        self._journal({"action": "link", "inward": inward, "outward": outward, "type": link_type})

    def find_user(self, email: str) -> str:
        users = self._send("GET", f"/rest/api/3/user/search?query={urllib.parse.quote(email)}")
        users = users if isinstance(users, list) else []
        exact = [u for u in users if (u.get("emailAddress") or "").lower() == email.lower()]
        if len(exact) == 1:
            return exact[0]["accountId"]
        if any(not u.get("emailAddress") for u in users):
            # user/search matches by prefix and this site hides emails: never guess who the requester is
            raise JiraError(f"Jira oculta el email de los usuarios que coinciden con {email}: no se puede confirmar "
                            "la identidad. Pedir a un admin de Jira que haga visible el email (o que confirme la "
                            "cuenta) y volver a correr")
        raise JiraError(f"no se encontró a {email} en Jira: pedir que lo den de alta como cliente del Service "
                        "Desk y volver a correr")

    def create_request(self, service_desk_id: str, request_type_id: str, summary: str, description: str,
                       on_behalf_of: str = "") -> str:
        body = {"serviceDeskId": service_desk_id, "requestTypeId": request_type_id,
                "requestFieldValues": {"summary": summary, "description": description}}
        if on_behalf_of:
            body["raiseOnBehalfOf"] = on_behalf_of
        key = self._send("POST", "/rest/servicedeskapi/request", body).get("issueKey")
        if not key:
            raise JiraError("JSM respondió el alta sin clave de pedido")
        self._journal({"action": "jsm-request", "key": key, "summary": summary})
        return key

    def create_helpdesk_issue(self, project: str, issue_type: str, summary: str, description: str,
                              labels: List[str], reporter: str) -> str:
        """The requester's ticket in a software help desk: the requester is the reporter, never dropped (D12)."""
        fields = {"project": {"key": project}, "issuetype": {"name": issue_type}, "summary": summary,
                  "description": description, "labels": labels, "reporter": {"id": reporter}}
        try:
            key = self._send("POST", "/rest/api/2/issue", {"fields": fields}).get("key")
        except JiraError as exc:
            if exc.status == 400 and "reporter" in str(exc):
                raise JiraError(f"Jira rechazó el reporter en {project}: darle a la cuenta de la API el permiso "
                                "'Modify reporter' en ese proyecto y volver a correr. No se creó nada.",
                                status=400) from exc
            raise
        if not key:
            raise JiraError("Jira respondió el alta sin clave de issue")
        self._journal({"action": "helpdesk-issue", "key": key, "summary": summary})
        return key

    def add_watcher(self, key: str, account_id: str) -> None:
        check_key(key)
        self._send("POST", f"/rest/api/2/issue/{key}/watchers", account_id)
        self._journal({"action": "watcher", "key": key, "accountId": account_id})

    def add_comment(self, key: str, body: str) -> None:
        """A plain issue comment: in a software help desk every comment is visible to the requester."""
        check_key(key)
        self._send("POST", f"/rest/api/2/issue/{key}/comment", {"body": body})
        self._journal({"action": "comment", "key": key, "public": True, "body": body})

    def add_participants(self, key: str, account_ids: List[str]) -> None:
        check_key(key)
        self._send("POST", f"/rest/servicedeskapi/request/{key}/participant", {"accountIds": account_ids})
        self._journal({"action": "jsm-participants", "key": key, "accountIds": account_ids})

    def add_labels(self, key: str, labels: List[str]) -> None:
        check_key(key)
        for label in labels:
            if not _LABEL.fullmatch(label):
                raise JiraError(f"label inválido {label!r}")
        self._send("PUT", f"/rest/api/2/issue/{key}", {"update": {"labels": [{"add": label} for label in labels]}})
        self._journal({"action": "labels", "key": key, "labels": labels})

    def comment(self, key: str, body: str, public: bool) -> None:
        check_key(key)
        self._send("POST", f"/rest/servicedeskapi/request/{key}/comment", {"body": body, "public": public})
        self._journal({"action": "jsm-comment", "key": key, "public": public, "body": body})
