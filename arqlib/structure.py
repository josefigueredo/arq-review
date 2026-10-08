"""Jira shape per level (spec §8). Pure: builds the plan, never talks to Jira."""
from __future__ import annotations

import hashlib
from typing import Dict, List, Sequence, Tuple

from arqlib.review import check_pry
from arqlib.summary import md_to_wiki, render_epic

COORD, TEC = "track:coordinacion", "track:tecnica"

SIMPLE_SUBTASKS: Tuple[Tuple[str, str, str], ...] = (
    ("triage", "Triage y apertura", COORD),
    ("gap-check", "Gap check de input mínimo", TEC),
    ("analisis", "Análisis y opciones", TEC),
    ("firma", "Revisión y firma", TEC),
    ("publicar", "Publicar devolución", COORD),
)

COMPLEX_STORIES: Tuple[Tuple[str, str, Tuple[str, ...], Tuple[Tuple[str, str, str], ...]], ...] = (
    ("intake", "Intake y triage", (COORD,), (
        ("normalizar", "Normalizar pedido", COORD),
        ("triage", "Triage", COORD),
        ("abrir-ticket", "Abrir ticket del requirente y plazo", COORD),
    )),
    ("analisis", "Análisis y opciones", (TEC,), (
        ("gap-check", "Gap check de input mínimo", TEC),
        ("constraints", "Análisis vs constraints", TEC),
        ("opciones", "Opciones y recomendación", TEC),
    )),
    ("validacion", "Validación técnica", (TEC,), (
        ("prueba", "Prueba acotada", TEC),
    )),
    ("decision", "Decisión y comunicación", (COORD, TEC), (
        ("firma", "Revisión y firma", TEC),
        ("publicar", "Publicar devolución", COORD),
    )),
)


# What each issue asks for: (por qué, qué, cómo, terminado cuando), in Markdown; describe() fills the review's values
# ({pry}, {nombre}, {contacto}, {head_flag}) and converts it to Jira wiki. Unknown values are named, never "...".
_TRIAGE = ("El nivel decide la estructura de Jira, el input mínimo y quién firma.",
           "Contestar las 6 preguntas de triage con evidencia del pedido; ante la duda, sí.",
           "arq-manager propone cada respuesta citando el pedido y la persona que coordina la confirma; después "
           "`arq triage {pry} --answers <respuestas confirmadas>` (preguntas en contract/triage.md).",
           "El review tiene `nivel` y el estado es `triado`.")
_GAP = ("Sin el input mínimo no hay análisis posible: se analizaría prosa.",
        "Contrastar el pedido y su documentación vigente con cada input del nivel (contract/minimum-input.md).",
        "arq-architect anota lo que falta con `arq set {pry} faltantes=<ids que falten>`; si falta algo, redacta "
        "reviews/{pry}.jsm.md y arq-manager lo publica con "
        "`arq jsm {pry} --file reviews/{pry}.jsm.md --public --template jsm-pedido-info.md --apply`.",
        "`faltantes` vacío (estado `en-analisis`), o el pedido de información publicado y el estado en `esperando-info`.")
_ANALISIS = ("La devolución tiene que citar reglas, no opiniones, y mejorar lo que el requirente propuso.",
             "Evaluar cada componente contra contract/constraints.md, original + 2 opciones para el componente más "
             "débil, recomendación, condiciones verificables y señales para Cloud, Seguridad y FinOps.",
             "arq-architect completa las secciones de contract/templates/analisis.md en reviews/{pry}.md y registra el "
             "resultado con `arq set {pry} componente_debil=<componente> senales=<sectores> veredicto=<veredicto>`.",
             "El review tiene veredicto propuesto, cada afirmación con su etiqueta de evidencia, y el estado es "
             "`en-firma`.")
_FIRMA = ("Una persona responde por el veredicto: simple → track técnico, complejo → Sr Expert.",
          "Revisar reviews/{pry}.md y firmar, o devolverlo a análisis.",
          "Quien firma lo registra con `arq set {pry} firmante=<usuario>` y `arq state {pry} --to publicado`; si pide "
          "cambios, `arq state {pry} --to en-analisis` anula la firma.",
          "El estado es `publicado` con firmante.")
_PUBLICAR = ("El requirente necesita la devolución en su ticket y la plataforma PRY necesita la decisión.",
             "Publicar la devolución, crear el seguimiento de las condiciones y pegar el comentario en la plataforma.",
             "arq-manager publica con `arq jsm {pry} --file reviews/{pry}.jsm.md --public --template "
             "jsm-devolucion.md --apply` y, si hay condiciones, `arq seguimiento {pry} <condición> --apply`; una persona "
             "hace click en Aprobar o Rechazar en la plataforma y se cierra con "
             "`arq state {pry} --to cerrado --resultado <aprobado|condicionado|rechazado>`.",
             "La devolución está en el ticket del requirente, la plataforma PRY tiene la decisión y el estado es "
             "`cerrado`.")
DOCS = {
    "revision": ("Un pedido simple se revisa en una sola tarea con sus pasos como sub-tasks.",
                 "Llevar el pedido desde el triage hasta la devolución publicada.",
                 "Con las skills arq-manager y arq-architect, parado en el repo de reviews; `arq ver {pry}` muestra "
                 "el avance.",
                 "Todas las sub-tasks hechas y el review en estado `cerrado`."),
    "revision/triage": ("Hay que abrir los canales y arrancar el plazo antes de pedir nada.",
                        "Triage, épica y ticket del requirente, y plazo de respuesta.",
                        "arq-manager tria el pedido (`arq triage {pry} --answers <respuestas confirmadas>`), una persona "
                        "crea la épica y el ticket (`arq jira {pry} --apply`) y se arranca el plazo "
                        "(`arq timebox {pry}`).",
                        "Épica y ticket creados (`jsm_listo: si`) y `vence` fijado."),
    "revision/gap-check": _GAP, "revision/analisis": _ANALISIS, "revision/firma": _FIRMA,
    "revision/publicar": _PUBLICAR,
    "intake": ("El pedido tiene que quedar registrado, clasificado y con su canal abierto antes de analizarlo.",
               "Normalizar, triar y abrir el ticket del requirente con su plazo.",
               "Con la skill arq-manager; `arq ver {pry}` muestra el avance.", "Las tres sub-tasks hechas."),
    "intake/normalizar": ("El pedido original es evidencia: no se resume ni se corrige.",
                          "Transcribir el pedido textual de la plataforma PRY, con contacto y head.",
                          "arq-manager transcribe el pedido sin resumirlo y lo registra con "
                          "`arq new {pry} --nombre \"{nombre}\" --pedido <archivo con el pedido> --contacto "
                          "{contacto}{head_flag}`.",
                          "Existe reviews/{pry}.md en estado `recibido`."),
    "intake/triage": _TRIAGE,
    "intake/abrir-ticket": ("El requirente conversa en su ticket; sin plazo, el pedido queda abierto para siempre.",
                            "Crear la épica y el ticket del requirente a su nombre, y arrancar el plazo.",
                            "Una persona corre `arq jira {pry} --apply` y arq-manager arranca el plazo con "
                            "`arq timebox {pry}`.",
                            "`jsm_listo: si` y `vence` fijado en el review."),
    "analisis": ("La revisión técnica es el corazón de la devolución.",
                 "Gap check, evaluación contra constraints y opciones con recomendación.",
                 "Con la skill arq-architect.", "Las tres sub-tasks hechas y el review en `en-firma`."),
    "analisis/gap-check": _GAP,
    "analisis/constraints": ("Cada hallazgo tiene que poder citarse como regla publicada.",
                             "Evaluar cada componente (computo, datos, identidad, red, aprovisionamiento, operacion, "
                             "costo) contra contract/constraints.md: ok, débil o bloqueante.",
                             "arq-architect completa la tabla de evaluación en reviews/{pry}.md, con una etiqueta de "
                             "evidencia en cada hallazgo.",
                             "Cada componente tiene estado y cada hallazgo cita su constraint o su evidencia."),
    "analisis/opciones": _ANALISIS,
    "validacion": ("Hay afirmaciones que el análisis no puede sostener sin probarlas.",
                   "Validar con una prueba acotada lo que el análisis no puede afirmar.",
                   "Definir el alcance y la fecha de fin de la prueba antes de empezar.",
                   "La prueba dio un resultado que el análisis cita como evidencia."),
    "validacion/prueba": ("Una prueba sin alcance ni fin se convierte en un proyecto.",
                          "Ejecutar la prueba técnica definida en el análisis.",
                          "Dejar el resultado en reviews/{pry}.md como evidencia que resuelve un `[verificar]`.",
                          "El resultado está registrado en el review."),
    "decision": ("La decisión se firma y se comunica, en ese orden.",
                 "Firma de una persona y publicación de la devolución.",
                 "Con las skills arq-manager y arq-architect.", "Las dos sub-tasks hechas y el review `cerrado`."),
    "decision/firma": _FIRMA,
    "decision/publicar": _PUBLICAR,
}
FOOTER = "Generado por arq desde reviews/{pry}.md. Esta descripción se regenera: para notas, usar comentarios."


def _fill(text: str, meta: Dict[str, str]) -> str:
    head = meta.get("head", "")
    values = {"{pry}": meta.get("pry", ""), "{nombre}": meta.get("nombre", "") or "<nombre del pedido>",
              "{contacto}": meta.get("contacto", "") or "<email del contacto>",
              "{head_flag}": f" --head {head}" if head else ""}
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    return text


def describe(node: str, meta: Dict[str, str]) -> str:
    por_que, que, como, terminado = DOCS[node]
    markdown = (f"Por qué: {por_que}\n\nQué: {que}\n\nCómo: {como}\n\nTerminado cuando: {terminado}\n\n"
                f"_{FOOTER}_")
    return md_to_wiki(_fill(markdown, meta))


class StructureError(ValueError):
    pass


def pry_label(pry: str) -> str:
    return "pry:" + check_pry(pry)[len("PRY-"):]


def _node(node: str, summary: str, labels: List[str], description: str) -> Dict[str, object]:
    """`node` is the issue's stable identity: texts may change in code or by hand in Jira, the id never does."""
    return {"node": node, "summary": summary, "labels": labels, "description": description}


def _subtasks(parent: str, base: List[str], specs: Sequence[Tuple[str, str, str]],
              meta: Dict[str, str]) -> List[Dict[str, object]]:
    return [_node(f"{parent}/{slug}", summary, base + [track], describe(f"{parent}/{slug}", meta))
            for slug, summary, track in specs]


def base_labels(meta: Dict[str, str]) -> List[str]:
    nivel = meta.get("nivel", "")
    if nivel not in ("simple", "complejo"):
        raise StructureError("el pedido no tiene nivel: correr `arq triage` primero")
    return [pry_label(meta.get("pry", "")), f"nivel:{nivel}"]


def build_plan(meta: Dict[str, str], validacion: bool = False, review_body: str = "") -> dict:
    """The epic's description is the review's summary (summary.render_epic); every other issue says what to do."""
    base = base_labels(meta)
    pry = meta["pry"]
    epic = _node("epica", f"[{pry}] {meta.get('nombre', '')}".strip(), list(base), render_epic(meta, review_body))
    if meta["nivel"] == "simple":
        task = _node("revision", f"Revisión {pry}", base + [COORD, TEC], describe("revision", meta))
        task.update(type="task", subtasks=_subtasks("revision", base, SIMPLE_SUBTASKS, meta))
        return {"epic": epic, "items": [task]}
    items = []
    for slug, summary, tracks, subtasks in COMPLEX_STORIES:
        if slug == "validacion" and not validacion:
            continue
        story = _node(slug, summary, base + list(tracks), describe(slug, meta))
        story.update(type="story", subtasks=_subtasks(slug, base, subtasks, meta))
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
        subtasks.append(_node(f"condicion/{digest}", summary, base + [COORD], md_to_wiki(
            f"Por qué: el veredicto aprobó {meta['pry']} con esta condición.\n\nQué: {text}\n\n"
            f"Cómo: el requirente la cumple y lo informa en su ticket; Arquitectura lo verifica.\n\n"
            f"Terminado cuando: hay evidencia de que la condición se cumple.\n\n_" + FOOTER.replace("{pry}", meta["pry"]) + "_")))
    return {"parent_node": "revision" if simple else "decision", "parent_summary": parent, "subtasks": subtasks}
