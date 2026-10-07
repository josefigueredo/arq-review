"""contract/minimum-input.md: required input IDs per level (spec §6.3)."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from arqlib.paths import CONTRACT

NIVELES: Tuple[str, ...] = ("simple", "complejo")
_ITEM = re.compile(r"^- `(\w+)` — ")


class InputsError(ValueError):
    pass


def _sections() -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current = None
    for line in (CONTRACT / "minimum-input.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None and _ITEM.match(line):
            sections[current].append(_ITEM.match(line).group(1))
    return sections


def input_ids(nivel: str) -> List[str]:
    if nivel not in NIVELES:
        raise InputsError(f"nivel desconocido {nivel!r}: usar {', '.join(NIVELES)}")
    sections = _sections()
    return sections["simple"] + (sections["complejo"] if nivel == "complejo" else [])


def all_ids() -> List[str]:
    return input_ids("complejo")
