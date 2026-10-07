"""contract/constraints.md: parse and lint (spec §6.1)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

SEVERITIES: Tuple[str, ...] = ("bloqueante", "condicionante", "recomendación")
FIELDS: Dict[str, str] = {"Regla": "regla", "Severidad": "severidad", "Por qué": "por_que",
                          "Cómo verificar": "como_verificar", "Excepción": "excepcion"}
_HEADING = re.compile(r"^### (C-[A-Z]+-\d{2}) · (.+)$")
_FIELD = re.compile(r"^- \*\*(.+?):\*\* (.*)$")


@dataclass
class Constraint:
    id: str
    titulo: str
    regla: str = ""
    severidad: str = ""
    por_que: str = ""
    como_verificar: str = ""
    excepcion: str = ""


def _scan(text: str) -> Tuple[List[Constraint], List[str]]:
    found: List[Constraint] = []
    errors: List[str] = []
    current = None
    for line in text.splitlines():
        if line.startswith("### "):
            match = _HEADING.match(line.strip())
            if not match:
                errors.append(f"encabezado inválido: {line.strip()!r} (usar ### C-AREA-NN · título)")
                current = None
                continue
            current = Constraint(id=match.group(1), titulo=match.group(2).strip())
            found.append(current)
            continue
        field = _FIELD.match(line.strip())
        if current is not None and field and field.group(1) in FIELDS:
            setattr(current, FIELDS[field.group(1)], field.group(2).strip())
    return found, errors


def parse(text: str) -> List[Constraint]:
    return _scan(text)[0]


def lint(text: str) -> List[str]:
    found, errors = _scan(text)
    if not found and not errors:
        return ["no hay constraints"]
    seen = set()
    for c in found:
        if c.id in seen:
            errors.append(f"{c.id}: ID duplicado")
        seen.add(c.id)
        for label, attr in FIELDS.items():
            if not getattr(c, attr):
                errors.append(f"{c.id}: falta el campo {label}")
        if c.severidad and c.severidad not in SEVERITIES:
            errors.append(f"{c.id}: severidad inválida {c.severidad!r} ({', '.join(SEVERITIES)})")
    return errors
