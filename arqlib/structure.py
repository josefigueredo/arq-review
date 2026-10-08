"""Jira shape per level (spec §8). Pure: builds the plan, never talks to Jira."""
from __future__ import annotations

import hashlib
from typing import Dict, List, Sequence, Tuple

from arqlib.review import check_pry

COORD, TEC = "track:coordinacion", "track:tecnica"

SIMPLE_SUBTASKS: Tuple[Tuple[str, str, str, str], ...] = (
    ("triage", "Triage y apertura", COORD, "Contestar el triage, abrir la épica y el ticket del requirente, arrancar el plazo."),
    ("gap-check", "Gap check de input mínimo", TEC, "Contrastar el pedido con el input mínimo del nivel y pedir lo que falte."),
    ("analisis", "Análisis y opciones", TEC, "Evaluar contra las constraints y proponer opciones para el componente más débil."),
    ("firma", "Revisión y firma", TEC, "Revisar el análisis y firmarlo."),
    ("publicar", "Publicar devolución", COORD, "Responder en el ticket del requirente y dejar el comentario en la plataforma PRY."),
)

COMPLEX_STORIES: Tuple[Tuple[str, str, Tuple[str, ...], str, Tuple[Tuple[str, str, str, str], ...]], ...] = (
    ("intake", "Intake y triage", (COORD,), "Dejar el pedido normalizado, triado y con canales abiertos.", (
        ("normalizar", "Normalizar pedido", COORD, "Pasar el pedido a reviews/PRY-XXXX.md."),
        ("triage", "Triage", COORD, "Contestar las preguntas de triage."),
        ("abrir-ticket", "Abrir ticket del requirente y plazo", COORD, "Crear el ticket del requirente y arrancar el plazo."),
    )),
    ("analisis", "Análisis y opciones", (TEC,), "Producir el análisis con opciones y recomendación.", (
        ("gap-check", "Gap check de input mínimo", TEC, "Contrastar con el input mínimo del nivel complejo."),
        ("constraints", "Análisis vs constraints", TEC, "Evaluar cada componente contra las constraints."),
        ("opciones", "Opciones y recomendación", TEC, "Original y dos opciones, recomendación y condiciones."),
    )),
    ("validacion", "Validación técnica", (TEC,), "Opcional: validar con una prueba acotada lo que el análisis no puede afirmar.", (
        ("prueba", "Prueba acotada", TEC, "Prueba técnica con alcance y fecha de fin definidos."),
    )),
    ("decision", "Decisión y comunicación", (COORD, TEC), "Firmar y comunicar la decisión.", (
        ("firma", "Revisión y firma", TEC, "Revisar el análisis y firmarlo."),
        ("publicar", "Publicar devolución", COORD, "Responder en el ticket del requirente, comentar en la plataforma PRY y escalar a RFC si corresponde."),
    )),
)


class StructureError(ValueError):
    pass


def pry_label(pry: str) -> str:
    return "pry:" + check_pry(pry)[len("PRY-"):]


def _node(node: str, summary: str, labels: List[str], description: str) -> Dict[str, object]:
    """`node` is the issue's stable identity: texts may change in code or by hand in Jira, the id never does."""
    return {"node": node, "summary": summary, "labels": labels, "description": description}


def _subtasks(parent: str, base: List[str], specs: Sequence[Tuple[str, str, str, str]]) -> List[Dict[str, object]]:
    return [_node(f"{parent}/{slug}", summary, base + [track], description)
            for slug, summary, track, description in specs]


def base_labels(meta: Dict[str, str]) -> List[str]:
    nivel = meta.get("nivel", "")
    if nivel not in ("simple", "complejo"):
        raise StructureError("el pedido no tiene nivel: correr `arq triage` primero")
    return [pry_label(meta.get("pry", "")), f"nivel:{nivel}"]


def build_plan(meta: Dict[str, str], validacion: bool = False) -> dict:
    base = base_labels(meta)
    pry = meta["pry"]
    epic = _node("epica", f"[{pry}] {meta.get('nombre', '')}".strip(), list(base),
                 f"Revisión de Arquitectura del pedido {pry}. Fuente de verdad: reviews/{pry}.md en el repo de reviews.")
    if meta["nivel"] == "simple":
        task = _node("revision", f"Revisión {pry}", base + [COORD, TEC], "Revisión de nivel simple.")
        task.update(type="task", subtasks=_subtasks("revision", base, SIMPLE_SUBTASKS))
        return {"epic": epic, "items": [task]}
    items = []
    for slug, summary, tracks, description, subtasks in COMPLEX_STORIES:
        if slug == "validacion" and not validacion:
            continue
        story = _node(slug, summary, base + list(tracks), description)
        story.update(type="story", subtasks=_subtasks(slug, base, subtasks))
        items.append(story)
    return {"epic": epic, "items": items}


def followup_plan(meta: Dict[str, str], condiciones: List[str]) -> dict:
    base = base_labels(meta)
    texts = [" ".join(c.split()) for c in condiciones if c.strip()]
    if not texts:
        raise StructureError("hace falta al menos una condición")
    simple = meta["nivel"] == "simple"
    parent = f"Revisión {meta['pry']}" if simple else "Decisión y comunicación"
    subtasks = []
    for text in texts:
        summary = f"Condición: {text}"
        if len(summary) > 240:
            summary = summary[:237].rstrip() + "..."
        digest = hashlib.sha1(text.lower().encode("utf-8")).hexdigest()[:10]
        subtasks.append(_node(f"condicion/{digest}", summary, base + [COORD],
                              f"Condición de la aprobación, a verificar: {text}"))
    return {"parent_node": "revision" if simple else "decision", "parent_summary": parent, "subtasks": subtasks}
