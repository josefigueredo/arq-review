"""Dry-run preview: a self-contained HTML tree of what `arq jira --apply` would create."""
from __future__ import annotations

import re
from html import escape
from typing import Dict

_CODE = re.compile(r"\{\{(.+?)\}\}")
_BOLD = re.compile(r"(?<!\w)\*(.+?)\*(?!\w)")
_ITALIC = re.compile(r"(?<!\w)_(.+?)_(?!\w)")
_ESCAPED = re.compile(r"\\([\[\]{}])")


def _wiki(text: str) -> str:
    """Descriptions are Jira wiki markup (`{{code}}`, `*bold*`, `_italic_`); show them as Jira would, not raw."""
    parts = _CODE.split(escape(text))  # escaped first: user text can never inject tags
    for i in range(0, len(parts), 2):
        parts[i] = _ITALIC.sub(r"<em>\1</em>", _BOLD.sub(r"<strong>\1</strong>", parts[i]))
    for i in range(1, len(parts), 2):
        parts[i] = f"<code>{parts[i]}</code>"
    return _ESCAPED.sub(r"\1", "".join(parts))


def _li(node: dict, kind: str, children: str = "") -> str:
    labels = " ".join(f'<span class="l">{escape(label)}</span>' for label in node["labels"])
    return (f'<li><span class="k">{escape(kind)}</span> {escape(node["summary"])} {labels}'
            f'<div class="d">{_wiki(node["description"])}</div>{children}</li>')


def render_html(plan: dict, meta: Dict[str, str]) -> str:
    items = ""
    for item in plan["items"]:
        subs = "".join(_li(sub, "sub-task") for sub in item["subtasks"])
        items += _li(item, item["type"], f"<ul>{subs}</ul>")
    tree = _li(plan["epic"], "épica", f"<ul>{items}</ul>")
    title = escape(f"{meta.get('pry', '')} · vista previa")
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#fff;--fg:#172B4D;--muted:#626F86;--chip:#E9F2FF}}
@media (prefers-color-scheme: dark){{:root{{--bg:#1D2125;--fg:#DEE4EA;--muted:#9FADBC;--chip:#1C2B41}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;margin:0;padding:16px}}
ul{{list-style:none;padding-left:20px}} li{{margin:6px 0}}
.k{{font-weight:600;text-transform:uppercase;font-size:11px;color:var(--muted)}}
.l{{background:var(--chip);border-radius:3px;padding:0 6px;font-size:12px;margin-left:4px}}
.d{{color:var(--muted);font-size:13px}}
</style></head><body>
<h1>{title}</h1>
<p>Dry run: nada de esto existe todavía en Jira. Para crearlo, el usuario corre <code>arq jira {escape(meta.get('pry', ''))} --apply</code>.</p>
<ul>{tree}</ul>
</body></html>
"""
