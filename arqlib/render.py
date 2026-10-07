"""`{{name}}` placeholders in contract templates. Nothing public leaves with a placeholder left in it."""
from __future__ import annotations

import re
from typing import Dict

from arqlib.paths import CONTRACT

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
_NAME = re.compile(r"[\w-]+\.md")


class RenderError(ValueError):
    pass


def render(template: str, values: Dict[str, str]) -> str:
    missing = sorted({name for name in PLACEHOLDER.findall(template) if not values.get(name, "").strip()})
    if missing:
        raise RenderError(f"faltan valores para: {', '.join(missing)}")
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


def assert_rendered(text: str) -> None:
    left = sorted(set(PLACEHOLDER.findall(text)))
    if left:
        raise RenderError(f"quedan placeholders sin completar: {', '.join(left)}")


def load_template(name: str) -> str:
    path = CONTRACT / "templates" / name
    if not _NAME.fullmatch(name) or not path.exists():
        raise RenderError(f"la plantilla {name!r} no existe en {CONTRACT / 'templates'}")
    return path.read_text(encoding="utf-8")


def _literal(text: str) -> str:
    return r"\s+".join(re.escape(word) for word in text.split())


def matches_template(template: str, text: str) -> bool:
    """True when `text` is `template` with every placeholder filled, ignoring how whitespace and lines are laid out."""
    pieces = []
    for index, part in enumerate(PLACEHOLDER.split(template)):
        if index % 2:
            pieces.append(r"(.+?)")
        elif part.strip():
            pieces.append(_literal(part))
    return re.fullmatch(r"\s*".join(pieces), text.strip(), flags=re.S) is not None
