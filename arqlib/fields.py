"""Frontmatter fields the architect writes, validated against the contract (spec §7)."""
from __future__ import annotations

from typing import Dict, List, Tuple

from arqlib.frontmatter import as_list
from arqlib.inputs import input_ids

COMPONENTES: Tuple[str, ...] = ("computo", "datos", "identidad", "red", "aprovisionamiento", "operacion", "costo")
SENALES: Tuple[str, ...] = ("cloud", "seguridad", "finops")
VEREDICTOS: Tuple[str, ...] = ("aprobar", "aprobar-con-condiciones", "rechazar")
EDITABLE: Tuple[str, ...] = ("faltantes", "componente_debil", "senales", "veredicto", "firmante")


class FieldsError(ValueError):
    pass


def parse_updates(pairs: List[str]) -> Dict[str, str]:
    updates: Dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip():
            raise FieldsError(f"actualización inválida {pair!r}: usar campo=valor")
        updates[key.strip()] = value.strip()
    return updates


def _check_list(name: str, values: List[str], allowed: Tuple[str, ...]) -> str:
    unknown = [v for v in values if v not in allowed]
    if unknown:
        raise FieldsError(f"{name} desconocidos: {', '.join(unknown)}; válidos: {', '.join(allowed)}")
    return ", ".join(values)


def apply_updates(meta: Dict[str, str], updates: Dict[str, str]) -> Dict[str, str]:
    new = dict(meta)
    for key, value in updates.items():
        if key not in EDITABLE:
            hint = " (usar arq state)" if key == "estado" else ""
            raise FieldsError(f"el campo {key!r} no se edita con set{hint}; editables: {', '.join(EDITABLE)}")
        if key == "faltantes":
            if meta.get("nivel") not in ("simple", "complejo"):
                raise FieldsError("el pedido no tiene nivel: correr `arq triage` primero")
            value = _check_list("inputs", as_list(value), tuple(input_ids(meta["nivel"])))
        elif key == "senales":
            value = _check_list("señales", as_list(value), SENALES)
        elif key == "componente_debil" and value:
            _check_list("componentes", [value], COMPONENTES)
        elif key == "veredicto" and value:
            _check_list("veredictos", [value], VEREDICTOS)
        new[key] = value
    if new.get("veredicto") and as_list(new.get("faltantes", "")):
        raise FieldsError("no se emite veredicto con input faltante: primero pedir la información por JSM")
    return new
