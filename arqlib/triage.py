"""Deterministic triage (spec §6.2): one "yes" makes a request `complejo`."""
from __future__ import annotations

from typing import Dict, Tuple

QUESTIONS: Tuple[Tuple[str, str], ...] = (
    ("multi_cuenta", "¿Toca más de una cuenta, empresa o vertical?"),
    ("migracion", "¿Es una migración o mueve datos existentes?"),
    ("fecha_comprometida", "¿La fecha es comprometida (no negociable)?"),
    ("otros_equipos", "¿Involucra a otros equipos además del que pide?"),
    ("datos_sensibles_o_ia", "¿Incluye datos de clientes o personales, o servicios de IA externos?"),
    ("larga_o_productiva", "¿Dura más de 3 meses o queda productivo?"),
)
_YES = {"si", "sí", "s", "yes", "y"}
_NO = {"no", "n"}


class TriageError(ValueError):
    pass


def parse_answers(text: str) -> Dict[str, bool]:
    answers: Dict[str, bool] = {}
    for part in text.split(","):
        if not part.strip():
            continue
        key, sep, value = part.partition("=")
        value = value.strip().lower()
        if not sep or value not in _YES | _NO:
            raise TriageError(f"respuesta inválida {part.strip()!r}: contestar si o no (id=si o id=no)")
        answers[key.strip()] = value in _YES
    return answers


def classify(answers: Dict[str, bool]) -> str:
    ids = [qid for qid, _ in QUESTIONS]
    missing = [qid for qid in ids if qid not in answers]
    unknown = sorted(set(answers) - set(ids))
    if missing:
        raise TriageError(f"faltan respuestas: {', '.join(missing)}")
    if unknown:
        raise TriageError(f"preguntas desconocidas: {', '.join(unknown)}")
    return "complejo" if any(answers.values()) else "simple"
