"""The review epic's description, generated from reviews/PRY-XXXX.md (spec D2: git is the source, Jira a mirror).

Jira's v2 API takes descriptions in wiki markup, so the review's Markdown is converted: headings, lists, tables,
bold and inline code. Brackets and braces are escaped because wiki markup reads `[x]` as a link and `{x}` as a macro.
"""
from __future__ import annotations

import re
from typing import Dict, List

MAX_DESCRIPTION = 30000  # Jira rejects descriptions over 32767 characters
# Review sections shown in the epic, in this order; the requester's original text goes last.
SECTIONS = ("Lo que entendimos", "Input faltante", "Análisis preliminar (sin veredicto)", "Evaluación por componente",
            "Opciones consideradas", "Decisión", "Recomendación", "Condiciones", "Consecuencias",
            "Señales para otros sectores (sin veredicto)", "Veredicto propuesto", "Pedido original")


def _inline(text: str) -> str:
    text = re.sub(r"`(\[[^`\]]+\])`", r"\1", text)  # evidence tags like `[C-PLAT-01]` read as plain text
    text = re.sub(r"([\[\]{}])", r"\\\1", text)
    text = re.sub(r"`([^`]+)`", r"{{\1}}", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)


_BLOCK = re.compile(r"^\s*(#{1,6}\s|[-*]\s|\d+\.\s|\|)")


def _unwrap(markdown: str) -> List[str]:
    """Join hard-wrapped lines: Jira renders every newline inside a paragraph as a visible break."""
    lines: List[str] = []
    for line in markdown.splitlines():
        continuation = (line.strip() and lines and lines[-1].strip() and not _BLOCK.match(line)
                        and not lines[-1].lstrip().startswith(("|", "#")))
        if continuation:
            lines[-1] = lines[-1].rstrip() + " " + line.strip()
        else:
            lines.append(line)
    return lines


def md_to_wiki(markdown: str) -> str:
    out: List[str] = []
    header_row = True
    for line in _unwrap(markdown):
        stripped = line.strip()
        if not stripped.startswith("|"):
            header_row = True
        heading = re.match(r"^(#{2,4})\s+(.*)$", stripped)
        bullet = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        numbered = re.match(r"^(\s*)\d+\.\s+(.*)$", line)
        if heading:
            out.append(f"h{len(heading.group(1)) + 1}. {_inline(heading.group(2))}")
        elif stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                continue
            sep = "||" if header_row else "|"
            out.append(f"{sep} " + f" {sep} ".join(_inline(c) for c in cells) + f" {sep}")
            header_row = False
        elif bullet:
            depth = len(bullet.group(1).expandtabs()) // 2 + 1
            out.append("*" * depth + " " + _inline(bullet.group(2)))
        elif numbered:
            depth = len(numbered.group(1).expandtabs()) // 2 + 1
            out.append("#" * depth + " " + _inline(numbered.group(2)))
        else:
            out.append(_inline(line))
    return "\n".join(out)


def _sections(body: str) -> Dict[str, str]:
    found: Dict[str, str] = {}
    for chunk in re.split(r"(?m)^## ", body):
        title, _, content = chunk.partition("\n")
        if title.strip() in SECTIONS:
            found[title.strip()] = content.strip()
    return found


def render_epic(meta: Dict[str, str], body: str) -> str:
    pry = meta.get("pry", "")
    dash = lambda key: meta.get(key) or "—"  # noqa: E731
    verdict = meta.get("veredicto") or "— (sin veredicto)"
    head = [
        f"h3. Revisión de Arquitectura · {pry} · {meta.get('nombre', '')}",
        f"*Estado:* {dash('estado')} · *Nivel:* {dash('nivel')} · *Vence:* {dash('vence')} · "
        f"*Firmante:* {dash('firmante')} · *Veredicto:* {verdict}",
        f"*Ticket del requirente:* {dash('jsm')} · *Input faltante:* {meta.get('faltantes') or 'ninguno'}",
        f"*Componente más débil:* {dash('componente_debil')} · *Señales:* {meta.get('senales') or 'ninguna'}",
    ]
    footer = (f"----\n_Generado por arq desde reviews/{pry}.md, la fuente de verdad. Esta descripción se regenera "
              f"en cada `arq jira {pry} --apply`: para notas, usar comentarios._").replace("`", "")
    sections = _sections(body)
    parts = [md_to_wiki(f"## {title}\n\n{sections[title]}") for title in SECTIONS if title in sections]
    text = "\n".join(head) + ("\n\n" + "\n\n".join(parts) if parts else "") + "\n\n" + footer
    if len(text) <= MAX_DESCRIPTION:
        return text
    cut = f"\n\n_(recortado: el análisis completo está en reviews/{pry}.md)_\n\n{footer}"
    return text[:MAX_DESCRIPTION - len(cut)] + cut
