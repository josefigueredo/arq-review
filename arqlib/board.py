"""Read-only view of a PRY in Jira: the requester's ticket and the review epic as a tree, with status and progress."""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

SYMBOL = {"todo": "○", "in_progress": "◐", "done": "✔"}
_NUMBERED = re.compile(r"([A-Z][A-Z0-9]*)-(\d+)")


def _order(key: str) -> Tuple[str, int]:
    match = _NUMBERED.fullmatch(key)
    return (match.group(1), int(match.group(2))) if match else (key, 0)


def hyperlink(text: str, url: str, enabled: bool) -> str:
    """OSC 8 terminal hyperlink: clickable in iTerm2, Ghostty, WezTerm, kitty and VS Code; plain text when disabled."""
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\" if enabled else text


def _line(issue: Dict[str, Optional[str]], url: Callable[[str], str], links: bool) -> str:
    who = f" · {issue['assignee']}" if issue.get("assignee") else ""
    return (f"{SYMBOL.get(issue.get('category') or 'todo', '○')} {hyperlink(issue['key'], url(issue['key']), links)}  "
            f"{issue.get('summary') or ''}  [{issue.get('type')} · {issue.get('status')}{who}]")


def render_board(meta: Dict[str, str], issues: List[Dict[str, Optional[str]]], url: Callable[[str], str],
                 links: bool = False) -> str:
    by_key = {issue["key"]: issue for issue in issues}
    children: Dict[str, List[str]] = {}
    for issue in issues:
        if issue.get("parent"):
            children.setdefault(issue["parent"], []).append(issue["key"])
    lines = [f"{meta.get('pry')} · {meta.get('nombre')} — estado: {meta.get('estado')} · nivel: {meta.get('nivel')} · "
             f"vence: {meta.get('vence') or '—'}", "", "Ticket del requirente"]
    ticket = by_key.get(meta.get("jsm", ""))
    lines.append("  " + (_line(ticket, url, links) if ticket else f"{meta.get('jsm') or '—'} (no se encontró en Jira)"))
    lines += ["", "Épica de revisión"]
    shown = {meta.get("jsm", "")}
    epic = by_key.get(meta.get("epica", ""))
    if not epic:
        lines.append(f"  {meta.get('epica') or '—'} (no se encontró en Jira)")
    else:
        tree = [epic]
        lines.append("  " + _line(epic, url, links))
        shown.add(epic["key"])

        def walk(key: str, prefix: str) -> None:
            kids = sorted(children.get(key, []), key=_order)
            for index, kid in enumerate(kids):
                last = index == len(kids) - 1
                lines.append("  " + prefix + ("└─ " if last else "├─ ") + _line(by_key[kid], url, links))
                tree.append(by_key[kid])
                shown.add(kid)
                walk(kid, prefix + ("   " if last else "│  "))

        walk(epic["key"], "")
        count = {category: sum(1 for i in tree if i.get("category") == category) for category in SYMBOL}
        lines += ["", f"Avance de la épica: {count['done']} de {len(tree)} hechas · {count['in_progress']} en curso · "
                      f"{count['todo']} por hacer"]
    others = sorted((key for key in by_key if key not in shown), key=_order)
    if others:
        lines += ["", "Otros issues con el label"] + ["  " + _line(by_key[key], url, links) for key in others]
    return "\n".join(lines)
