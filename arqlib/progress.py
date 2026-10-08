"""Which issues are finished and which one is under way, derived from the review (spec D16). Pure: never talks to Jira.

The rules mirror each task's "Terminado cuando". arq only ever moves issues forward: what a person closed by hand
stays closed, and nothing is reopened.
"""
from __future__ import annotations

from typing import Dict, Set

ORDER = ("recibido", "triado", "esperando-info", "en-analisis", "en-firma", "publicado", "cerrado")
RANK = {estado: i for i, estado in enumerate(ORDER)}


def _rank(meta: Dict[str, str]) -> int:
    estado = meta.get("estado", "")
    if estado == "propuesta-rechazo" or (estado == "cerrado" and not meta.get("veredicto")):
        return RANK["esperando-info"]  # closed for missing information: no analysis happened
    return RANK.get(estado, 0)


def done_nodes(meta: Dict[str, str], plan: dict, info_published: bool) -> Set[str]:
    r = _rank(meta)
    closed = meta.get("estado") == "cerrado"
    ticket = meta.get("jsm_listo") == "si" and bool(meta.get("vence"))
    gap = r >= RANK["en-analisis"] or (r >= RANK["esperando-info"] and info_published)
    leaves = {
        "intake/normalizar": True,
        "intake/triage": r >= RANK["triado"],
        "intake/abrir-ticket": ticket,
        "revision/triage": r >= RANK["triado"] and ticket,
        "analisis/gap-check": gap, "revision/gap-check": gap,
        "analisis/constraints": r >= RANK["en-firma"], "analisis/opciones": r >= RANK["en-firma"],
        "revision/analisis": r >= RANK["en-firma"],
        "decision/firma": r >= RANK["publicado"], "revision/firma": r >= RANK["publicado"],
        "decision/publicar": closed, "revision/publicar": closed,
    }
    present = {sub["node"] for item in plan["items"] for sub in item["subtasks"]}
    done = {node for node, finished in leaves.items() if finished and node in present}
    for item in plan["items"]:
        children = [sub["node"] for sub in item["subtasks"]]
        if children and all(child in done for child in children):
            done.add(item["node"])
    if closed:
        done.add("epica")
    return done


def active_nodes(meta: Dict[str, str], plan: dict, done: Set[str]) -> Set[str]:
    """The first unfinished task in execution order, its story and the epic: what goes to "en curso".

    The optional technical validation is skipped: nothing in the review marks it finished, so it would hold the flow.
    """
    if meta.get("estado") == "cerrado":
        return set()
    for item in plan["items"]:
        if item["node"] == "validacion":
            continue
        for sub in item["subtasks"]:
            if sub["node"] not in done:
                return {sub["node"], item["node"], "epica"}
    return set()
