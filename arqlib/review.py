"""reviews/PRY-XXXX.md in the team repo: the frontmatter is the review's state (spec §5.1)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple

from arqlib import frontmatter

FIELDS: Tuple[str, ...] = ("pry", "nombre", "contacto", "head", "estado", "nivel", "epica", "jsm", "jsm_listo",
                           "vence", "firmante", "resultado", "faltantes", "componente_debil", "senales", "veredicto")
_PRY = re.compile(r"PRY-\d{4}-\d{4}")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class ReviewError(ValueError):
    pass


def check_pry(pry: str) -> str:
    if not _PRY.fullmatch(pry or ""):
        raise ReviewError(f"PRY inválido {pry!r}: usar PRY-AAAA-NNNN")
    return pry


def check_email(email: str) -> str:
    if not _EMAIL.fullmatch(email or ""):
        raise ReviewError(f"email inválido {email!r}")
    return email


def review_path(repo: Path, pry: str) -> Path:
    return repo / "reviews" / f"{check_pry(pry)}.md"


def new_review(repo: Path, pry: str, nombre: str, pedido: str, contacto: str, head: str = "") -> Path:
    path = review_path(repo, pry)
    check_email(contacto)
    if head:
        check_email(head)
    if path.exists():
        raise ReviewError(f"{path} ya existe: usar `arq show {pry}`")
    meta = {field: "" for field in FIELDS}
    meta.update(pry=pry, nombre=" ".join(nombre.split()), contacto=contacto, head=head, estado="recibido")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dump(meta, f"## Pedido original\n\n{pedido.strip()}\n"), encoding="utf-8")
    return path


def load(repo: Path, pry: str) -> Tuple[Dict[str, str], str]:
    path = review_path(repo, pry)
    if not path.exists():
        raise ReviewError(f"no existe {path}: correr `arq new {pry}` primero")
    return frontmatter.parse(path.read_text(encoding="utf-8"))


def save(repo: Path, pry: str, meta: Dict[str, str], body: str) -> None:
    review_path(repo, pry).write_text(frontmatter.dump(meta, body), encoding="utf-8")
