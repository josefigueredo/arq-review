"""Flat `key: value` frontmatter. Values are single-line strings; lists are comma-separated."""
from __future__ import annotations

from typing import Dict, List, Tuple

FENCE = "---"


class FrontmatterError(ValueError):
    pass


def parse(text: str) -> Tuple[Dict[str, str], str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != FENCE:
        raise FrontmatterError("falta el frontmatter: el archivo tiene que empezar con ---")
    meta: Dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FENCE:
            return meta, "\n".join(lines[index + 1:]).lstrip("\n")
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            raise FrontmatterError(f"línea {index + 1} inválida en el frontmatter: {line!r}")
        meta[key.strip()] = value.strip()
    raise FrontmatterError("el frontmatter no cierra con ---")


def dump(meta: Dict[str, str], body: str) -> str:
    for key, value in meta.items():
        if "\n" in value:
            raise FrontmatterError(f"el valor de {key!r} no puede tener saltos de línea")
    head = "\n".join(f"{key}: {value}".rstrip() for key, value in meta.items())
    return f"{FENCE}\n{head}\n{FENCE}\n\n{body}"


def as_list(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]
