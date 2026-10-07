"""Review lifecycle (spec §5.1). The frontmatter `estado` field is the only source of the current state."""
from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

STATES: Tuple[str, ...] = ("recibido", "triado", "esperando-info", "en-analisis", "en-firma", "publicado",
                           "propuesta-rechazo", "cerrado")
RESULTADOS: Tuple[str, ...] = ("aprobado", "condicionado", "rechazado")
RESULTADO_POR_VEREDICTO: Dict[str, str] = {"aprobar": "aprobado", "aprobar-con-condiciones": "condicionado",
                                           "rechazar": "rechazado"}

TRANSITIONS: Dict[str, FrozenSet[str]] = {
    "recibido": frozenset({"triado"}),
    "triado": frozenset({"esperando-info", "en-analisis"}),
    "esperando-info": frozenset({"en-analisis", "propuesta-rechazo"}),
    "en-analisis": frozenset({"esperando-info", "en-firma"}),
    "en-firma": frozenset({"en-analisis", "publicado"}),
    "publicado": frozenset({"cerrado"}),
    "propuesta-rechazo": frozenset({"cerrado"}),
    "cerrado": frozenset(),
}


class StateError(ValueError):
    pass


def transition(meta: Dict[str, str], to: str, resultado: str = "") -> Dict[str, str]:
    current = meta.get("estado", "")
    if current not in TRANSITIONS:
        raise StateError(f"estado actual desconocido: {current!r}")
    if to == current and not resultado:
        return dict(meta)  # re-running a step is safe: asking for the current state changes nothing
    allowed = TRANSITIONS[current]
    if to not in allowed:
        valid = ", ".join(sorted(allowed)) or "ninguna (estado final)"
        raise StateError(f"transición inválida: {current} → {to}; válidas: {valid}")
    if to == "en-firma":
        if not meta.get("veredicto", "").strip():
            raise StateError("no se pasa a firma sin veredicto propuesto: `arq set PRY veredicto=...`")
        if meta.get("faltantes", "").strip():
            raise StateError("no se pasa a firma con input faltante")
    if to == "publicado" and not meta.get("firmante", "").strip():
        raise StateError("no se puede publicar sin firmante: una persona tiene que firmar la revisión")
    new = dict(meta)
    new["estado"] = to
    if to == "cerrado":
        if resultado not in RESULTADOS:
            raise StateError(f"resultado inválido {resultado!r}; válidos: {', '.join(RESULTADOS)}")
        if current == "propuesta-rechazo" and resultado != "rechazado":
            raise StateError("una propuesta de rechazo solo puede cerrarse como rechazado")
        expected = RESULTADO_POR_VEREDICTO.get(meta.get("veredicto", ""))
        if current == "publicado" and resultado != expected:
            raise StateError(f"el veredicto {meta.get('veredicto', '')!r} se cierra como {expected!r}, "
                             f"no como {resultado!r}")
        new["resultado"] = resultado
    elif resultado:
        raise StateError("el resultado se fija solo al cerrar")
    return new
