"""Apply a structure plan to Jira idempotently.

Issues are matched by (summary, parent) among (1) a search by the pry: label and (2) the keys the journal recorded,
confirmed one by one, because Jira Cloud's search/jql is eventually consistent and may miss what was just created.
"""
from __future__ import annotations

import hashlib
from typing import Callable, Dict, List, Optional, Sequence, Tuple


NODE_PROPERTY = "arq.node"


class ApplyError(ValueError):
    pass


def known_from_journal(entries: List[dict], label: str, pry: str) -> Tuple[List[dict], List[str]]:
    issues: List[dict] = []
    jsm: List[str] = []
    for entry in entries:
        fields = entry.get("fields") or {}
        if entry.get("action") == "create" and label in (fields.get("labels") or []):
            issues.append({"key": entry.get("key"), "summary": fields.get("summary"),
                           "parent": (fields.get("parent") or {}).get("key")})
        elif entry.get("action") in ("jsm-request", "helpdesk-issue") and \
                str(entry.get("summary", "")).startswith(f"{pry} "):
            jsm.append(entry.get("key"))
    return issues, jsm


def _found(client, label: str, known: Sequence[dict]) -> List[dict]:
    found = client.search_label(label)
    seen = {issue["key"] for issue in found}
    for entry in known:
        if entry.get("key") and entry["key"] not in seen:
            brief = client.get_brief(entry["key"])
            if brief is not None:
                found.append(brief)
                seen.add(brief["key"])
    return found


class _Index:
    """Existing issues by stable id; issues created before ids existed are kept by (summary, parent) to migrate."""

    def __init__(self, client, label: str, known: Sequence[dict]):
        self.by_node: Dict[str, str] = {}
        self.by_text: Dict[Tuple[str, Optional[str]], str] = {}
        self.desc: Dict[str, str] = {}  # key → hash of the description arq last wrote
        for issue in _found(client, label, known):
            prop = client.get_property(issue["key"], NODE_PROPERTY)
            if prop and prop.get("id"):
                self.by_node[prop["id"]] = issue["key"]
                self.desc[issue["key"]] = prop.get("desc", "")
            else:
                self.by_text[(issue["summary"], issue["parent"])] = issue["key"]


def _fields(project: str, issue_type: str, node: dict, parent: Optional[str]) -> dict:
    fields = {"project": {"key": project}, "issuetype": {"name": issue_type}, "summary": node["summary"],
              "description": node["description"], "labels": node["labels"]}
    if parent:
        fields["parent"] = {"key": parent}
    return fields


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


class _Ensurer:
    """Creates what is missing and keeps every description as arq generated it (arq owns descriptions; notes go in
    comments). A description is written only when its hash differs from the one stored in `arq.node`."""

    def __init__(self, client, project: str, index: _Index):
        self.client, self.project, self.index = client, project, index
        self.created: List[str] = []
        self.reused: List[str] = []
        self.updated: List[str] = []

    def __call__(self, node: dict, issue_type: str, parent: Optional[str]) -> str:
        digest = _digest(node["description"])
        key = self.index.by_node.get(node["node"])
        if key:
            self.reused.append(key)
            if self.index.desc.get(key) != digest:
                self._refresh(key, node, digest)
            return key
        key = self.index.by_text.pop((node["summary"], parent), None)
        if key:  # created before stable ids: adopt it once, by its text
            self.reused.append(key)
            self._refresh(key, node, digest)
            return key
        key = self.client.create(_fields(self.project, issue_type, node, parent))
        self.created.append(key)
        self._remember(key, node, digest)
        return key

    def _refresh(self, key: str, node: dict, digest: str) -> None:
        self.client.update_description(key, node["description"])
        self.updated.append(key)
        self._remember(key, node, digest)

    def _remember(self, key: str, node: dict, digest: str) -> None:
        self.client.set_property(key, NODE_PROPERTY, {"id": node["node"], "desc": digest})
        self.index.by_node[node["node"]] = key
        self.index.desc[key] = digest


def apply_plan(plan: dict, client, project: str, issue_types: Dict[str, str],
               known: Sequence[dict] = ()) -> Dict[str, object]:
    ensure = _Ensurer(client, project, _Index(client, plan["epic"]["labels"][0], known))
    epic = ensure(plan["epic"], issue_types["epic"], None)
    for item in plan["items"]:
        item_key = ensure(item, issue_types[item["type"]], epic)
        for sub in item["subtasks"]:
            ensure(sub, issue_types["subtask"], item_key)
    return {"epica": epic, "created": ensure.created, "reused": ensure.reused, "updated": ensure.updated,
            "nodes": dict(ensure.index.by_node)}


def sync_progress(client, label: str, nodes: Dict[str, str], done: set) -> Dict[str, List[str]]:
    """Move to Done every finished issue that is not there yet; leaves first, the epic last. Never moves back."""
    category = {issue["key"]: issue.get("category") for issue in client.search_board(label)}
    moved: List[str] = []
    blocked: List[str] = []
    for node in sorted(done, key=lambda n: (n == "epica", -n.count("/"))):
        key = nodes.get(node)
        if not key or category.get(key) == "done":
            continue
        (moved if client.transition_done(key) else blocked).append(key)
    return {"moved": moved, "blocked": blocked}


def sync_epic(client, key: str, epic: dict) -> None:
    """Rewrite the epic's description after the requester's ticket exists, so a first run is already complete."""
    client.update_description(key, epic["description"])
    client.set_property(key, NODE_PROPERTY, {"id": epic["node"], "desc": _digest(epic["description"])})


def apply_followups(follow: dict, label: str, client, project: str, issue_types: Dict[str, str],
                    known: Sequence[dict] = ()) -> Dict[str, object]:
    index = _Index(client, label, known)
    parent = index.by_node.get(follow["parent_node"]) or next(
        (key for (summary, _), key in index.by_text.items() if summary == follow["parent_summary"]), None)
    if not parent:
        raise ApplyError(f"no existe {follow['parent_summary']!r} en Jira: correr `arq jira` con --apply primero")
    ensure = _Ensurer(client, project, index)
    for sub in follow["subtasks"]:
        ensure(sub, issue_types["subtask"], parent)
    return {"created": ensure.created, "reused": ensure.reused, "updated": ensure.updated}


def _software(config: dict) -> bool:
    return config.get("canal_requirente", "jsm") == "software"


def _existing_request(client, config: dict, label: str, known_jsm: Sequence[str]) -> Optional[str]:
    project = config["helpdesk_project"] if _software(config) else config["jsm_project"]
    prefix = f"{project}-"
    for issue in client.search_label(label):
        if issue["key"].startswith(prefix):
            return issue["key"]
    for key in known_jsm:
        if key and client.get_brief(key) is not None:
            return key
    return None


def ensure_request(meta: Dict[str, str], client, config: dict, description: str, labels: List[str],
                   on_created: Callable[[str], None], on_ready: Callable[[], None],
                   known_jsm: Sequence[str] = ()) -> Tuple[str, bool]:
    """Create (or find) the JSM request on behalf of the requester, then label, add the head and link it.

    `on_created` runs as soon as the key is known, so a later failure never loses it; `on_ready` runs only when every
    step is done. A re-run with a key but not ready repeats the remaining idempotent steps.
    """
    if meta.get("jsm") and meta.get("jsm_listo"):
        return meta["jsm"], False
    key = meta.get("jsm") or _existing_request(client, config, labels[0], known_jsm)
    created = False
    summary = f"{meta['pry']} · {meta.get('nombre', '')}"
    if not key:
        requester = client.find_user(meta["contacto"])  # before creating: never raise a ticket on someone else's behalf
        if _software(config):
            key = client.create_helpdesk_issue(config["helpdesk_project"], config["helpdesk_issue_type"], summary,
                                               description, labels, requester)
        else:
            key = client.create_request(str(config["jsm_service_desk_id"]), str(config["jsm_request_type_id"]),
                                        summary, description, on_behalf_of=requester)
        created = True
    on_created(key)
    client.add_labels(key, labels)
    if meta.get("head"):
        head = client.find_user(meta["head"])
        if _software(config):
            client.add_watcher(key, head)
        else:
            client.add_participants(key, [head])
    client.link(key, meta["epica"], config["link_type"])
    on_ready()
    return key, created
