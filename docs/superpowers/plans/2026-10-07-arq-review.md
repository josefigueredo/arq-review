# arq-review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir `arq-review`: un CLI `arq` (stdlib) + contrato + dos skills (`arq-manager`, `arq-architect`) que llevan
un pedido `PRY-YYYY-NNNN` desde el intake hasta la devolución de Arquitectura, con épica en Jira, conversación en JSM y
análisis versionado en git.

**Architecture:** Núcleo determinístico en `arqlib/` (frontmatter, estados, triage, constraints, plazo, reviews,
estructura Jira, cliente Jira/JSM, preview, evaluación) expuesto por `arq.py`. Las skills aportan el juicio y llaman al
CLI. El estado de cada PRY vive en el frontmatter de `reviews/PRY-XXXX.md` dentro del repo de reviews del equipo (cwd).
Toda escritura en Jira es dry run por defecto; `--apply` lo corre el usuario.

**Tech Stack:** Python ≥ 3.9, solo stdlib (`argparse`, `urllib`, `json`, `re`, `dataclasses`, `datetime`, `html`),
`unittest`. Bash para `install.sh`.

**Spec:** `docs/superpowers/specs/2026-10-07-arq-review-design.md`

## Global Constraints

- Python ≥ 3.9: `from __future__ import annotations` en cada módulo; `typing.Dict/List/Optional/Tuple`, nunca `X | Y`
  en runtime ni `match`.
- Solo stdlib. Ninguna dependencia externa. Los tests nunca salen a la red (Jira falso u `opener` falso).
- Suite: `python3 -m unittest discover -s tests -v` y también `/usr/bin/python3 -m unittest discover -s tests` (3.9).
- Textos para personas en español rioplatense neutro y profesional; identificadores de código en inglés.
- Labels: `pry:YYYY-NNNN`, `nivel:simple|complejo`, `track:coordinacion|tecnica`. Nunca labels de seniority.
- Estados: `recibido, triado, esperando-info, en-analisis, en-firma, publicado, propuesta-rechazo, cerrado`;
  resultados: `aprobado, condicionado, rechazado`.
- Toda escritura en Jira/JSM: dry run por defecto, se ejecuta solo con `--apply`, queda en `.arq/jira-writes.jsonl`.
- Credenciales solo por entorno: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`.
- El agente nunca aprueba ni rechaza en la plataforma PRY.
- Commits: conventional commits, **sin** `Co-Authored-By` ni atribución de IA.
- Errores de dominio: `arq` imprime `error: <mensaje>` en stderr y sale con 1; uso inválido sale con 2. Nunca un
  traceback para un error esperado.

## Review Focus

- **PRY mal formado o con path traversal** (`PRY-2026-28`, `../../etc/passwd`): se rechaza con error claro antes de tocar
  disco o Jira. Test en Task 6.
- **Re-ejecutar `arq jira --apply` tras una falla a mitad de camino**: no duplica épica, items ni sub-tasks; crea solo lo
  que falta. Test en Task 10.
- **Plazo que cruza fines de semana o arranca un sábado**: los días hábiles saltan sábado y domingo. Test en Task 5.
- **`constraints.md` mal escrito** (ID duplicado, severidad inválida, campo faltante): `arq lint` lista errores, no
  explota. Test en Task 4.
- **Respuesta pública a JSM con placeholders, texto libre o antes de la firma**: se rechaza antes de publicar. Tests
  en Tasks 7 y 13.
- **Requirente que no existe en Jira**: no se crea ningún pedido JSM y el error dice cómo darlo de alta. Test en
  Task 10.
- **Búsqueda de Jira que todavía no ve lo recién creado**: el journal lo cubre y no se duplica. Test en Task 10.
- **Skill que pide el estado actual** (`esperando-info` → `esperando-info`): no hace nada en lugar de fallar. Test en
  Task 2.

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `arq.py` | Entrypoint: agrega la carpeta al `sys.path` y corre `arqlib.cli.main` |
| `arqlib/paths.py` | `ROOT`, `CONTRACT` |
| `arqlib/frontmatter.py` | Parse/dump de frontmatter plano `clave: valor` |
| `arqlib/state.py` | Máquina de estados |
| `arqlib/triage.py` | Preguntas sí/no → nivel |
| `arqlib/constraints.py` | Parser y lint de `constraints.md` |
| `arqlib/inputs.py` | Parser de `minimum-input.md` (IDs de input por nivel) |
| `arqlib/timebox.py` | Días hábiles y vencimiento |
| `arqlib/config.py` | `.arq/config.json` y credenciales |
| `arqlib/review.py` | Alta, lectura y guardado de `reviews/PRY-XXXX.md` |
| `arqlib/render.py` | Placeholders `{{x}}` |
| `arqlib/structure.py` | Plan de épica/items/sub-tasks por nivel (puro) |
| `arqlib/journal.py` | Journal de escrituras |
| `arqlib/jira.py` | Cliente Jira + JSM (stdlib) |
| `arqlib/apply.py` | Aplicación idempotente del plan |
| `arqlib/preview.py` | Preview HTML del plan |
| `arqlib/evaluate.py` | Evaluación de golden cases |
| `arqlib/cli.py` | Subcomandos `arq` |
| `contract/*.md`, `contract/templates/*.md` | Contrato (lo mantiene Arquitectura) |
| `skills/arq-manager/SKILL.md`, `skills/arq-architect/SKILL.md` | Skills de rol |
| `tests/helpers.py`, `tests/test_*.py`, `tests/golden/*` | Pruebas |
| `install.sh`, `README.md`, `AGENTS.md` | Instalación y documentación |

---

### Task 1: Scaffold y frontmatter

**Files:**
- Create: `arq.py`, `arqlib/__init__.py`, `arqlib/paths.py`, `arqlib/frontmatter.py`, `tests/helpers.py`,
  `tests/test_frontmatter.py`, `AGENTS.md`, `.gitignore`

**Interfaces:**
- Produces: `paths.ROOT: Path`, `paths.CONTRACT: Path`;
  `frontmatter.parse(text: str) -> Tuple[Dict[str, str], str]`, `frontmatter.dump(meta: Dict[str, str], body: str) -> str`,
  `frontmatter.as_list(value: str) -> List[str]`, `frontmatter.FrontmatterError(ValueError)`;
  `tests.helpers.make_repo() -> Path` (repo temporal vacío).

- [ ] **Step 1: Crear scaffold**

`arq.py`:
```python
#!/usr/bin/env python3
"""Entry point: puts the repo on sys.path and runs the arq CLI (works through a symlink)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from arqlib.cli import main  # noqa: E402

sys.exit(main())
```

`arqlib/__init__.py`:
```python
"""arq-review: architecture review of PRY requests."""
```

`arqlib/paths.py`:
```python
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contract"
```

`tests/helpers.py`:
```python
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def make_repo() -> Path:
    """An empty team reviews repo in a temp dir."""
    return Path(tempfile.mkdtemp(prefix="arq-test-"))
```

`.gitignore`:
```
__pycache__/
*.pyc
```

`AGENTS.md`:
```markdown
# arq-review — guía para agentes

- Python ≥ 3.9, solo stdlib. TDD. Suite: `python3 -m unittest discover -s tests -v`, también con `/usr/bin/python3`.
- Los tests nunca salen a la red.
- El contrato (`contract/`) lo mantiene Arquitectura: el código lo lee, nunca lo reescribe.
- Toda escritura en Jira/JSM es dry run salvo `--apply`, que corre el usuario.
- Commits: conventional commits, sin atribución de IA.
```

- [ ] **Step 2: Escribir el test que falla**

`tests/test_frontmatter.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib import frontmatter
from arqlib.frontmatter import FrontmatterError


class FrontmatterTest(unittest.TestCase):
    def test_roundtrip(self):
        meta = {"pry": "PRY-2026-0028", "estado": "recibido", "jsm": ""}
        text = frontmatter.dump(meta, "## Pedido original\n\nHola\n")
        self.assertEqual(frontmatter.parse(text), (meta, "## Pedido original\n\nHola\n"))

    def test_value_with_colon_keeps_everything_after_first_colon(self):
        meta, _ = frontmatter.parse("---\ndoc: https://x.y/z?a=b\n---\n\nbody")
        self.assertEqual(meta["doc"], "https://x.y/z?a=b")

    def test_missing_opening_fence(self):
        with self.assertRaisesRegex(FrontmatterError, "empezar con ---"):
            frontmatter.parse("pry: x\n---\n")

    def test_unclosed(self):
        with self.assertRaisesRegex(FrontmatterError, "no cierra"):
            frontmatter.parse("---\npry: x\n")

    def test_line_without_colon(self):
        with self.assertRaisesRegex(FrontmatterError, "línea 2"):
            frontmatter.parse("---\nsin dos puntos\n---\n")

    def test_dump_rejects_newline_in_value(self):
        with self.assertRaisesRegex(FrontmatterError, "nombre"):
            frontmatter.dump({"nombre": "a\nb"}, "")

    def test_as_list(self):
        self.assertEqual(frontmatter.as_list(" finops, seguridad ,,"), ["finops", "seguridad"])
        self.assertEqual(frontmatter.as_list(""), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `ImportError: cannot import name 'frontmatter' from 'arqlib'`

- [ ] **Step 4: Implementar**

`arqlib/frontmatter.py`:
```python
"""Flat `key: value` frontmatter. Values are single-line strings; lists are comma-separated."""
from __future__ import annotations

from typing import Dict, List, Tuple

FENCE = "---"


class FrontmatterError(ValueError):
    pass


def parse(text: str) -> Tuple[Dict[str, str], str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != FENCE:
        raise FrontmatterError("falta el frontmatter: el archivo tiene que empezar con ---")
    meta: Dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FENCE:
            return meta, "\n".join(lines[index + 1:]).lstrip("\n")
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            raise FrontmatterError(f"línea {index + 1} inválida en el frontmatter: {line!r}")
        meta[key.strip()] = value.strip()
    raise FrontmatterError("el frontmatter no cierra con ---")


def dump(meta: Dict[str, str], body: str) -> str:
    for key, value in meta.items():
        if "\n" in value:
            raise FrontmatterError(f"el valor de {key!r} no puede tener saltos de línea")
    head = "\n".join(f"{key}: {value}".rstrip() for key, value in meta.items())
    return f"{FENCE}\n{head}\n{FENCE}\n\n{body}"


def as_list(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]
```

Nota: `rstrip()` en `dump` deja `jsm:` sin espacio final cuando el valor es vacío; `parse` lo lee como `""`.

- [ ] **Step 5: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add arq.py arqlib tests AGENTS.md .gitignore
git commit -m "feat: scaffold arq CLI and flat frontmatter parser"
```

---

### Task 2: Máquina de estados

**Files:**
- Create: `arqlib/state.py`, `tests/test_state.py`

**Interfaces:**
- Produces: `state.STATES: Tuple[str, ...]`, `state.RESULTADOS: Tuple[str, ...]`,
  `state.RESULTADO_POR_VEREDICTO: Dict[str, str]`,
  `state.transition(meta: Dict[str, str], to: str, resultado: str = "") -> Dict[str, str]` (devuelve copia; pedir el
  estado actual sin resultado no hace nada), `state.StateError(ValueError)`.

Guardas: `en-firma` exige `veredicto` y `faltantes` vacío; `publicado` exige `firmante`; cerrar desde `publicado`
exige el `resultado` que corresponde al `veredicto`; cerrar desde `propuesta-rechazo` solo como `rechazado`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_state.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.state import StateError, transition


def meta(estado: str, **extra: str) -> dict:
    base = {"estado": estado, "firmante": "", "resultado": "", "veredicto": "", "faltantes": ""}
    base.update(extra)
    return base


class StateTest(unittest.TestCase):
    def test_happy_path(self):
        m = meta("recibido", veredicto="aprobar-con-condiciones")
        for to in ("triado", "esperando-info", "en-analisis", "en-firma"):
            m = transition(m, to)
        m["firmante"] = "edgardo.costilla"
        m = transition(m, "publicado")
        m = transition(m, "cerrado", resultado="condicionado")
        self.assertEqual((m["estado"], m["resultado"]), ("cerrado", "condicionado"))

    def test_same_state_is_a_no_op(self):
        for estado in ("esperando-info", "en-analisis", "triado"):
            self.assertEqual(transition(meta(estado), estado)["estado"], estado)

    def test_returns_copy(self):
        original = meta("recibido")
        transition(original, "triado")
        self.assertEqual(original["estado"], "recibido")

    def test_invalid_transition_lists_valid_ones(self):
        with self.assertRaisesRegex(StateError, r"recibido → publicado.*triado"):
            transition(meta("recibido"), "publicado")

    def test_unknown_current_state(self):
        with self.assertRaisesRegex(StateError, "desconocido"):
            transition(meta("inventado"), "triado")

    def test_en_firma_requires_verdict_and_complete_input(self):
        with self.assertRaisesRegex(StateError, "veredicto"):
            transition(meta("en-analisis"), "en-firma")
        with self.assertRaisesRegex(StateError, "input faltante"):
            transition(meta("en-analisis", veredicto="aprobar", faltantes="rollback"), "en-firma")

    def test_publicado_requires_firmante(self):
        with self.assertRaisesRegex(StateError, "firmante"):
            transition(meta("en-firma", veredicto="aprobar"), "publicado")

    def test_cerrado_requires_valid_resultado(self):
        with self.assertRaisesRegex(StateError, "resultado"):
            transition(meta("publicado", veredicto="aprobar"), "cerrado", resultado="quizas")

    def test_cerrado_resultado_must_match_verdict(self):
        with self.assertRaisesRegex(StateError, "rechazar.*rechazado"):
            transition(meta("publicado", veredicto="rechazar"), "cerrado", resultado="aprobado")
        closed = transition(meta("publicado", veredicto="rechazar"), "cerrado", resultado="rechazado")
        self.assertEqual(closed["resultado"], "rechazado")

    def test_resultado_only_when_closing(self):
        with self.assertRaisesRegex(StateError, "solo al cerrar"):
            transition(meta("recibido"), "triado", resultado="aprobado")

    def test_propuesta_rechazo_closes_only_as_rechazado(self):
        m = transition(meta("esperando-info"), "propuesta-rechazo")
        with self.assertRaisesRegex(StateError, "rechazado"):
            transition(m, "cerrado", resultado="aprobado")
        self.assertEqual(transition(m, "cerrado", resultado="rechazado")["resultado"], "rechazado")

    def test_cerrado_is_final(self):
        with self.assertRaises(StateError):
            transition(meta("cerrado"), "en-analisis")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -p "test_state.py" -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'arqlib.state'`

- [ ] **Step 3: Implementar**

`arqlib/state.py`:
```python
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
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add arqlib/state.py tests/test_state.py
git commit -m "feat: add review state machine"
```

---

### Task 3: Triage y `contract/triage.md`

**Files:**
- Create: `arqlib/triage.py`, `contract/triage.md`, `tests/test_triage.py`

**Interfaces:**
- Produces: `triage.QUESTIONS: Tuple[Tuple[str, str], ...]` (id, pregunta),
  `triage.parse_answers(text: str) -> Dict[str, bool]`, `triage.classify(answers: Dict[str, bool]) -> str`
  (`"simple"` | `"complejo"`), `triage.TriageError(ValueError)`.

- [ ] **Step 1: Escribir el contrato**

`contract/triage.md`:
```markdown
# Triage de pedidos PRY

Lo corre quien coordina (`arq-manager`). Se contesta sí o no, sin conocimiento técnico.
**Un solo "sí" → nivel `complejo`.** Todo "no" → nivel `simple`. Ante la duda, contestar "sí".

| ID | Pregunta |
|---|---|
| `multi_cuenta` | ¿Toca más de una cuenta, empresa o vertical? |
| `migracion` | ¿Es una migración o mueve datos existentes? |
| `fecha_comprometida` | ¿La fecha es comprometida (no negociable)? |
| `otros_equipos` | ¿Involucra a otros equipos además del que pide? |
| `datos_sensibles_o_ia` | ¿Incluye datos de clientes o personales, o servicios de IA externos? |
| `larga_o_productiva` | ¿Dura más de 3 meses o queda productivo? |

Uso: `arq triage PRY-2026-0028 --answers "multi_cuenta=no,migracion=no,fecha_comprometida=no,otros_equipos=no,datos_sensibles_o_ia=no,larga_o_productiva=no"`
```

- [ ] **Step 2: Escribir el test que falla**

`tests/test_triage.py`:
```python
from __future__ import annotations

import re
import unittest

import helpers  # noqa: F401
from arqlib.paths import CONTRACT
from arqlib.triage import QUESTIONS, TriageError, classify, parse_answers

ALL_NO = ",".join(f"{qid}=no" for qid, _ in QUESTIONS)


class TriageTest(unittest.TestCase):
    def test_all_no_is_simple(self):  # PRY-2026-0028
        self.assertEqual(classify(parse_answers(ALL_NO)), "simple")

    def test_one_yes_is_complejo(self):
        self.assertEqual(classify(parse_answers(ALL_NO.replace("migracion=no", "migracion=si"))), "complejo")

    def test_product_brain_case_is_complejo(self):  # PRY-2026-0026
        text = ("multi_cuenta=si,migracion=si,fecha_comprometida=si,otros_equipos=si,"
                "datos_sensibles_o_ia=si,larga_o_productiva=no")
        self.assertEqual(classify(parse_answers(text)), "complejo")

    def test_accepts_sí_with_accent_and_spaces(self):
        answers = parse_answers(ALL_NO.replace("migracion=no", " migracion = Sí "))
        self.assertTrue(answers["migracion"])

    def test_missing_question(self):
        with self.assertRaisesRegex(TriageError, "faltan.*larga_o_productiva"):
            classify(parse_answers(ALL_NO.replace(",larga_o_productiva=no", "")))

    def test_unknown_question(self):
        with self.assertRaisesRegex(TriageError, "desconocidas.*color"):
            classify(parse_answers(ALL_NO + ",color=si"))

    def test_invalid_value(self):
        with self.assertRaisesRegex(TriageError, "si o no"):
            parse_answers("migracion=quizas")

    def test_contract_lists_exactly_the_questions(self):
        text = (CONTRACT / "triage.md").read_text(encoding="utf-8")
        ids = re.findall(r"^\| `(\w+)` \|", text, flags=re.M)
        self.assertEqual(ids, [qid for qid, _ in QUESTIONS])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.triage'`

- [ ] **Step 4: Implementar**

`arqlib/triage.py`:
```python
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
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add arqlib/triage.py contract/triage.md tests/test_triage.py
git commit -m "feat: add deterministic triage with contract"
```

---

### Task 4: Constraints: parser, lint y `contract/constraints.md` inicial

**Files:**
- Create: `arqlib/constraints.py`, `contract/constraints.md`, `tests/test_constraints.py`

**Interfaces:**
- Produces: `constraints.SEVERITIES: Tuple[str, ...]`, dataclass `constraints.Constraint(id, titulo, regla, severidad,
  por_que, como_verificar, excepcion)`, `constraints.parse(text: str) -> List[Constraint]`,
  `constraints.lint(text: str) -> List[str]` (lista de errores; vacía = ok).

- [ ] **Step 1: Escribir el contrato inicial**

`contract/constraints.md` (Arquitectura lo completa; estas tres son las que ya se conocen):
```markdown
# Constraints de Arquitectura

Formato fijo: `### C-<AREA>-<NN> · <título>` y los cinco campos. Severidad: `bloqueante | condicionante | recomendación`.
Validar con `arq lint`. El architect cita el ID en cada hallazgo, por ejemplo `[C-PLAT-01]`.

### C-PLAT-01 · Recursos solo vía platform
- **Regla:** Todo recurso de cómputo, datos o red se aprovisiona desde platform. No se crean recursos por consola ni por IaC propia fuera de platform.
- **Severidad:** bloqueante
- **Por qué:** Gobierno, inventario, costos imputables y acceso unificado.
- **Cómo verificar:** El pedido nombra la aplicación, scope o servicio de platform, o dice cómo se va a aprovisionar. Si pide acceso directo a la consola de AWS o crear recursos a mano, incumple.
- **Excepción:** Solo con un ADR firmado por Arquitectura y Cloud.

### C-IDP-01 · IdP platform
- **Regla:** La plataforma de desarrollo interna (IdP) es platform. Aplicaciones, despliegues y parámetros se gestionan desde ahí.
- **Severidad:** bloqueante
- **Por qué:** Una sola puerta para el ciclo de vida de las aplicaciones.
- **Cómo verificar:** El ciclo de vida descrito (build, deploy, parámetros) pasa por platform.
- **Excepción:** Solo con un ADR firmado por Arquitectura.

### C-CLD-01 · AWS como única cloud
- **Regla:** Toda la infraestructura corre en AWS.
- **Severidad:** bloqueante
- **Por qué:** Contratos, seguridad y operación consolidados en un solo proveedor.
- **Cómo verificar:** No aparecen otros proveedores de cloud. Los SaaS se evalúan aparte, como señal para Seguridad y FinOps.
- **Excepción:** Solo con un ADR firmado por Arquitectura, Cloud y FinOps.
```

- [ ] **Step 2: Escribir el test que falla**

`tests/test_constraints.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.constraints import lint, parse
from arqlib.paths import CONTRACT

GOOD = """# x

### C-PLAT-01 · Recursos solo vía platform
- **Regla:** r
- **Severidad:** bloqueante
- **Por qué:** p
- **Cómo verificar:** c
- **Excepción:** e
"""


class ConstraintsTest(unittest.TestCase):
    def test_parse(self):
        [c] = parse(GOOD)
        self.assertEqual((c.id, c.titulo, c.severidad, c.como_verificar), (
            "C-PLAT-01", "Recursos solo vía platform", "bloqueante", "c"))

    def test_lint_ok(self):
        self.assertEqual(lint(GOOD), [])

    def test_shipped_contract_is_clean(self):
        text = (CONTRACT / "constraints.md").read_text(encoding="utf-8")
        self.assertEqual(lint(text), [])
        self.assertIn("C-PLAT-01", [c.id for c in parse(text)])

    def test_duplicate_id(self):
        self.assertIn("C-PLAT-01: ID duplicado", lint(GOOD + "\n" + GOOD.split("\n", 2)[2]))

    def test_invalid_severity(self):
        errors = lint(GOOD.replace("bloqueante", "urgente"))
        self.assertEqual(errors, ["C-PLAT-01: severidad inválida 'urgente' (bloqueante, condicionante, recomendación)"])

    def test_missing_field(self):
        self.assertEqual(lint(GOOD.replace("- **Excepción:** e\n", "")), ["C-PLAT-01: falta el campo Excepción"])

    def test_bad_heading(self):
        self.assertEqual(lint("### C-plat-1 · x\n"), ["encabezado inválido: '### C-plat-1 · x' (usar ### C-AREA-NN · título)"])

    def test_empty_file(self):
        self.assertEqual(lint("# nada"), ["no hay constraints"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.constraints'`

- [ ] **Step 4: Implementar**

`arqlib/constraints.py`:
```python
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
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add arqlib/constraints.py contract/constraints.md tests/test_constraints.py
git commit -m "feat: add constraints contract with parser and lint"
```

---

### Task 5: Plazo en días hábiles

**Files:**
- Create: `arqlib/timebox.py`, `tests/test_timebox.py`

**Interfaces:**
- Produces: `timebox.add_business_days(start: date, days: int) -> date`,
  `timebox.is_overdue(vence: str, today: date) -> bool`, `timebox.TimeboxError(ValueError)`.

Feriados quedan fuera del MVP: solo se saltan sábados y domingos.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_timebox.py`:
```python
from __future__ import annotations

import unittest
from datetime import date

import helpers  # noqa: F401
from arqlib.timebox import TimeboxError, add_business_days, is_overdue


class TimeboxTest(unittest.TestCase):
    def test_ten_business_days_from_wednesday(self):
        self.assertEqual(add_business_days(date(2026, 10, 7), 10), date(2026, 10, 21))

    def test_friday_plus_one_is_monday(self):
        self.assertEqual(add_business_days(date(2026, 10, 9), 1), date(2026, 10, 12))

    def test_saturday_start_plus_one_is_monday(self):
        self.assertEqual(add_business_days(date(2026, 10, 10), 1), date(2026, 10, 12))

    def test_days_must_be_positive(self):
        with self.assertRaises(TimeboxError):
            add_business_days(date(2026, 10, 7), 0)

    def test_overdue_only_after_the_due_day(self):
        self.assertFalse(is_overdue("2026-10-21", date(2026, 10, 21)))
        self.assertTrue(is_overdue("2026-10-21", date(2026, 10, 22)))

    def test_invalid_date(self):
        with self.assertRaisesRegex(TimeboxError, "fecha inválida"):
            is_overdue("21/10/2026", date(2026, 10, 22))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.timebox'`

- [ ] **Step 3: Implementar**

`arqlib/timebox.py`:
```python
"""Business-day timebox for waiting on the requester (spec D7). Weekends only; holidays are out of scope."""
from __future__ import annotations

from datetime import date, timedelta


class TimeboxError(ValueError):
    pass


def add_business_days(start: date, days: int) -> date:
    if days < 1:
        raise TimeboxError("el plazo tiene que ser de al menos 1 día hábil")
    current, counted = start, 0
    while counted < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            counted += 1
    return current


def is_overdue(vence: str, today: date) -> bool:
    try:
        due = date.fromisoformat(vence)
    except ValueError as exc:
        raise TimeboxError(f"fecha inválida {vence!r}: usar AAAA-MM-DD") from exc
    return today > due
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add arqlib/timebox.py tests/test_timebox.py
git commit -m "feat: add business-day timebox"
```

---

### Task 6: Configuración del repo de reviews y archivos de review

**Files:**
- Create: `arqlib/config.py`, `arqlib/review.py`, `tests/test_config.py`, `tests/test_review.py`

**Interfaces:**
- Consumes: `frontmatter.parse/dump` (Task 1).
- Produces:
  - `config.DEFAULT_CONFIG: dict`, `config.init_repo(repo: Path) -> List[str]` (rutas creadas),
    `config.load_config(repo: Path, require_jsm: bool = False) -> dict`,
    `config.credentials(env: Mapping[str, str]) -> Tuple[str, str, str]`, `config.ConfigError(ValueError)`.
  - `review.FIELDS: Tuple[str, ...]`, `review.check_pry(pry: str) -> str` (devuelve el PRY validado),
    `review.check_email(email: str) -> str`, `review.review_path(repo: Path, pry: str) -> Path`,
    `review.new_review(repo: Path, pry: str, nombre: str, pedido: str, contacto: str, head: str = "") -> Path`,
    `review.load(repo: Path, pry: str) -> Tuple[Dict[str, str], str]`,
    `review.save(repo: Path, pry: str, meta: Dict[str, str], body: str) -> None`, `review.ReviewError(ValueError)`.

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_config.py`:
```python
from __future__ import annotations

import json
import unittest

import helpers
from arqlib.config import ConfigError, credentials, init_repo, load_config


class ConfigTest(unittest.TestCase):
    def test_init_creates_config_and_reviews_and_is_idempotent(self):
        repo = helpers.make_repo()
        self.assertEqual(sorted(init_repo(repo)), [".arq/config.json", "reviews/"])
        self.assertEqual(init_repo(repo), [])
        self.assertEqual(load_config(repo)["timebox_dias_habiles"], 10)

    def test_missing_config_points_to_init(self):
        with self.assertRaisesRegex(ConfigError, "arq init"):
            load_config(helpers.make_repo())

    def test_invalid_json(self):
        repo = helpers.make_repo()
        (repo / ".arq").mkdir()
        (repo / ".arq" / "config.json").write_text("{nope", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "JSON inválido"):
            load_config(repo)

    def test_require_jsm_needs_ids(self):
        repo = helpers.make_repo()
        init_repo(repo)
        with self.assertRaisesRegex(ConfigError, "jsm_service_desk_id"):
            load_config(repo, require_jsm=True)

    def _write(self, repo, **changes):
        path = repo / ".arq" / "config.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(changes)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_missing_issue_type(self):
        repo = helpers.make_repo()
        init_repo(repo)
        types = dict(json.loads((repo / ".arq" / "config.json").read_text(encoding="utf-8"))["issue_types"])
        del types["subtask"]
        self._write(repo, issue_types=types)
        with self.assertRaisesRegex(ConfigError, "issue_types.subtask"):
            load_config(repo)

    def test_issue_types_must_be_an_object(self):
        repo = helpers.make_repo()
        init_repo(repo)
        self._write(repo, issue_types="Epic")
        with self.assertRaisesRegex(ConfigError, "issue_types"):
            load_config(repo)

    def test_require_jsm_needs_project_key(self):
        repo = helpers.make_repo()
        init_repo(repo)
        self._write(repo, jsm_service_desk_id="3", jsm_request_type_id="41")
        with self.assertRaisesRegex(ConfigError, "jsm_project"):
            load_config(repo, require_jsm=True)

    def test_credentials(self):
        env = {"JIRA_BASE_URL": "https://x.atlassian.net", "JIRA_EMAIL": "a@b", "JIRA_API_TOKEN": "t"}
        self.assertEqual(credentials(env), ("https://x.atlassian.net", "a@b", "t"))
        with self.assertRaisesRegex(ConfigError, "JIRA_API_TOKEN"):
            credentials({"JIRA_BASE_URL": "u", "JIRA_EMAIL": "e"})

    def test_credentials_require_https(self):
        with self.assertRaisesRegex(ConfigError, "https"):
            credentials({"JIRA_BASE_URL": "http://x.atlassian.net", "JIRA_EMAIL": "a@b", "JIRA_API_TOKEN": "t"})


if __name__ == "__main__":
    unittest.main()
```

`tests/test_review.py`:
```python
from __future__ import annotations

import unittest

import helpers
from arqlib.review import FIELDS, ReviewError, load, new_review, review_path, save


MAIL = "requester@example.com"


class ReviewTest(unittest.TestCase):
    def test_new_review(self):
        repo = helpers.make_repo()
        path = new_review(repo, "PRY-2026-0028", "PoC modelos IA\nLocales", "Habilitar una G6e.xlarge\n", MAIL,
                          "reviewer@example.com")
        self.assertEqual(path, repo / "reviews" / "PRY-2026-0028.md")
        meta, body = load(repo, "PRY-2026-0028")
        self.assertEqual(list(meta), list(FIELDS))
        self.assertEqual((meta["pry"], meta["nombre"], meta["estado"], meta["contacto"], meta["head"]), (
            "PRY-2026-0028", "PoC modelos IA Locales", "recibido", MAIL, "reviewer@example.com"))
        self.assertEqual(body, "## Pedido original\n\nHabilitar una G6e.xlarge\n")

    def test_new_review_refuses_overwrite(self):
        repo = helpers.make_repo()
        new_review(repo, "PRY-2026-0028", "x", "y", MAIL)
        with self.assertRaisesRegex(ReviewError, "ya existe"):
            new_review(repo, "PRY-2026-0028", "x", "y", MAIL)

    def test_invalid_email(self):
        repo = helpers.make_repo()
        for bad in ("pablo", "a@b", "a b@c.d", ""):
            with self.assertRaisesRegex(ReviewError, "email inválido"):
                new_review(repo, "PRY-2026-0028", "x", "y", bad)
        with self.assertRaisesRegex(ReviewError, "email inválido"):
            new_review(repo, "PRY-2026-0028", "x", "y", MAIL, "head")

    def test_malformed_and_traversal_ids_are_rejected(self):
        repo = helpers.make_repo()
        for bad in ("PRY-2026-28", "pry-2026-0028", "../../etc/passwd", "PRY-2026-0028/../x", ""):
            with self.assertRaisesRegex(ReviewError, "PRY inválido"):
                review_path(repo, bad)
        self.assertFalse((repo / "reviews").exists())

    def test_load_missing(self):
        with self.assertRaisesRegex(ReviewError, "arq new"):
            load(helpers.make_repo(), "PRY-2026-0001")

    def test_save_roundtrip(self):
        repo = helpers.make_repo()
        new_review(repo, "PRY-2026-0026", "Product Brain", "Migrar", "user@example.com")
        meta, body = load(repo, "PRY-2026-0026")
        meta["nivel"] = "complejo"
        save(repo, "PRY-2026-0026", meta, body + "\n## Análisis\n")
        self.assertEqual(load(repo, "PRY-2026-0026")[0]["nivel"], "complejo")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.config'` y `'arqlib.review'`

- [ ] **Step 3: Implementar `config.py`**

`arqlib/config.py`:
```python
"""Team reviews repo settings (.arq/config.json) and Jira credentials from the environment."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Mapping, Tuple

DEFAULT_CONFIG = {
    "jira_project": "ARQ",
    "jsm_project": "",
    "jsm_service_desk_id": "",
    "jsm_request_type_id": "",
    "issue_types": {"epic": "Epic", "story": "Story", "task": "Task", "subtask": "Subtask"},
    "link_type": "Relates",
    "timebox_dias_habiles": 10,
}
_REQUIRED = ("jira_project", "issue_types", "link_type", "timebox_dias_habiles")
_ISSUE_TYPES = ("epic", "story", "task", "subtask")
_ENV = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")


class ConfigError(ValueError):
    pass


def config_path(repo: Path) -> Path:
    return repo / ".arq" / "config.json"


def init_repo(repo: Path) -> List[str]:
    created: List[str] = []
    path = config_path(repo)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(".arq/config.json")
    if not (repo / "reviews").exists():
        (repo / "reviews").mkdir(parents=True)
        created.append("reviews/")
    return created


def load_config(repo: Path, require_jsm: bool = False) -> dict:
    path = config_path(repo)
    if not path.exists():
        raise ConfigError(f"falta {path}: correr `arq init` en el repo de reviews")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON inválido en {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} tiene que ser un objeto JSON")
    missing = [key for key in _REQUIRED if key not in data]
    types = data.get("issue_types")
    if "issue_types" in data and not isinstance(types, dict):
        raise ConfigError("issue_types tiene que ser un objeto: {\"epic\": ..., \"story\": ..., ...}")
    missing += [f"issue_types.{t}" for t in _ISSUE_TYPES if not (types or {}).get(t)]
    if require_jsm:
        missing += [key for key in ("jsm_project", "jsm_service_desk_id", "jsm_request_type_id")
                    if not str(data.get(key, "")).strip()]
    if missing:
        raise ConfigError(f"faltan en {path}: {', '.join(missing)}")
    if not isinstance(data["timebox_dias_habiles"], int) or data["timebox_dias_habiles"] < 1:
        raise ConfigError("timebox_dias_habiles tiene que ser un entero ≥ 1")
    return data


def credentials(env: Mapping[str, str]) -> Tuple[str, str, str]:
    missing = [name for name in _ENV if not env.get(name, "").strip()]
    if missing:
        raise ConfigError(f"faltan variables de entorno: {', '.join(missing)}")
    if not env["JIRA_BASE_URL"].startswith("https://"):
        raise ConfigError("JIRA_BASE_URL tiene que empezar con https:// (el token viaja en cada request)")
    return env["JIRA_BASE_URL"], env["JIRA_EMAIL"], env["JIRA_API_TOKEN"]
```

- [ ] **Step 4: Implementar `review.py`**

`arqlib/review.py`:
```python
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
```

- [ ] **Step 5: Correr y verificar que pasan**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add arqlib/config.py arqlib/review.py tests/test_config.py tests/test_review.py
git commit -m "feat: add reviews repo config and review files"
```

---

### Task 7: Input mínimo, plantillas y render

**Files:**
- Create: `arqlib/inputs.py`, `arqlib/render.py`, `contract/minimum-input.md`, `contract/templates/analisis.md`,
  `contract/templates/comentario-pry.md`, `contract/templates/jsm-pedido-info.md`,
  `contract/templates/jsm-devolucion.md`, `contract/templates/jsm-cierre.md`, `contract/templates/escalar-rfc.md`,
  `tests/test_inputs.py`, `tests/test_render.py`

**Interfaces:**
- Produces: `inputs.NIVELES: Tuple[str, ...]`, `inputs.input_ids(nivel: str) -> List[str]` (complejo incluye simple),
  `inputs.all_ids() -> List[str]`, `inputs.InputsError(ValueError)`;
  `render.render(template: str, values: Dict[str, str]) -> str`, `render.assert_rendered(text: str) -> None`,
  `render.load_template(name: str) -> str`, `render.matches_template(template: str, text: str) -> bool`
  (el texto es la plantilla con cada placeholder completado; tolera diferencias de espacios y saltos de línea),
  `render.RenderError(ValueError)`.

- [ ] **Step 1: Escribir el contrato de input mínimo**

`contract/minimum-input.md`:
```markdown
# Input mínimo por nivel

El test: cada afirmación del pedido tiene que poder apuntar a un artefacto concreto (número, componente, diagrama o
métrica). Si no puede, es prosa y cuenta como faltante. El nivel `complejo` exige todo lo de `simple` y además lo suyo.
El architect anota los IDs que faltan en el frontmatter (`faltantes: id1, id2`).

## simple
- `problema` — Qué problema concreto se resuelve y para quién.
- `hipotesis_medible` — Métrica, valor actual y umbral que valida o refuta la hipótesis.
- `recursos` — Tipo, tamaño y cantidad de cada recurso.
- `duracion_y_baja` — Cuánto dura y en qué fecha se da de baja.
- `costo_estimado` — Costo mensual estimado y cómo se calculó.
- `responsable` — Persona responsable del recurso mientras exista.
- `via_aprovisionamiento` — Cómo se aprovisiona (aplicación, scope o servicio de platform).

## complejo
- `diagrama_c4` — Diagrama C4 de nivel 1 y 2 (contexto y contenedores), revisable.
- `flujos_datos` — Flujos de datos y clasificación de la información que circula.
- `cuentas_entornos` — Cuentas y entornos de origen y destino.
- `rollback` — Plan de vuelta atrás y criterio para activarlo.
- `dependencias` — Dependencias con otros equipos, cada una con dueño.
- `rnf` — Requisitos no funcionales: disponibilidad, latencia, RPO/RTO si aplica.
```

- [ ] **Step 2: Escribir las plantillas**

`contract/templates/analisis.md`:
```markdown
# {{pry}} · {{nombre}}

> Revisión de Arquitectura. Fuente de verdad en git; cualquier copia (Confluence, Product Brain) se genera desde acá.

## Lo que entendimos
{{reformulacion}}

## Input faltante
{{faltantes}}

## Drivers de la decisión
{{drivers}}

## Evaluación por componente
| Componente | Estado | Hallazgo |
|---|---|---|
{{evaluacion}}

## Opciones consideradas
{{opciones}}

## Decisión
{{decision}}

## Recomendación
{{recomendacion}}

## Condiciones
{{condiciones}}

## Consecuencias
{{consecuencias}}

## Señales para otros sectores (sin veredicto)
{{senales}}

## Veredicto propuesto
{{veredicto}}
```

`contract/templates/jsm-cierre.md`:
```markdown
Hola {{contacto}}, el pedido {{pry}} ({{nombre}}) estuvo abierto hasta el {{vence}} esperando la información que
pedimos, y no la recibimos.

Lo cerramos como incompleto en la plataforma de requerimientos. Cuando tengan la información, pueden cargar un pedido
nuevo y mencionar este ticket: retomamos desde donde quedó.

Equipo de Arquitectura
```

`contract/templates/comentario-pry.md`:
```markdown
Arquitectura: {{veredicto}}.
{{resumen}}
Condiciones: {{condiciones}}
Análisis completo y seguimiento: {{link}}
```

`contract/templates/jsm-pedido-info.md`:
```markdown
Hola {{contacto}}, gracias por el pedido {{pry}} ({{nombre}}).

Para poder evaluarlo desde Arquitectura necesitamos completar esta información:

{{faltantes}}

Por qué lo pedimos: {{motivo}}

Pueden responder en este mismo ticket. Mantenemos el pedido abierto hasta el {{vence}}; si para esa fecha no tenemos la
información, lo vamos a cerrar como incompleto y se podrá volver a cargar cuando esté lista.

Equipo de Arquitectura
```

`contract/templates/jsm-devolucion.md`:
```markdown
Hola {{contacto}}, terminamos la revisión de Arquitectura del pedido {{pry}} ({{nombre}}).

Resultado: {{veredicto}}

{{resumen}}

Recomendaciones:
{{recomendaciones}}

Condiciones para avanzar:
{{condiciones}}

Otros sectores (Cloud, Seguridad, FinOps) hacen su propia validación; les dejamos estas observaciones para que las
tengan en cuenta:
{{senales}}

El análisis completo está en {{link}}. Cualquier duda, respondan en este ticket.

Equipo de Arquitectura
```

`contract/templates/escalar-rfc.md`:
```markdown
# Cuándo escalar a RFC en Product Brain

Se escala si el pedido es de nivel `complejo` **y** cumple al menos una de estas condiciones:

- Dura más de 3 meses.
- Involucra a más de 2 equipos.

Al escalar, la épica ARQ sigue siendo la de *revisión*; la épica de *delivery* la crea el flujo de Product Brain y las
dos se linkean (`arq link`), sin fusionarse.
```

- [ ] **Step 3: Escribir los tests que fallan**

`tests/test_inputs.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.inputs import InputsError, all_ids, input_ids


class InputsTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(input_ids("simple"), ["problema", "hipotesis_medible", "recursos", "duracion_y_baja",
                                               "costo_estimado", "responsable", "via_aprovisionamiento"])

    def test_complejo_includes_simple(self):
        ids = input_ids("complejo")
        self.assertEqual(ids[:7], input_ids("simple"))
        self.assertIn("rollback", ids)

    def test_ids_unique(self):
        self.assertEqual(len(all_ids()), len(set(all_ids())))

    def test_unknown_nivel(self):
        with self.assertRaisesRegex(InputsError, "nivel"):
            input_ids("medio")


if __name__ == "__main__":
    unittest.main()
```

`tests/test_render.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.render import RenderError, assert_rendered, load_template, matches_template, render

TEMPLATES = ("analisis.md", "comentario-pry.md", "jsm-pedido-info.md", "jsm-devolucion.md", "jsm-cierre.md",
             "escalar-rfc.md")


class RenderTest(unittest.TestCase):
    def test_render(self):
        self.assertEqual(render("Hola {{contacto}} ({{pry}})", {"contacto": "Juan", "pry": "PRY-2026-0028"}),
                         "Hola Juan (PRY-2026-0028)")

    def test_render_lists_missing_values(self):
        with self.assertRaisesRegex(RenderError, "contacto, pry"):
            render("{{contacto}} {{pry}}", {"contacto": "  "})

    def test_assert_rendered(self):
        assert_rendered("todo completo")
        with self.assertRaisesRegex(RenderError, "nombre"):
            assert_rendered("Hola {{nombre}}")

    def test_all_templates_exist(self):
        for name in TEMPLATES:
            self.assertTrue(load_template(name).strip(), name)

    def test_unknown_template(self):
        with self.assertRaisesRegex(RenderError, "no existe"):
            load_template("../constraints.md")

    def test_filled_template_matches_even_reflowed(self):
        template = load_template("jsm-cierre.md")
        text = render(template, {"contacto": "Juan Pablo", "pry": "PRY-2026-0028", "nombre": "PoC",
                                 "vence": "2026-10-21"})
        self.assertTrue(matches_template(template, text))
        self.assertTrue(matches_template(template, " ".join(text.split())))  # otro ajuste de líneas

    def test_multiline_values_match(self):
        template = load_template("jsm-pedido-info.md")
        text = render(template, {"contacto": "Juan", "pry": "PRY-2026-0028", "nombre": "PoC",
                                 "faltantes": "- Fecha de baja\n- Costo mensual", "motivo": "Sin eso no hay caso.",
                                 "vence": "2026-10-21"})
        self.assertTrue(matches_template(template, text))

    def test_free_text_or_other_template_does_not_match(self):
        template = load_template("jsm-devolucion.md")
        self.assertFalse(matches_template(template, "127.0.0.1 localhost"))
        cierre = render(load_template("jsm-cierre.md"), {"contacto": "J", "pry": "P", "nombre": "N", "vence": "V"})
        self.assertFalse(matches_template(template, cierre))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Correr y verificar que fallan**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.inputs'` y `'arqlib.render'`

- [ ] **Step 5: Implementar**

`arqlib/inputs.py`:
```python
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
```

`arqlib/render.py`:
```python
"""`{{name}}` placeholders in contract templates. Nothing public leaves with a placeholder left in it."""
from __future__ import annotations

import re
from typing import Dict

from arqlib.paths import CONTRACT

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
_NAME = re.compile(r"[\w-]+\.md")


class RenderError(ValueError):
    pass


def render(template: str, values: Dict[str, str]) -> str:
    missing = sorted({name for name in PLACEHOLDER.findall(template) if not values.get(name, "").strip()})
    if missing:
        raise RenderError(f"faltan valores para: {', '.join(missing)}")
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


def assert_rendered(text: str) -> None:
    left = sorted(set(PLACEHOLDER.findall(text)))
    if left:
        raise RenderError(f"quedan placeholders sin completar: {', '.join(left)}")


def load_template(name: str) -> str:
    path = CONTRACT / "templates" / name
    if not _NAME.fullmatch(name) or not path.exists():
        raise RenderError(f"la plantilla {name!r} no existe en {CONTRACT / 'templates'}")
    return path.read_text(encoding="utf-8")


def _literal(text: str) -> str:
    return r"\s+".join(re.escape(word) for word in text.split())


def matches_template(template: str, text: str) -> bool:
    """True when `text` is `template` with every placeholder filled, ignoring how whitespace and lines are laid out."""
    pieces = []
    for index, part in enumerate(PLACEHOLDER.split(template)):
        if index % 2:
            pieces.append(r"(.+?)")
        elif part.strip():
            pieces.append(_literal(part))
    return re.fullmatch(r"\s*".join(pieces), text.strip(), flags=re.S) is not None
```

- [ ] **Step 6: Correr y verificar que pasan**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add arqlib/inputs.py arqlib/render.py contract tests/test_inputs.py tests/test_render.py
git commit -m "feat: add minimum-input contract, templates and render"
```

---

### Task 8: Estructura de Jira por nivel

**Files:**
- Create: `arqlib/structure.py`, `tests/test_structure.py`

**Interfaces:**
- Produces: `structure.pry_label(pry: str) -> str` (`"pry:2026-0028"`),
  `structure.base_labels(meta: Dict[str, str]) -> List[str]` (`[pry:..., nivel:...]`),
  `structure.build_plan(meta: Dict[str, str], validacion: bool = False) -> dict` con forma
  `{"epic": Node, "items": [Node & {"type": "task"|"story", "subtasks": [Node]}]}` donde
  `Node = {"summary": str, "labels": List[str], "description": str}`;
  `structure.followup_plan(meta: Dict[str, str], condiciones: List[str]) -> dict` →
  `{"parent_summary": str, "subtasks": [Node]}` (una sub-task por condición de un "aprobar con condiciones");
  `structure.StructureError(ValueError)`.

"Validación técnica" solo se crea con `validacion=True` (spec §8: opcional).

- [ ] **Step 1: Escribir el test que falla**

`tests/test_structure.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.structure import StructureError, build_plan, followup_plan, pry_label


def meta(nivel: str) -> dict:
    return {"pry": "PRY-2026-0028", "nombre": "PoC modelos IA Locales", "nivel": nivel}


class StructureTest(unittest.TestCase):
    def test_label(self):
        self.assertEqual(pry_label("PRY-2026-0028"), "pry:2026-0028")

    def test_simple_is_minimal_epic(self):
        plan = build_plan(meta("simple"))
        self.assertEqual(plan["epic"]["summary"], "[PRY-2026-0028] PoC modelos IA Locales")
        self.assertEqual(plan["epic"]["labels"], ["pry:2026-0028", "nivel:simple"])
        [task] = plan["items"]
        self.assertEqual((task["type"], task["summary"]), ("task", "Revisión PRY-2026-0028"))
        self.assertEqual([s["summary"] for s in task["subtasks"]], [
            "Triage y apertura", "Gap check de input mínimo", "Análisis y opciones", "Revisión y firma",
            "Publicar devolución"])
        self.assertEqual(task["subtasks"][0]["labels"], ["pry:2026-0028", "nivel:simple", "track:coordinacion"])

    def test_complejo_has_three_stories_by_default(self):
        plan = build_plan(meta("complejo"))
        self.assertEqual([i["summary"] for i in plan["items"]], [
            "Intake y triage", "Análisis y opciones", "Decisión y comunicación"])
        self.assertTrue(all(i["type"] == "story" for i in plan["items"]))
        self.assertEqual(plan["items"][2]["labels"][-2:], ["track:coordinacion", "track:tecnica"])

    def test_validacion_tecnica_is_opt_in(self):
        plan = build_plan(meta("complejo"), validacion=True)
        self.assertEqual(plan["items"][2]["summary"], "Validación técnica")
        self.assertEqual(len(plan["items"]), 4)

    def test_followup_one_subtask_per_condition(self):
        follow = followup_plan(meta("simple"), ["Apagado fuera de horario", "x" * 300])
        self.assertEqual(follow["parent_summary"], "Revisión PRY-2026-0028")
        self.assertEqual(follow["subtasks"][0]["summary"], "Condición: Apagado fuera de horario")
        self.assertLessEqual(len(follow["subtasks"][1]["summary"]), 240)
        self.assertIn("x" * 300, follow["subtasks"][1]["description"])
        self.assertEqual(follow["subtasks"][0]["labels"], ["pry:2026-0028", "nivel:simple", "track:coordinacion"])
        self.assertEqual(followup_plan(meta("complejo"), ["c"])["parent_summary"], "Decisión y comunicación")

    def test_followup_needs_conditions(self):
        with self.assertRaisesRegex(StructureError, "condición"):
            followup_plan(meta("simple"), ["  "])

    def test_every_issue_carries_pry_and_nivel_and_no_seniority(self):
        plan = build_plan(meta("complejo"), validacion=True)
        nodes = [plan["epic"]] + plan["items"] + [s for i in plan["items"] for s in i["subtasks"]]
        for node in nodes:
            self.assertEqual(node["labels"][:2], ["pry:2026-0028", "nivel:complejo"])
            self.assertFalse(any(word in " ".join(node["labels"]) for word in ("sr", "expert", "lead", "dev")))
            self.assertTrue(node["description"].strip())

    def test_requires_triage(self):
        with self.assertRaisesRegex(StructureError, "arq triage"):
            build_plan(meta(""))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.structure'`

- [ ] **Step 3: Implementar**

`arqlib/structure.py`:
```python
"""Jira shape per level (spec §8). Pure: builds the plan, never talks to Jira."""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from arqlib.review import check_pry

COORD, TEC = "track:coordinacion", "track:tecnica"

SIMPLE_SUBTASKS: Tuple[Tuple[str, str, str], ...] = (
    ("Triage y apertura", COORD, "Contestar el triage, abrir la épica y el pedido en JSM, arrancar el plazo."),
    ("Gap check de input mínimo", TEC, "Contrastar el pedido con el input mínimo del nivel y pedir lo que falte."),
    ("Análisis y opciones", TEC, "Evaluar contra las constraints y proponer opciones para el componente más débil."),
    ("Revisión y firma", TEC, "Revisar el análisis y firmarlo."),
    ("Publicar devolución", COORD, "Responder en JSM y dejar el comentario en la plataforma PRY."),
)

COMPLEX_STORIES: Tuple[Tuple[str, Tuple[str, ...], str, Tuple[Tuple[str, str, str], ...]], ...] = (
    ("Intake y triage", (COORD,), "Dejar el pedido normalizado, triado y con canales abiertos.", (
        ("Normalizar pedido", COORD, "Pasar el pedido a reviews/PRY-XXXX.md."),
        ("Triage", COORD, "Contestar las preguntas de triage."),
        ("Abrir JSM y plazo", COORD, "Crear el pedido en JSM y arrancar el plazo."),
    )),
    ("Análisis y opciones", (TEC,), "Producir el análisis con opciones y recomendación.", (
        ("Gap check de input mínimo", TEC, "Contrastar con el input mínimo del nivel complejo."),
        ("Análisis vs constraints", TEC, "Evaluar cada componente contra las constraints."),
        ("Opciones y recomendación", TEC, "Original y dos opciones, recomendación y condiciones."),
    )),
    ("Validación técnica", (TEC,), "Opcional: validar con una prueba acotada lo que el análisis no puede afirmar.", (
        ("Prueba acotada", TEC, "Prueba técnica con alcance y fecha de fin definidos."),
    )),
    ("Decisión y comunicación", (COORD, TEC), "Firmar y comunicar la decisión.", (
        ("Revisión y firma", TEC, "Revisar el análisis y firmarlo."),
        ("Publicar devolución", COORD, "Responder en JSM, comentar en la plataforma PRY y escalar a RFC si corresponde."),
    )),
)


class StructureError(ValueError):
    pass


def pry_label(pry: str) -> str:
    return "pry:" + check_pry(pry)[len("PRY-"):]


def _node(summary: str, labels: List[str], description: str) -> Dict[str, object]:
    return {"summary": summary, "labels": labels, "description": description}


def _subtasks(base: List[str], specs: Sequence[Tuple[str, str, str]]) -> List[Dict[str, object]]:
    return [_node(summary, base + [track], description) for summary, track, description in specs]


def base_labels(meta: Dict[str, str]) -> List[str]:
    nivel = meta.get("nivel", "")
    if nivel not in ("simple", "complejo"):
        raise StructureError("el pedido no tiene nivel: correr `arq triage` primero")
    return [pry_label(meta.get("pry", "")), f"nivel:{nivel}"]


def build_plan(meta: Dict[str, str], validacion: bool = False) -> dict:
    base = base_labels(meta)
    pry = meta["pry"]
    epic = _node(f"[{pry}] {meta.get('nombre', '')}".strip(), list(base),
                 f"Revisión de Arquitectura del pedido {pry}. Fuente de verdad: reviews/{pry}.md en el repo de reviews.")
    if meta["nivel"] == "simple":
        task = _node(f"Revisión {pry}", base + [COORD, TEC], "Revisión de nivel simple.")
        task.update(type="task", subtasks=_subtasks(base, SIMPLE_SUBTASKS))
        return {"epic": epic, "items": [task]}
    items = []
    for summary, tracks, description, subtasks in COMPLEX_STORIES:
        if summary == "Validación técnica" and not validacion:
            continue
        story = _node(summary, base + list(tracks), description)
        story.update(type="story", subtasks=_subtasks(base, subtasks))
        items.append(story)
    return {"epic": epic, "items": items}


def followup_plan(meta: Dict[str, str], condiciones: List[str]) -> dict:
    base = base_labels(meta)
    texts = [" ".join(c.split()) for c in condiciones if c.strip()]
    if not texts:
        raise StructureError("hace falta al menos una condición")
    parent = f"Revisión {meta['pry']}" if meta["nivel"] == "simple" else "Decisión y comunicación"
    subtasks = []
    for text in texts:
        summary = f"Condición: {text}"
        if len(summary) > 240:
            summary = summary[:237].rstrip() + "..."
        subtasks.append(_node(summary, base + [COORD], f"Condición de la aprobación, a verificar: {text}"))
    return {"parent_summary": parent, "subtasks": subtasks}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add arqlib/structure.py tests/test_structure.py
git commit -m "feat: build Jira epic structure per triage level"
```

---

### Task 9: Journal y cliente Jira/JSM

**Files:**
- Create: `arqlib/journal.py`, `arqlib/jira.py`, `tests/test_journal.py`, `tests/test_jira.py`

**Interfaces:**
- Produces:
  - `journal.journal(repo: Path, command: str, now: Optional[Callable[[], str]] = None) -> Callable[[dict], None]`
    (escribe en `.arq/jira-writes.jsonl`, nunca lanza); `journal.read_entries(repo: Path) -> List[dict]` (ignora
    líneas rotas).
  - `jira.Jira(base_url: str, email: str, token: str, opener=None, timeout: float = 20.0, journal=None)` con:
    `search_label(label: str) -> List[Dict[str, Optional[str]]]` (cada uno `{"key", "summary", "parent"}`),
    `get_brief(key: str) -> Optional[Dict[str, Optional[str]]]` (`None` si no existe),
    `create(fields: dict) -> str`, `link(inward: str, outward: str, link_type: str) -> None`,
    `find_user(email: str) -> str` (accountId),
    `create_request(service_desk_id: str, request_type_id: str, summary: str, description: str,
    on_behalf_of: str = "") -> str`, `add_participants(key: str, account_ids: List[str]) -> None`,
    `add_labels(key: str, labels: List[str]) -> None`, `comment(key: str, body: str, public: bool) -> None`;
    `jira.check_key(key: str) -> str`; `jira.JiraError(RuntimeError)` con atributo `status: Optional[int]`.

Endpoints (Jira Cloud): búsqueda `POST /rest/api/3/search/jql` (paginada con `nextPageToken`), lectura
`GET /rest/api/2/issue/{key}?fields=summary,parent`, alta `POST /rest/api/2/issue`, labels
`PUT /rest/api/2/issue/{key}` con `{"update": {"labels": [{"add": ...}]}}`, link `POST /rest/api/2/issueLink`,
usuarios `GET /rest/api/3/user/search?query=<email>`, request JSM `POST /rest/servicedeskapi/request` con
`raiseOnBehalfOf` (accountId del requirente), participantes
`POST /rest/servicedeskapi/request/{key}/participant` con `{"accountIds": [...]}`, comentario JSM
`POST /rest/servicedeskapi/request/{key}/comment` con `{"body", "public"}`. `public: false` es la nota interna;
`public: true` es la respuesta al cliente. Toda clave se valida con `check_key` antes de entrar en una URL.

`find_user`: si la API devuelve el email, se elige la coincidencia exacta (sin distinguir mayúsculas). Si la privacidad
del sitio lo oculta y hay un solo resultado, se usa ese. Ninguno → error que pide dar de alta al requirente como
cliente del Service Desk. Varios sin coincidencia exacta → error de ambigüedad. Nunca se crea un ticket a nombre de
otra persona.

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_journal.py`:
```python
from __future__ import annotations

import json
import unittest

import helpers
from arqlib.journal import journal, read_entries


class JournalTest(unittest.TestCase):
    def test_appends_json_lines(self):
        repo = helpers.make_repo()
        write = journal(repo, "jira", now=lambda: "2026-10-07T21:00:00Z")
        write({"action": "create", "key": "ARQ-1"})
        write({"action": "link", "inward": "JSM-1", "outward": "ARQ-1"})
        lines = (repo / ".arq" / "jira-writes.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(lines[0]), {"ts": "2026-10-07T21:00:00Z", "tool": "arq-review", "command": "jira",
                                                "action": "create", "key": "ARQ-1"})
        self.assertEqual(len(lines), 2)

    def test_never_raises(self):
        repo = helpers.make_repo()
        (repo / ".arq").write_text("soy un archivo, no una carpeta", encoding="utf-8")
        journal(repo, "jira")({"action": "create"})  # no exception

    def test_read_entries_skips_broken_lines(self):
        repo = helpers.make_repo()
        write = journal(repo, "jira", now=lambda: "t")
        write({"action": "create", "key": "ARQ-1"})
        with (repo / ".arq" / "jira-writes.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{roto\n")
        self.assertEqual([e["key"] for e in read_entries(repo)], ["ARQ-1"])
        self.assertEqual(read_entries(helpers.make_repo()), [])


if __name__ == "__main__":
    unittest.main()
```

`tests/test_jira.py`:
```python
from __future__ import annotations

import io
import json
import unittest
import urllib.error

import helpers  # noqa: F401
from arqlib.jira import Jira, JiraError


class FakeOpener:
    """Records every request and answers from a queue of JSON bodies (or exceptions)."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, request, timeout=None):
        body = json.loads(request.data) if request.data else None
        self.calls.append((request.get_method(), request.full_url, body))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return io.BytesIO(json.dumps(response).encode() if response is not None else b"")


def client(opener, log=None):
    return Jira("https://x.atlassian.net/", "a@b", "t", opener=opener, journal=(log.append if log is not None else None))


class JiraTest(unittest.TestCase):
    def test_search_label_paginates_and_flattens(self):
        opener = FakeOpener(
            {"issues": [{"key": "ARQ-1", "fields": {"summary": "[PRY-2026-0028] x", "parent": None}}],
             "nextPageToken": "p2"},
            {"issues": [{"key": "ARQ-2", "fields": {"summary": "Revisión PRY-2026-0028", "parent": {"key": "ARQ-1"}}}]},
        )
        found = client(opener).search_label("pry:2026-0028")
        self.assertEqual(found, [{"key": "ARQ-1", "summary": "[PRY-2026-0028] x", "parent": None},
                                 {"key": "ARQ-2", "summary": "Revisión PRY-2026-0028", "parent": "ARQ-1"}])
        method, url, body = opener.calls[0]
        self.assertEqual((method, url), ("POST", "https://x.atlassian.net/rest/api/3/search/jql"))
        self.assertEqual(body["jql"], 'labels = "pry:2026-0028" ORDER BY key')
        self.assertEqual(opener.calls[1][2]["nextPageToken"], "p2")

    def test_search_label_rejects_jql_injection(self):
        with self.assertRaisesRegex(JiraError, "label inválido"):
            client(FakeOpener()).search_label('x" OR project = SECRET')

    def test_create_journals(self):
        log = []
        key = client(FakeOpener({"key": "ARQ-7"}), log).create({"summary": "s"})
        self.assertEqual(key, "ARQ-7")
        self.assertEqual(log, [{"action": "create", "key": "ARQ-7", "fields": {"summary": "s"}}])

    def test_link(self):
        opener, log = FakeOpener(None), []
        client(opener, log).link("JSM-1", "ARQ-1", "Relates")
        self.assertEqual(opener.calls[0], ("POST", "https://x.atlassian.net/rest/api/2/issueLink", {
            "type": {"name": "Relates"}, "inwardIssue": {"key": "JSM-1"}, "outwardIssue": {"key": "ARQ-1"}}))
        self.assertEqual(log[0]["action"], "link")

    def test_create_request_on_behalf_of_requester(self):
        opener = FakeOpener({"issueKey": "JSM-12"})
        key = client(opener).create_request("3", "41", "PRY-2026-0028 · x", "desc", on_behalf_of="acc-juan")
        self.assertEqual(key, "JSM-12")
        self.assertEqual(opener.calls[0][2], {"serviceDeskId": "3", "requestTypeId": "41",
                                              "requestFieldValues": {"summary": "PRY-2026-0028 · x",
                                                                     "description": "desc"},
                                              "raiseOnBehalfOf": "acc-juan"})

    def test_create_without_key_in_response_is_a_jira_error(self):
        with self.assertRaisesRegex(JiraError, "sin clave"):
            client(FakeOpener({})).create({"summary": "s"})

    def test_find_user_exact_email(self):
        opener = FakeOpener([{"accountId": "a1", "emailAddress": "user@example.com"},
                             {"accountId": "a2", "emailAddress": "requester@example.com"}])
        self.assertEqual(client(opener).find_user("requester@example.com"), "a2")
        self.assertIn("/rest/api/3/user/search?query=requester%40example.com", opener.calls[0][1])

    def test_find_user_hidden_email_single_result(self):
        self.assertEqual(client(FakeOpener([{"accountId": "a9"}])).find_user("x@y.com"), "a9")

    def test_find_user_none_or_ambiguous(self):
        with self.assertRaisesRegex(JiraError, "cliente del Service Desk"):
            client(FakeOpener([])).find_user("x@y.com")
        with self.assertRaisesRegex(JiraError, "ambiguo"):
            client(FakeOpener([{"accountId": "a"}, {"accountId": "b"}])).find_user("x@y.com")

    def test_participants_and_labels(self):
        opener, log = FakeOpener({}, None), []
        jira = client(opener, log)
        jira.add_participants("JSM-12", ["acc-head"])
        jira.add_labels("JSM-12", ["pry:2026-0028", "nivel:simple"])
        self.assertEqual(opener.calls[0], ("POST", "https://x.atlassian.net/rest/servicedeskapi/request/JSM-12/participant",
                                           {"accountIds": ["acc-head"]}))
        self.assertEqual(opener.calls[1], ("PUT", "https://x.atlassian.net/rest/api/2/issue/JSM-12",
                                           {"update": {"labels": [{"add": "pry:2026-0028"}, {"add": "nivel:simple"}]}}))
        self.assertEqual([e["action"] for e in log], ["jsm-participants", "labels"])

    def test_get_brief(self):
        opener = FakeOpener({"key": "ARQ-2", "fields": {"summary": "s", "parent": {"key": "ARQ-1"}}})
        self.assertEqual(client(opener).get_brief("ARQ-2"), {"key": "ARQ-2", "summary": "s", "parent": "ARQ-1"})
        missing = urllib.error.HTTPError("u", 404, "Not Found", {}, io.BytesIO(b"{}"))
        self.assertIsNone(client(FakeOpener(missing)).get_brief("ARQ-9"))

    def test_keys_are_validated_before_building_urls(self):
        jira = client(FakeOpener())
        for call in (lambda: jira.comment("../../rest/api/2/issue/X", "b", public=True),
                     lambda: jira.link("JSM-1", "ARQ-1/../x", "Relates"),
                     lambda: jira.add_labels("jsm-1", ["l"]),
                     lambda: jira.get_brief("")):
            with self.assertRaisesRegex(JiraError, "clave de Jira inválida"):
                call()

    def test_comment_public_and_internal_are_distinct(self):
        opener, log = FakeOpener({}, {}), []
        jira = client(opener, log)
        jira.comment("JSM-12", "hola", public=True)
        jira.comment("JSM-12", "debate", public=False)
        self.assertEqual(opener.calls[0][1], "https://x.atlassian.net/rest/servicedeskapi/request/JSM-12/comment")
        self.assertEqual([c[2]["public"] for c in opener.calls], [True, False])
        self.assertEqual([e["public"] for e in log], [True, False])

    def test_http_error(self):
        error = urllib.error.HTTPError("u", 400, "Bad", {}, io.BytesIO(b'{"errors":{"summary":"required"}}'))
        with self.assertRaisesRegex(JiraError, "HTTP 400.*summary"):
            client(FakeOpener(error)).create({})

    def test_network_error(self):
        with self.assertRaisesRegex(JiraError, "no se pudo conectar"):
            client(FakeOpener(urllib.error.URLError("dns"))).create({})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.journal'` y `'arqlib.jira'`

- [ ] **Step 3: Implementar `journal.py`**

`arqlib/journal.py`:
```python
"""Every write arq makes to Jira/JSM, one JSON line each in .arq/jira-writes.jsonl (same idea as jira-kanban)."""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Callable, List, Optional


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def journal(repo: Path, command: str, now: Optional[Callable[[], str]] = None) -> Callable[[dict], None]:
    """A writer for Jira(journal=...). It never raises: a log that cannot be written must not undo the write."""
    clock = now or _utc_now

    def write(entry: dict) -> None:
        try:
            path = repo / ".arq" / "jira-writes.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"ts": clock(), "tool": "arq-review", "command": command, **entry},
                                        ensure_ascii=False) + "\n")
        except OSError:
            pass

    return write


def read_entries(repo: Path) -> List[dict]:
    """Every journaled write, oldest first. A broken line is skipped, never fatal."""
    path = repo / ".arq" / "jira-writes.jsonl"
    if not path.exists():
        return []
    entries: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries
```

- [ ] **Step 4: Implementar `jira.py`**

`arqlib/jira.py`:
```python
"""Small Jira Cloud + JSM client, stdlib only. Reads are never journaled; every successful write is."""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Dict, List, Optional

_LABEL = re.compile(r"[\w:.-]+")
_KEY = re.compile(r"[A-Z][A-Z0-9]+-\d+")


class JiraError(RuntimeError):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def check_key(key: str) -> str:
    if not _KEY.fullmatch(key or ""):
        raise JiraError(f"clave de Jira inválida {key!r}")
    return key


class Jira:
    def __init__(self, base_url: str, email: str, token: str, opener: Optional[Callable] = None,
                 timeout: float = 20.0, journal: Optional[Callable[[dict], None]] = None):
        self.base = base_url.rstrip("/")
        self._auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        self._open = opener or urllib.request.urlopen
        self._timeout = timeout
        self._journal = journal or (lambda entry: None)

    def _send(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": f"Basic {self._auth}", "Accept": "application/json", "Content-Type": "application/json"})
        try:
            with self._open(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise JiraError(f"{method} {path}: HTTP {exc.code} {exc.read()[:300].decode(errors='replace')}",
                            status=exc.code) from exc
        except urllib.error.URLError as exc:
            raise JiraError(f"{method} {path}: no se pudo conectar ({exc.reason})") from exc
        return json.loads(raw) if raw else {}

    def search_label(self, label: str) -> List[Dict[str, Optional[str]]]:
        if not _LABEL.fullmatch(label):
            raise JiraError(f"label inválido {label!r}")
        body: dict = {"jql": f'labels = "{label}" ORDER BY key', "fields": ["summary", "parent"], "maxResults": 100}
        found: List[Dict[str, Optional[str]]] = []
        while True:
            page = self._send("POST", "/rest/api/3/search/jql", body)
            for issue in page.get("issues", []):
                fields = issue.get("fields") or {}
                found.append({"key": issue["key"], "summary": fields.get("summary"),
                              "parent": (fields.get("parent") or {}).get("key")})
            token = page.get("nextPageToken")
            if not token:
                return found
            body = dict(body, nextPageToken=token)

    def get_brief(self, key: str) -> Optional[Dict[str, Optional[str]]]:
        check_key(key)
        try:
            issue = self._send("GET", f"/rest/api/2/issue/{key}?fields=summary,parent")
        except JiraError as exc:
            if exc.status == 404:
                return None
            raise
        fields = issue.get("fields") or {}
        return {"key": issue.get("key", key), "summary": fields.get("summary"),
                "parent": (fields.get("parent") or {}).get("key")}

    def create(self, fields: dict) -> str:
        key = self._send("POST", "/rest/api/2/issue", {"fields": fields}).get("key")
        if not key:
            raise JiraError("Jira respondió el alta sin clave de issue")
        self._journal({"action": "create", "key": key, "fields": fields})
        return key

    def link(self, inward: str, outward: str, link_type: str) -> None:
        check_key(inward)
        check_key(outward)
        self._send("POST", "/rest/api/2/issueLink", {"type": {"name": link_type}, "inwardIssue": {"key": inward},
                                                     "outwardIssue": {"key": outward}})
        self._journal({"action": "link", "inward": inward, "outward": outward, "type": link_type})

    def find_user(self, email: str) -> str:
        users = self._send("GET", f"/rest/api/3/user/search?query={urllib.parse.quote(email)}")
        users = users if isinstance(users, list) else []
        exact = [u for u in users if (u.get("emailAddress") or "").lower() == email.lower()]
        if len(exact) == 1:
            return exact[0]["accountId"]
        if not users:
            raise JiraError(f"no se encontró a {email} en Jira: pedir que lo den de alta como cliente del Service "
                            "Desk y volver a correr")
        if len(users) == 1 and not users[0].get("emailAddress"):
            return users[0]["accountId"]  # the site hides emails: a single hit is the only safe match
        raise JiraError(f"el email {email} es ambiguo en Jira ({len(users)} usuarios): resolverlo a mano")

    def create_request(self, service_desk_id: str, request_type_id: str, summary: str, description: str,
                       on_behalf_of: str = "") -> str:
        body = {"serviceDeskId": service_desk_id, "requestTypeId": request_type_id,
                "requestFieldValues": {"summary": summary, "description": description}}
        if on_behalf_of:
            body["raiseOnBehalfOf"] = on_behalf_of
        key = self._send("POST", "/rest/servicedeskapi/request", body).get("issueKey")
        if not key:
            raise JiraError("JSM respondió el alta sin clave de pedido")
        self._journal({"action": "jsm-request", "key": key, "summary": summary})
        return key

    def add_participants(self, key: str, account_ids: List[str]) -> None:
        check_key(key)
        self._send("POST", f"/rest/servicedeskapi/request/{key}/participant", {"accountIds": account_ids})
        self._journal({"action": "jsm-participants", "key": key, "accountIds": account_ids})

    def add_labels(self, key: str, labels: List[str]) -> None:
        check_key(key)
        for label in labels:
            if not _LABEL.fullmatch(label):
                raise JiraError(f"label inválido {label!r}")
        self._send("PUT", f"/rest/api/2/issue/{key}", {"update": {"labels": [{"add": label} for label in labels]}})
        self._journal({"action": "labels", "key": key, "labels": labels})

    def comment(self, key: str, body: str, public: bool) -> None:
        check_key(key)
        self._send("POST", f"/rest/servicedeskapi/request/{key}/comment", {"body": body, "public": public})
        self._journal({"action": "jsm-comment", "key": key, "public": public, "body": body})
```

- [ ] **Step 5: Correr y verificar que pasan**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add arqlib/journal.py arqlib/jira.py tests/test_journal.py tests/test_jira.py
git commit -m "feat: add stdlib Jira and JSM client with write journal"
```

---

### Task 10: Aplicación idempotente y preview HTML

**Files:**
- Create: `arqlib/apply.py`, `arqlib/preview.py`, `tests/test_apply.py`, `tests/test_preview.py`
- Modify: `tests/helpers.py` (agregar `FakeJira`)

**Interfaces:**
- Consumes: `structure.build_plan` (Task 8), interfaz de `Jira` (Task 9).
- Produces:
  - `apply.known_from_journal(entries: List[dict], label: str, pry: str) -> Tuple[List[dict], List[str]]` →
    `(issues {"key","summary","parent"} creados con ese label, claves JSM creadas para ese PRY)`.
  - `apply.apply_plan(plan: dict, client, project: str, issue_types: Dict[str, str],
    known: Sequence[dict] = ()) -> Dict[str, object]` → `{"epica": str, "created": List[str], "reused": List[str]}`.
  - `apply.apply_followups(follow: dict, label: str, client, project: str, issue_types: Dict[str, str],
    known: Sequence[dict] = ()) -> Dict[str, object]` → `{"created": List[str], "reused": List[str]}`.
  - `apply.ensure_request(meta: Dict[str, str], client, config: dict, description: str, labels: List[str],
    on_created: Callable[[str], None], on_ready: Callable[[], None], known_jsm: Sequence[str] = ())
    -> Tuple[str, bool]` → `(clave_jsm, creado)`.
  - `preview.render_html(plan: dict, meta: Dict[str, str]) -> str`.
  - `tests.helpers.FakeJira(project="ARQ", fail_on_create: Optional[int] = None)` con la misma interfaz que `Jira`
    y los atributos `issues`, `links`, `comments`, `requests`, `participants`, `users` (email → accountId),
    `hidden` (claves que la búsqueda todavía no devuelve, como la consistencia eventual de `search/jql`) y
    `fail_link` (el link lanza `JiraError`).

**Idempotencia, en tres capas:** (1) búsqueda por label `pry:`; (2) las claves que el journal registra y la búsqueda
todavía no devuelve se confirman con `get_brief` (la búsqueda de Jira Cloud es eventualmente consistente);
(3) en JSM, `jsm` se guarda apenas existe el pedido y `jsm_listo=si` recién cuando tiene labels, participantes y link.
Un re-run con `jsm` y sin `jsm_listo` completa lo que falta. Supuesto a verificar en la primera corrida real: repetir
`add_labels` (operación `add`), `add_participants` y un link idéntico no duplica nada en Jira.

- [ ] **Step 1: Agregar `FakeJira` a `tests/helpers.py`**

Agregar al final de `tests/helpers.py`:
```python
from typing import Dict, List, Optional, Set  # noqa: E402

from arqlib.jira import JiraError  # noqa: E402

USERS = {"requester@example.com": "acc-pablo", "reviewer@example.com": "acc-felipe"}


class FailingJira(RuntimeError):
    pass


class FakeJira:
    """In-memory Jira + JSM with the same surface as arqlib.jira.Jira."""

    def __init__(self, project: str = "ARQ", fail_on_create: Optional[int] = None):
        self.project = project
        self.fail_on_create = fail_on_create  # the Nth create (1-based) raises, like a rejected issue
        self.creates = 0
        self.seq = 1
        self.issues: Dict[str, dict] = {}
        self.links: List[tuple] = []
        self.comments: List[tuple] = []
        self.requests: List[str] = []
        self.participants: List[tuple] = []
        self.users: Dict[str, str] = dict(USERS)
        self.hidden: Set[str] = set()  # created but not yet visible to search (eventual consistency)
        self.fail_link = False

    def search_label(self, label: str) -> List[dict]:
        return [{"key": k, "summary": i["summary"], "parent": i["parent"]}
                for k, i in self.issues.items() if label in i["labels"] and k not in self.hidden]

    def get_brief(self, key: str) -> Optional[dict]:
        issue = self.issues.get(key)
        return {"key": key, "summary": issue["summary"], "parent": issue["parent"]} if issue else None

    def create(self, fields: dict) -> str:
        self.creates += 1
        if self.fail_on_create is not None and self.creates == self.fail_on_create:
            raise FailingJira(f"HTTP 400 en el alta #{self.creates}")
        key = f"{self.project}-{self.seq}"
        self.seq += 1
        self.issues[key] = {"summary": fields["summary"], "labels": list(fields.get("labels", [])),
                            "type": fields["issuetype"]["name"], "parent": (fields.get("parent") or {}).get("key")}
        return key

    def link(self, inward: str, outward: str, link_type: str) -> None:
        if self.fail_link:
            raise JiraError("POST /rest/api/2/issueLink: HTTP 404")
        if (inward, outward, link_type) not in self.links:
            self.links.append((inward, outward, link_type))

    def find_user(self, email: str) -> str:
        if email not in self.users:
            raise JiraError(f"no se encontró a {email} en Jira: pedir que lo den de alta como cliente del Service Desk")
        return self.users[email]

    def create_request(self, service_desk_id: str, request_type_id: str, summary: str, description: str,
                       on_behalf_of: str = "") -> str:
        key = f"JSM-{len(self.requests) + 1}"
        self.requests.append(key)
        self.issues[key] = {"summary": summary, "labels": [], "type": "request", "parent": None,
                            "reporter": on_behalf_of}
        return key

    def add_participants(self, key: str, account_ids: List[str]) -> None:
        self.participants += [(key, a) for a in account_ids if (key, a) not in self.participants]

    def add_labels(self, key: str, labels: List[str]) -> None:
        current = self.issues[key]["labels"]
        current += [label for label in labels if label not in current]

    def comment(self, key: str, body: str, public: bool) -> None:
        self.comments.append((key, body, public))
```

- [ ] **Step 2: Escribir los tests que fallan**

`tests/test_apply.py`:
```python
from __future__ import annotations

import unittest

import helpers
from arqlib.apply import apply_followups, apply_plan, ensure_request, known_from_journal
from arqlib.config import DEFAULT_CONFIG
from arqlib.jira import JiraError
from arqlib.structure import build_plan, followup_plan

TYPES = DEFAULT_CONFIG["issue_types"]


def plan(nivel: str = "simple") -> dict:
    return build_plan({"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": nivel})


class ApplyTest(unittest.TestCase):
    def test_creates_epic_task_and_subtasks_with_parents(self):
        jira = helpers.FakeJira()
        result = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual(result["epica"], "ARQ-1")
        self.assertEqual(len(result["created"]), 7)  # épica + task + 5 sub-tasks
        self.assertEqual(jira.issues["ARQ-2"]["parent"], "ARQ-1")
        self.assertEqual({jira.issues[k]["parent"] for k in ("ARQ-3", "ARQ-7")}, {"ARQ-2"})
        self.assertEqual(jira.issues["ARQ-3"]["type"], "Subtask")

    def test_rerun_is_idempotent(self):
        jira = helpers.FakeJira()
        apply_plan(plan(), jira, "ARQ", TYPES)
        again = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual((again["created"], len(again["reused"])), ([], 7))
        self.assertEqual(len(jira.issues), 7)

    def test_resumes_after_partial_failure_without_duplicates(self):
        jira = helpers.FakeJira(fail_on_create=4)
        with self.assertRaises(helpers.FailingJira):
            apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual(len(jira.issues), 3)
        jira.fail_on_create = None
        result = apply_plan(plan(), jira, "ARQ", TYPES)
        self.assertEqual((len(result["reused"]), len(result["created"])), (3, 4))
        self.assertEqual(len(jira.issues), 7)

    def test_complejo_creates_epic_three_stories_and_their_subtasks(self):
        jira = helpers.FakeJira()
        apply_plan(plan("complejo"), jira, "ARQ", TYPES)
        self.assertEqual(len(jira.issues), 1 + 3 + 8)
        self.assertEqual(sum(1 for i in jira.issues.values() if i["type"] == "Story"), 3)

    def test_journal_covers_search_lag(self):
        jira = helpers.FakeJira(fail_on_create=4)
        with self.assertRaises(helpers.FailingJira):
            apply_plan(plan(), jira, "ARQ", TYPES)
        jira.fail_on_create = None
        jira.hidden = set(jira.issues)  # la búsqueda todavía no ve lo recién creado
        known = [{"key": k, "summary": i["summary"], "parent": i["parent"]} for k, i in jira.issues.items()]
        result = apply_plan(plan(), jira, "ARQ", TYPES, known=known)
        self.assertEqual((len(result["reused"]), len(result["created"])), (3, 4))
        self.assertEqual(len(jira.issues), 7)

    def test_journal_entry_for_a_deleted_issue_is_ignored(self):
        jira = helpers.FakeJira()
        known = [{"key": "ARQ-99", "summary": "[PRY-2026-0028] PoC", "parent": None}]
        self.assertEqual(apply_plan(plan(), jira, "ARQ", TYPES, known=known)["epica"], "ARQ-1")

    def test_known_from_journal(self):
        entries = [
            {"action": "create", "key": "ARQ-1", "fields": {"summary": "E", "labels": ["pry:2026-0028"]}},
            {"action": "create", "key": "ARQ-2", "fields": {"summary": "T", "labels": ["pry:2026-0028"],
                                                            "parent": {"key": "ARQ-1"}}},
            {"action": "create", "key": "ARQ-3", "fields": {"summary": "otro", "labels": ["pry:2026-0001"]}},
            {"action": "jsm-request", "key": "SD-4", "summary": "PRY-2026-0028 · PoC"},
            {"action": "jsm-request", "key": "SD-5", "summary": "PRY-2026-0001 · otro"},
        ]
        issues, jsm = known_from_journal(entries, "pry:2026-0028", "PRY-2026-0028")
        self.assertEqual(issues, [{"key": "ARQ-1", "summary": "E", "parent": None},
                                  {"key": "ARQ-2", "summary": "T", "parent": "ARQ-1"}])
        self.assertEqual(jsm, ["SD-4"])

    def test_followups_hang_from_the_review_task_and_are_idempotent(self):
        jira = helpers.FakeJira()
        meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": "simple"}
        apply_plan(plan(), jira, "ARQ", TYPES)
        follow = followup_plan(meta, ["Apagado fuera de horario"])
        first = apply_followups(follow, "pry:2026-0028", jira, "ARQ", TYPES)
        again = apply_followups(follow, "pry:2026-0028", jira, "ARQ", TYPES)
        [key] = first["created"]
        self.assertEqual(jira.issues[key]["parent"], "ARQ-2")  # la task "Revisión PRY-2026-0028"
        self.assertEqual(again["created"], [])

    def test_followups_need_the_epic_structure(self):
        follow = followup_plan({"pry": "PRY-2026-0028", "nivel": "simple"}, ["c"])
        with self.assertRaisesRegex(ValueError, "arq jira"):
            apply_followups(follow, "pry:2026-0028", helpers.FakeJira(), "ARQ", TYPES)

    def test_same_subtask_summary_under_different_parents_is_not_confused(self):
        jira = helpers.FakeJira()
        sub = {"summary": "Revisión y firma", "labels": ["pry:2026-0028"], "description": "d"}
        custom = {"epic": {"summary": "E", "labels": ["pry:2026-0028"], "description": "d"},
                  "items": [{"type": "story", "summary": s, "labels": ["pry:2026-0028"], "description": "d",
                             "subtasks": [dict(sub)]} for s in ("A", "B")]}
        apply_plan(custom, jira, "ARQ", TYPES)
        again = apply_plan(custom, jira, "ARQ", TYPES)
        self.assertEqual(len(jira.issues), 5)  # épica + 2 stories + 2 sub-tasks con el mismo nombre
        self.assertEqual(again["created"], [])


LABELS = ["pry:2026-0028", "nivel:simple"]
CONFIG = dict(DEFAULT_CONFIG, jsm_project="JSM", jsm_service_desk_id="3", jsm_request_type_id="41")


def request_meta(**extra: str) -> dict:
    meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "epica": "ARQ-1", "jsm": "", "jsm_listo": "",
            "contacto": "requester@example.com", "head": "reviewer@example.com"}
    meta.update(extra)
    return meta


class EnsureRequestTest(unittest.TestCase):
    def call(self, jira, meta, known_jsm=()):
        saved, ready = [], []
        result = ensure_request(meta, jira, CONFIG, "desc", LABELS, saved.append, lambda: ready.append(True),
                                known_jsm=known_jsm)
        return result, saved, ready

    def test_creates_on_behalf_of_requester_with_labels_head_and_link(self):
        jira = helpers.FakeJira()
        (key, created), saved, ready = self.call(jira, request_meta())
        self.assertEqual((key, created, saved, ready), ("JSM-1", True, ["JSM-1"], [True]))
        self.assertEqual(jira.issues["JSM-1"]["reporter"], "acc-pablo")
        self.assertEqual(jira.issues["JSM-1"]["labels"], LABELS)
        self.assertEqual(jira.participants, [("JSM-1", "acc-felipe")])
        self.assertEqual(jira.links, [("JSM-1", "ARQ-1", "Relates")])

    def test_unknown_requester_creates_nothing(self):
        jira = helpers.FakeJira()
        with self.assertRaisesRegex(JiraError, "cliente del Service Desk"):
            self.call(jira, request_meta(contacto="user@example.com"))
        self.assertEqual(jira.requests, [])

    def test_ready_request_is_skipped(self):
        jira = helpers.FakeJira()
        (key, created), saved, ready = self.call(jira, request_meta(jsm="JSM-9", jsm_listo="si"))
        self.assertEqual((key, created, jira.requests, saved, ready), ("JSM-9", False, [], [], []))

    def test_rerun_after_link_failure_finishes_the_link(self):
        jira = helpers.FakeJira()
        jira.fail_link = True
        meta = request_meta()
        with self.assertRaises(JiraError):
            self.call(jira, meta)
        jira.fail_link = False
        (key, created), _, ready = self.call(jira, request_meta(jsm="JSM-1"))
        self.assertEqual((key, created, ready, jira.requests), ("JSM-1", False, [True], ["JSM-1"]))
        self.assertEqual(jira.links, [("JSM-1", "ARQ-1", "Relates")])

    def test_existing_request_found_by_label_is_not_duplicated(self):
        jira = helpers.FakeJira(project="JSM")
        jira.create_request("3", "41", "PRY-2026-0028 · PoC", "d")
        jira.add_labels("JSM-1", LABELS)
        (key, created), saved, _ = self.call(jira, request_meta())
        self.assertEqual((key, created, saved, jira.requests), ("JSM-1", False, ["JSM-1"], ["JSM-1"]))

    def test_existing_request_from_journal_covers_search_lag(self):
        jira = helpers.FakeJira()
        jira.create_request("3", "41", "PRY-2026-0028 · PoC", "d")  # creado, pero sin labels todavía
        (key, created), _, _ = self.call(jira, request_meta(), known_jsm=["JSM-1"])
        self.assertEqual((key, created, jira.requests), ("JSM-1", False, ["JSM-1"]))

    def test_without_head_there_are_no_participants(self):
        jira = helpers.FakeJira()
        self.call(jira, request_meta(head=""))
        self.assertEqual(jira.participants, [])


if __name__ == "__main__":
    unittest.main()
```

`tests/test_preview.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.preview import render_html
from arqlib.structure import build_plan


class PreviewTest(unittest.TestCase):
    def test_lists_every_issue_and_labels(self):
        meta = {"pry": "PRY-2026-0028", "nombre": "PoC", "nivel": "simple"}
        html = render_html(build_plan(meta), meta)
        self.assertIn("[PRY-2026-0028] PoC", html)
        self.assertIn("Publicar devolución", html)
        self.assertIn("track:coordinacion", html)
        self.assertTrue(html.startswith("<!doctype html>"))

    def test_escapes_user_text(self):
        meta = {"pry": "PRY-2026-0028", "nombre": "<script>alert(1)</script>", "nivel": "simple"}
        html = render_html(build_plan(meta), meta)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Correr y verificar que fallan**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.apply'` y `'arqlib.preview'`

- [ ] **Step 4: Implementar `apply.py`**

`arqlib/apply.py`:
```python
"""Apply a structure plan to Jira idempotently.

Issues are matched by (summary, parent) among (1) a search by the pry: label and (2) the keys the journal recorded,
confirmed one by one, because Jira Cloud's search/jql is eventually consistent and may miss what was just created.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple


class ApplyError(ValueError):
    pass


def known_from_journal(entries: List[dict], label: str, pry: str) -> Tuple[List[dict], List[str]]:
    issues: List[dict] = []
    jsm: List[str] = []
    for entry in entries:
        fields = entry.get("fields") or {}
        if entry.get("action") == "create" and label in (fields.get("labels") or []):
            issues.append({"key": entry.get("key"), "summary": fields.get("summary"),
                           "parent": (fields.get("parent") or {}).get("key")})
        elif entry.get("action") == "jsm-request" and str(entry.get("summary", "")).startswith(f"{pry} "):
            jsm.append(entry.get("key"))
    return issues, jsm


def _index(client, label: str, known: Sequence[dict]) -> Dict[Tuple[str, Optional[str]], str]:
    found = client.search_label(label)
    seen = {issue["key"] for issue in found}
    for entry in known:
        if entry.get("key") and entry["key"] not in seen:
            brief = client.get_brief(entry["key"])
            if brief is not None:
                found.append(brief)
                seen.add(brief["key"])
    return {(issue["summary"], issue["parent"]): issue["key"] for issue in found}


def _fields(project: str, issue_type: str, node: dict, parent: Optional[str]) -> dict:
    fields = {"project": {"key": project}, "issuetype": {"name": issue_type}, "summary": node["summary"],
              "description": node["description"], "labels": node["labels"]}
    if parent:
        fields["parent"] = {"key": parent}
    return fields


class _Ensurer:
    def __init__(self, client, project: str, existing: Dict[Tuple[str, Optional[str]], str]):
        self.client, self.project, self.existing = client, project, existing
        self.created: List[str] = []
        self.reused: List[str] = []

    def __call__(self, node: dict, issue_type: str, parent: Optional[str]) -> str:
        key = self.existing.get((node["summary"], parent))
        if key:
            self.reused.append(key)
            return key
        key = self.client.create(_fields(self.project, issue_type, node, parent))
        self.existing[(node["summary"], parent)] = key
        self.created.append(key)
        return key


def apply_plan(plan: dict, client, project: str, issue_types: Dict[str, str],
               known: Sequence[dict] = ()) -> Dict[str, object]:
    ensure = _Ensurer(client, project, _index(client, plan["epic"]["labels"][0], known))
    epic = ensure(plan["epic"], issue_types["epic"], None)
    for item in plan["items"]:
        item_key = ensure(item, issue_types[item["type"]], epic)
        for sub in item["subtasks"]:
            ensure(sub, issue_types["subtask"], item_key)
    return {"epica": epic, "created": ensure.created, "reused": ensure.reused}


def apply_followups(follow: dict, label: str, client, project: str, issue_types: Dict[str, str],
                    known: Sequence[dict] = ()) -> Dict[str, object]:
    existing = _index(client, label, known)
    parents = [key for (summary, _), key in existing.items() if summary == follow["parent_summary"]]
    if not parents:
        raise ApplyError(f"no existe {follow['parent_summary']!r} en Jira: correr `arq jira` con --apply primero")
    ensure = _Ensurer(client, project, existing)
    for sub in follow["subtasks"]:
        ensure(sub, issue_types["subtask"], parents[0])
    return {"created": ensure.created, "reused": ensure.reused}


def _existing_request(client, config: dict, label: str, known_jsm: Sequence[str]) -> Optional[str]:
    prefix = f"{config['jsm_project']}-"
    for issue in client.search_label(label):
        if issue["key"].startswith(prefix):
            return issue["key"]
    for key in known_jsm:
        if key and client.get_brief(key) is not None:
            return key
    return None


def ensure_request(meta: Dict[str, str], client, config: dict, description: str, labels: List[str],
                   on_created: Callable[[str], None], on_ready: Callable[[], None],
                   known_jsm: Sequence[str] = ()) -> Tuple[str, bool]:
    """Create (or find) the JSM request on behalf of the requester, then label, add the head and link it.

    `on_created` runs as soon as the key is known, so a later failure never loses it; `on_ready` runs only when every
    step is done. A re-run with a key but not ready repeats the remaining idempotent steps.
    """
    if meta.get("jsm") and meta.get("jsm_listo"):
        return meta["jsm"], False
    key = meta.get("jsm") or _existing_request(client, config, labels[0], known_jsm)
    created = False
    if not key:
        requester = client.find_user(meta["contacto"])  # before creating: never raise a ticket on someone else's behalf
        key = client.create_request(str(config["jsm_service_desk_id"]), str(config["jsm_request_type_id"]),
                                    f"{meta['pry']} · {meta.get('nombre', '')}", description, on_behalf_of=requester)
        created = True
    on_created(key)
    client.add_labels(key, labels)
    if meta.get("head"):
        client.add_participants(key, [client.find_user(meta["head"])])
    client.link(key, meta["epica"], config["link_type"])
    on_ready()
    return key, created
```

- [ ] **Step 5: Implementar `preview.py`**

`arqlib/preview.py`:
```python
"""Dry-run preview: a self-contained HTML tree of what `arq jira --apply` would create."""
from __future__ import annotations

from html import escape
from typing import Dict


def _li(node: dict, kind: str, children: str = "") -> str:
    labels = " ".join(f'<span class="l">{escape(label)}</span>' for label in node["labels"])
    return (f'<li><span class="k">{escape(kind)}</span> {escape(node["summary"])} {labels}'
            f'<div class="d">{escape(node["description"])}</div>{children}</li>')


def render_html(plan: dict, meta: Dict[str, str]) -> str:
    items = ""
    for item in plan["items"]:
        subs = "".join(_li(sub, "sub-task") for sub in item["subtasks"])
        items += _li(item, item["type"], f"<ul>{subs}</ul>")
    tree = _li(plan["epic"], "épica", f"<ul>{items}</ul>")
    title = escape(f"{meta.get('pry', '')} · vista previa")
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#fff;--fg:#172B4D;--muted:#626F86;--chip:#E9F2FF}}
@media (prefers-color-scheme: dark){{:root{{--bg:#1D2125;--fg:#DEE4EA;--muted:#9FADBC;--chip:#1C2B41}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;margin:0;padding:16px}}
ul{{list-style:none;padding-left:20px}} li{{margin:6px 0}}
.k{{font-weight:600;text-transform:uppercase;font-size:11px;color:var(--muted)}}
.l{{background:var(--chip);border-radius:3px;padding:0 6px;font-size:12px;margin-left:4px}}
.d{{color:var(--muted);font-size:13px}}
</style></head><body>
<h1>{title}</h1>
<p>Dry run: nada de esto existe todavía en Jira. Para crearlo, el usuario corre <code>arq jira {escape(meta.get('pry', ''))} --apply</code>.</p>
<ul>{tree}</ul>
</body></html>
"""
```

- [ ] **Step 6: Correr y verificar que pasan**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add arqlib/apply.py arqlib/preview.py tests/helpers.py tests/test_apply.py tests/test_preview.py
git commit -m "feat: apply Jira plan idempotently and render dry-run preview"
```

---

### Task 11: Campos que escribe el architect

**Files:**
- Create: `arqlib/fields.py`, `tests/test_fields.py`

**Interfaces:**
- Consumes: `inputs.input_ids` (Task 7), `frontmatter.as_list` (Task 1).
- Produces: `fields.COMPONENTES`, `fields.SENALES`, `fields.VEREDICTOS: Tuple[str, ...]`, `fields.EDITABLE`,
  `fields.parse_updates(pairs: List[str]) -> Dict[str, str]`,
  `fields.apply_updates(meta: Dict[str, str], updates: Dict[str, str]) -> Dict[str, str]` (devuelve copia),
  `fields.FieldsError(ValueError)`.

Esta tarea aplica la matriz de veredicto del spec (§7): **no hay veredicto con input faltante**.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_fields.py`:
```python
from __future__ import annotations

import unittest

import helpers  # noqa: F401
from arqlib.fields import FieldsError, apply_updates, parse_updates


def meta(**extra: str) -> dict:
    base = {"pry": "PRY-2026-0028", "nivel": "simple", "faltantes": "", "componente_debil": "", "senales": "",
            "veredicto": "", "firmante": "", "estado": "en-analisis"}
    base.update(extra)
    return base


class FieldsTest(unittest.TestCase):
    def test_parse_updates(self):
        self.assertEqual(parse_updates(["senales=finops, seguridad", "veredicto="]),
                         {"senales": "finops, seguridad", "veredicto": ""})
        with self.assertRaisesRegex(FieldsError, "campo=valor"):
            parse_updates(["senales"])

    def test_normalizes_lists(self):
        new = apply_updates(meta(), {"faltantes": " hipotesis_medible,,costo_estimado ", "senales": "finops"})
        self.assertEqual((new["faltantes"], new["senales"]), ("hipotesis_medible, costo_estimado", "finops"))

    def test_rejects_unknown_input_id_for_level(self):
        with self.assertRaisesRegex(FieldsError, "rollback"):
            apply_updates(meta(), {"faltantes": "rollback"})  # rollback es solo de nivel complejo

    def test_requires_triage_before_faltantes(self):
        with self.assertRaisesRegex(FieldsError, "arq triage"):
            apply_updates(meta(nivel=""), {"faltantes": "problema"})

    def test_rejects_non_editable_field(self):
        with self.assertRaisesRegex(FieldsError, "estado.*arq state"):
            apply_updates(meta(), {"estado": "cerrado"})

    def test_rejects_unknown_signal_component_and_verdict(self):
        for updates in ({"senales": "legales"}, {"componente_debil": "frontend"}, {"veredicto": "quizas"}):
            with self.assertRaises(FieldsError):
                apply_updates(meta(), updates)

    def test_no_verdict_with_missing_input(self):
        with self.assertRaisesRegex(FieldsError, "input faltante"):
            apply_updates(meta(faltantes="costo_estimado"), {"veredicto": "aprobar"})
        self.assertEqual(apply_updates(meta(), {"veredicto": "aprobar-con-condiciones"})["veredicto"],
                         "aprobar-con-condiciones")

    def test_returns_copy(self):
        original = meta()
        apply_updates(original, {"senales": "finops"})
        self.assertEqual(original["senales"], "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.fields'`

- [ ] **Step 3: Implementar**

`arqlib/fields.py`:
```python
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
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add arqlib/fields.py tests/test_fields.py
git commit -m "feat: validate architect-written fields and verdict matrix"
```

---

### Task 12: Evaluación y golden cases

**Files:**
- Create: `arqlib/evaluate.py`, `tests/test_golden.py`, `tests/golden/PRY-2026-0028/input.md`,
  `tests/golden/PRY-2026-0028/expected.json`, `tests/golden/PRY-2026-0028/reference.md`,
  `tests/golden/PRY-2026-0026/input.md`, `tests/golden/PRY-2026-0026/expected.json`

**Interfaces:**
- Consumes: `frontmatter.parse/as_list`, `fields.COMPONENTES/SENALES`, `inputs.all_ids`, `constraints.parse`.
- Produces: `evaluate.evaluate(expected: dict, meta: Dict[str, str], body: str) -> List[str]` (fallas; vacía = ok),
  `evaluate.evaluate_files(golden_dir: Path, review_file: Path) -> List[str]`.

`expected.json` admite: `nivel`, `estado`, `componente_debil` (igualdad), `debe_pedir` (⊂ `faltantes`),
`debe_citar` (cada `[ID]` aparece en el cuerpo), `senales` (⊂ `senales`), `sin_veredicto` (`veredicto` vacío).
`reference.md` es una salida ideal escrita a mano: sirve de ejemplo para el architect y de test de la rúbrica. El
`reference.md` de PRY-2026-0026 se agrega cuando se tunee ese caso con una corrida real.

- [ ] **Step 1: Crear los golden cases**

`tests/golden/PRY-2026-0028/input.md`:
```markdown
- Tipo: Interno Plataforma
- Nombre: PoC modelos IA Locales
- Descripción: Habilitar una instancia G6e.xlarge L40S de 44 GiB de VRAM
- Empresa / área: CROSS
- Tipo de trabajo: Optimización de costos (FinOps)
- Fecha deseada: 2026-10-13 (Sí, es negociable)
- Justificación fecha: No hay urgencia, es mejora deseable
- Impacto: Únicamente se aplazan los tiempos de prueba, pero no pone en criticidad ningún proyecto
- Equipos involucrados: No, solo Plataforma
- Documentación: Google Doc (link)
- ¿Quién valida?: El head del área
- Entregable esperado: Un business case donde valide la hipótesis de valor: con modelos locales se logre reducir el costo de procesamiento frente a modelos SaaS
- Requisitos al cierre: Requiere documentación
- Problema / mejora: El incremento de costos en modelos SaaS, especialmente Cursor y GitHub Copilot, en la adopción de IA para los flujos de trabajo; se espera que el costo de máquinas virtuales reduzca el costo pagado por software as a service
- Es cross: Sí — SaaS
```

`tests/golden/PRY-2026-0028/expected.json`:
```json
{
  "nivel": "simple",
  "estado": "esperando-info",
  "debe_pedir": ["hipotesis_medible", "duracion_y_baja", "costo_estimado", "via_aprovisionamiento"],
  "debe_citar": ["C-PLAT-01"],
  "componente_debil": "costo",
  "senales": ["finops"],
  "sin_veredicto": true
}
```

`tests/golden/PRY-2026-0028/reference.md`:
```markdown
---
pry: PRY-2026-0028
nombre: PoC modelos IA Locales
contacto: requester@example.com
head: reviewer@example.com
estado: esperando-info
nivel: simple
epica: ARQ-1
jsm: JSM-1
jsm_listo: si
vence: 2026-10-21
firmante:
resultado:
faltantes: hipotesis_medible, duracion_y_baja, costo_estimado, via_aprovisionamiento, responsable
componente_debil: costo
senales: finops
veredicto:
---

## Pedido original

Habilitar una instancia G6e.xlarge L40S de 44 GiB de VRAM para validar que modelos locales reducen el costo frente a
Cursor y GitHub Copilot.

## Lo que entendimos

Plataforma quiere una GPU en AWS para correr modelos de IA propios y comparar su costo contra las licencias SaaS de
asistentes de código `[pedido]`.

## Input faltante

- `hipotesis_medible`: no hay métrica, valor actual ni umbral; "reducir el costo" no se puede refutar `[pedido]`.
- `duracion_y_baja`: no dice cuánto dura la PoC ni cuándo se da de baja la instancia `[pedido]`.
- `costo_estimado`: no hay costo mensual de la instancia ni del gasto SaaS actual `[pedido]`.
- `via_aprovisionamiento`: no dice si la instancia se crea desde platform `[C-PLAT-01]`.
- `responsable`: no hay responsable del recurso mientras exista `[pedido]`.

## Análisis preliminar (sin veredicto)

| Componente | Estado | Hallazgo |
|---|---|---|
| costo | débil | GPU dedicada sin horario ni fecha de baja; del orden de US$1.3k/mes si corre 24/7 `[verificar]` |
| aprovisionamiento | débil | Falta confirmar que pasa por platform `[C-PLAT-01]` |
| computo | ok | La L40S tiene 48 GB de VRAM, no 44 GiB `[verificar]` |

La hipótesis compara productos de IDE por asiento contra inferencia cruda: el business case tiene que medir
equivalencia funcional, no solo costo `[supuesto]`.

## Señales para otros sectores (sin veredicto)

- ⚠ FinOps podría observar: costo de una GPU encendida sin horario ni presupuesto con alerta, porque no hay fecha de
  baja `[pedido]`.
```

`tests/golden/PRY-2026-0026/input.md`:
```markdown
- Tipo: Empresas/Vertical del grupo
- Nombre: Product Brain
- Descripción: Migrar instancias de PB de las cuentas de uMarket a ACME Cross Domain + Habilitación de Bedrock en cuenta ACME Cross Domain
- Empresa / área: PDLC Tools
- Tipo de trabajo: Migración
- Fecha deseada: 2026-10-15 (No, es comprometida)
- Justificación fecha: Dependencia con otro proyecto
- Impacto: Demoras en la implementación del nuevo PDLC federado
- Equipos involucrados: Sí — Base de datos. En caso de demorar en la fecha, propongo migrar instancias apuntando al servicio de uMarket si es posible
- Documentación: diagrama .drawio en GitHub (acme-agent/docs/diagrams/all-diagrams.drawio)
- ¿Quién valida?: Líder del Squad
- Entregable esperado: Product Brain migrado a la cuenta destino + habilitación de Bedrock a nivel AWS
- Requisitos al cierre: No requiere nada adicional
- Comentario previo de Arquitectura: se generó una primera versión para la Hackathon y no hubo evaluación formal de ARQ
```

`tests/golden/PRY-2026-0026/expected.json`:
```json
{
  "nivel": "complejo",
  "estado": "esperando-info",
  "debe_pedir": ["diagrama_c4", "flujos_datos", "rollback", "dependencias"],
  "debe_citar": ["C-PLAT-01"],
  "componente_debil": "datos",
  "senales": ["seguridad", "cloud"],
  "sin_veredicto": true
}
```

- [ ] **Step 2: Escribir el test que falla**

`tests/test_golden.py`:
```python
from __future__ import annotations

import json
import unittest
from pathlib import Path

import helpers
from arqlib import frontmatter
from arqlib.constraints import parse
from arqlib.evaluate import evaluate, evaluate_files
from arqlib.fields import COMPONENTES, SENALES
from arqlib.inputs import all_ids
from arqlib.paths import CONTRACT

GOLDEN = helpers.ROOT / "tests" / "golden"
REF = GOLDEN / "PRY-2026-0028" / "reference.md"


def cases():
    return sorted(p for p in GOLDEN.iterdir() if p.is_dir())


class GoldenContractTest(unittest.TestCase):
    def test_every_case_is_consistent_with_the_contract(self):
        constraint_ids = {c.id for c in parse((CONTRACT / "constraints.md").read_text(encoding="utf-8"))}
        self.assertEqual([p.name for p in cases()], ["PRY-2026-0026", "PRY-2026-0028"])
        for case in cases():
            self.assertTrue((case / "input.md").read_text(encoding="utf-8").strip(), case.name)
            expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
            self.assertTrue(set(expected["debe_pedir"]) <= set(all_ids()), case.name)
            self.assertTrue(set(expected["debe_citar"]) <= constraint_ids, case.name)
            self.assertIn(expected["componente_debil"], COMPONENTES, case.name)
            self.assertTrue(set(expected["senales"]) <= set(SENALES), case.name)


class EvaluateTest(unittest.TestCase):
    def setUp(self):
        self.expected = json.loads((GOLDEN / "PRY-2026-0028" / "expected.json").read_text(encoding="utf-8"))
        self.meta, self.body = frontmatter.parse(REF.read_text(encoding="utf-8"))

    def test_reference_passes(self):
        self.assertEqual(evaluate(self.expected, self.meta, self.body), [])
        self.assertEqual(evaluate_files(GOLDEN / "PRY-2026-0028", REF), [])

    def test_verdict_with_missing_input_fails(self):
        self.meta["veredicto"] = "aprobar"
        self.assertEqual(evaluate(self.expected, self.meta, self.body),
                         ["no debe emitir veredicto con input faltante"])

    def test_missing_citation_and_request_fail(self):
        self.meta["faltantes"] = "hipotesis_medible"
        failures = evaluate(self.expected, self.meta, self.body.replace("[C-PLAT-01]", ""))
        self.assertIn("debe citar [C-PLAT-01]", failures)
        self.assertIn("debe pedir costo_estimado", failures)

    def test_wrong_level_and_missing_signal_fail(self):
        self.meta.update(nivel="complejo", senales="")
        failures = evaluate(self.expected, self.meta, self.body)
        self.assertIn("nivel: esperado 'simple', obtenido 'complejo'", failures)
        self.assertIn("debe señalar finops", failures)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.evaluate'`

- [ ] **Step 4: Implementar**

`arqlib/evaluate.py`:
```python
"""Golden-case rubric (spec §11): properties a review must have, never exact text."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from arqlib import frontmatter
from arqlib.frontmatter import as_list


def evaluate(expected: dict, meta: Dict[str, str], body: str) -> List[str]:
    failures: List[str] = []
    for key in ("nivel", "estado", "componente_debil"):
        if key in expected and meta.get(key, "") != expected[key]:
            failures.append(f"{key}: esperado {expected[key]!r}, obtenido {meta.get(key, '')!r}")
    faltantes = as_list(meta.get("faltantes", ""))
    failures += [f"debe pedir {item}" for item in expected.get("debe_pedir", []) if item not in faltantes]
    failures += [f"debe citar [{cid}]" for cid in expected.get("debe_citar", []) if f"[{cid}]" not in body]
    senales = as_list(meta.get("senales", ""))
    failures += [f"debe señalar {s}" for s in expected.get("senales", []) if s not in senales]
    if expected.get("sin_veredicto") and meta.get("veredicto"):
        failures.append("no debe emitir veredicto con input faltante")
    return failures


def evaluate_files(golden_dir: Path, review_file: Path) -> List[str]:
    expected = json.loads((golden_dir / "expected.json").read_text(encoding="utf-8"))
    meta, body = frontmatter.parse(review_file.read_text(encoding="utf-8"))
    return evaluate(expected, meta, body)
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add arqlib/evaluate.py tests/test_golden.py tests/golden
git commit -m "feat: add golden-case rubric with PRY-2026-0026 and PRY-2026-0028"
```

---

### Task 13: CLI `arq`

**Files:**
- Create: `arqlib/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `cli.main(argv: Optional[List[str]] = None, env: Optional[Mapping[str, str]] = None,
  cwd: Optional[str] = None, client_factory: Optional[Callable[[], object]] = None,
  today: Optional[date] = None) -> int`, `cli.build_parser() -> argparse.ArgumentParser`. Subcomandos: `init`,
  `path`, `new`, `show`, `triage`, `set`, `state`, `timebox`, `lint`, `jira`, `jsm`, `seguimiento`, `link`, `eval`.

Reglas que aplica el CLI (además de las de cada módulo):
- `triage` se puede repetir mientras el pedido no tenga épica; con épica, el nivel queda fijo.
- `jsm --public` exige `--template` (`jsm-pedido-info.md`, `jsm-devolucion.md` o `jsm-cierre.md`), que el texto siga
  esa plantilla (`matches_template`) y el estado que le corresponde: `esperando-info`, `publicado` y
  `propuesta-rechazo` respectivamente. Así una devolución nunca sale antes de la firma. `--internal` acepta texto libre.
- `seguimiento` crea una sub-task por condición, solo con `veredicto=aprobar-con-condiciones` y estado `publicado` o
  `cerrado`.
- `jira --apply` lee el journal para cubrir la demora de la búsqueda, y deja `jsm_listo=si` solo cuando el pedido JSM
  tiene labels, participantes y link. Si algo falla, el mismo comando completa lo que falta.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_cli.py`:
```python
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date

import helpers
from arqlib.cli import main
from arqlib.render import load_template, render
from arqlib.review import load

ALL_NO = ("multi_cuenta=no,migracion=no,fecha_comprometida=no,otros_equipos=no,"
          "datos_sensibles_o_ia=no,larga_o_productiva=no")
PRY = "PRY-2026-0028"
CONTACTO = "requester@example.com"


def run(repo, *argv, fake=None, env=None, today=date(2026, 10, 7)):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv), env=env if env is not None else {}, cwd=str(repo),
                    client_factory=(lambda: fake) if fake is not None else None, today=today)
    return code, out.getvalue(), err.getvalue()


def ready_repo():
    repo = helpers.make_repo()
    run(repo, "init")
    path = repo / ".arq" / "config.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(jsm_project="JSM", jsm_service_desk_id="3", jsm_request_type_id="41")
    path.write_text(json.dumps(data), encoding="utf-8")
    (repo / "pedido.txt").write_text("Habilitar una G6e.xlarge", encoding="utf-8")
    run(repo, "new", PRY, "--nombre", "PoC modelos IA Locales", "--pedido", str(repo / "pedido.txt"),
        "--contacto", CONTACTO, "--head", "reviewer@example.com")
    return repo


def opened_repo(fake):
    repo = ready_repo()
    run(repo, "triage", PRY, "--answers", ALL_NO)
    run(repo, "jira", PRY, "--apply", fake=fake)
    return repo


def write(repo, name, text):
    (repo / name).write_text(text, encoding="utf-8")
    return str(repo / name)


def pedido_info():
    return render(load_template("jsm-pedido-info.md"), {
        "contacto": "Juan Pablo", "pry": PRY, "nombre": "PoC", "faltantes": "- Fecha de baja",
        "motivo": "Sin fecha de baja no se puede estimar el costo.", "vence": "2026-10-21"})


class CliTest(unittest.TestCase):
    def test_simple_flow(self):
        repo, fake = ready_repo(), helpers.FakeJira()
        self.assertEqual(run(repo, "triage", PRY, "--answers", ALL_NO)[:2], (0, "nivel: simple\n"))

        code, out, _ = run(repo, "jira", PRY, "--html", str(repo / "vista.html"), fake=fake)
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertTrue((repo / "vista.html").exists())
        self.assertEqual(fake.issues, {})

        code, out, _ = run(repo, "jira", PRY, "--apply", fake=fake)
        self.assertEqual(code, 0)
        meta, _ = load(repo, PRY)
        self.assertEqual((meta["epica"], meta["jsm"], meta["jsm_listo"]), ("ARQ-1", "JSM-1", "si"))
        self.assertEqual(fake.issues["JSM-1"]["reporter"], "acc-pablo")
        self.assertEqual(fake.links, [("JSM-1", "ARQ-1", "Relates")])

        self.assertIn("vence: 2026-10-21 (en plazo)", run(repo, "timebox", PRY)[1])
        self.assertEqual(run(repo, "state", PRY, "--to", "esperando-info")[0], 0)
        self.assertEqual(run(repo, "state", PRY, "--to", "esperando-info")[0], 0)  # repetir no rompe
        self.assertEqual(run(repo, "set", PRY, "faltantes=costo_estimado", "senales=finops")[0], 0)

        code, _, err = run(repo, "set", PRY, "veredicto=aprobar")
        self.assertEqual(code, 1)
        self.assertIn("input faltante", err)

    def test_retriage_until_the_epic_exists(self):
        repo, fake = ready_repo(), helpers.FakeJira()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        code, out, _ = run(repo, "triage", PRY, "--answers", ALL_NO.replace("migracion=no", "migracion=si"))
        self.assertEqual((code, out), (0, "nivel: complejo\n"))
        run(repo, "jira", PRY, "--apply", fake=fake)
        code, _, err = run(repo, "triage", PRY, "--answers", ALL_NO)
        self.assertEqual(code, 1)
        self.assertIn("épica", err)

    def test_public_reply_needs_matching_template_and_state(self):
        fake = helpers.FakeJira()
        repo = opened_repo(fake)
        run(repo, "state", PRY, "--to", "esperando-info")
        info = write(repo, "info.md", pedido_info())

        code, _, err = run(repo, "jsm", PRY, "--file", info, "--public", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("--template", err)

        bad = write(repo, "bad.md", "Hola {{contacto}}")
        code, _, err = run(repo, "jsm", PRY, "--file", bad, "--public", "--template", "jsm-pedido-info.md", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("placeholders", err)

        free = write(repo, "free.md", "127.0.0.1 localhost")
        code, _, err = run(repo, "jsm", PRY, "--file", free, "--public", "--template", "jsm-pedido-info.md", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("no sigue la plantilla", err)

        devolucion = write(repo, "dev.md", render(load_template("jsm-devolucion.md"), {
            "contacto": "Juan Pablo", "pry": PRY, "nombre": "PoC", "veredicto": "Aprobado con condiciones",
            "resumen": "r", "recomendaciones": "- r", "condiciones": "- c", "senales": "- s", "link": "https://x"}))
        code, _, err = run(repo, "jsm", PRY, "--file", devolucion, "--public", "--template", "jsm-devolucion.md",
                           fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("se publica en estado publicado", err)  # una devolución nunca sale antes de la firma

        code, out, _ = run(repo, "jsm", PRY, "--file", info, "--public", "--template", "jsm-pedido-info.md", fake=fake)
        self.assertEqual((code, fake.comments), (0, []))
        self.assertIn("respuesta pública", out)
        run(repo, "jsm", PRY, "--file", info, "--public", "--template", "jsm-pedido-info.md", "--apply", fake=fake)
        run(repo, "jsm", PRY, "--file", free, "--internal", "--apply", fake=fake)
        self.assertEqual([c[2] for c in fake.comments], [True, False])

    def test_followups_only_for_published_conditional_approval(self):
        fake = helpers.FakeJira()
        repo = opened_repo(fake)
        code, _, err = run(repo, "seguimiento", PRY, "Apagado fuera de horario", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("aprobar-con-condiciones", err)

        run(repo, "state", PRY, "--to", "en-analisis")
        run(repo, "set", PRY, "veredicto=aprobar-con-condiciones")
        run(repo, "state", PRY, "--to", "en-firma")
        run(repo, "set", PRY, "firmante=edgardo.costilla")
        self.assertEqual(run(repo, "state", PRY, "--to", "publicado")[0], 0)

        code, out, _ = run(repo, "seguimiento", PRY, "Apagado fuera de horario", fake=fake)
        self.assertEqual(code, 0)
        self.assertIn("Condición: Apagado fuera de horario", out)
        before = len(fake.issues)
        run(repo, "seguimiento", PRY, "Apagado fuera de horario", "--apply", fake=fake)
        run(repo, "seguimiento", PRY, "Apagado fuera de horario", "--apply", fake=fake)
        self.assertEqual(len(fake.issues), before + 1)
        self.assertEqual(run(repo, "state", PRY, "--to", "cerrado", "--resultado", "aprobado")[0], 1)
        self.assertEqual(run(repo, "state", PRY, "--to", "cerrado", "--resultado", "condicionado")[0], 0)

    def test_bad_pry_never_touches_disk(self):
        repo = helpers.make_repo()
        run(repo, "init")
        code, _, err = run(repo, "new", "../../x", "--nombre", "x", "--pedido", "-", "--contacto", CONTACTO)
        self.assertEqual(code, 1)
        self.assertIn("PRY inválido", err)
        self.assertEqual(list((repo / "reviews").iterdir()), [])

    def test_missing_credentials(self):
        repo = ready_repo()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        code, _, err = run(repo, "jira", PRY, "--apply")
        self.assertEqual(code, 1)
        self.assertIn("JIRA_API_TOKEN", err)

    def test_link_failure_is_completed_by_rerunning(self):
        repo, fake = ready_repo(), helpers.FakeJira()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        fake.fail_link = True
        code, _, err = run(repo, "jira", PRY, "--apply", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("volver a correr", err)
        self.assertEqual((load(repo, PRY)[0]["jsm"], load(repo, PRY)[0]["jsm_listo"]), ("JSM-1", ""))
        fake.fail_link = False
        self.assertEqual(run(repo, "jira", PRY, "--apply", fake=fake)[0], 0)
        self.assertEqual(load(repo, PRY)[0]["jsm_listo"], "si")
        self.assertEqual(fake.requests, ["JSM-1"])

    def test_overdue_timebox_suggests_rejection_proposal(self):
        repo = ready_repo()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        run(repo, "timebox", PRY)
        run(repo, "state", PRY, "--to", "esperando-info")
        code, out, _ = run(repo, "timebox", PRY, today=date(2026, 10, 22))
        self.assertIn("vencido", out)
        self.assertIn(f"arq state {PRY} --to propuesta-rechazo", out)

    def test_lint(self):
        repo = helpers.make_repo()
        self.assertEqual(run(repo, "lint")[0], 0)
        (repo / "c.md").write_text("### C-X-01 · t\n- **Severidad:** urgente\n", encoding="utf-8")
        code, out, _ = run(repo, "lint", "--file", str(repo / "c.md"))
        self.assertEqual(code, 1)
        self.assertIn("severidad inválida", out)

    def test_link_validates_keys(self):
        code, _, err = run(ready_repo(), "link", "JSM-1", "../x")
        self.assertEqual(code, 1)
        self.assertIn("clave de Jira inválida", err)

    def test_usage_error_exits_2(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["inventado"])
        self.assertEqual(raised.exception.code, 2)

    def test_eval_reference(self):
        golden = helpers.ROOT / "tests" / "golden" / "PRY-2026-0028"
        code, out, _ = run(helpers.make_repo(), "eval", str(golden), str(golden / "reference.md"))
        self.assertEqual((code, out), (0, "ok: cumple la rúbrica\n"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `No module named 'arqlib.cli'`

- [ ] **Step 3: Implementar**

`arqlib/cli.py`:
```python
"""arq: CLI of arq-review. Domain errors print `error: ...` and exit 1; argparse usage errors exit 2."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Callable, List, Mapping, Optional

from arqlib import config as cfg
from arqlib import fields, review, state, triage
from arqlib.apply import apply_followups, apply_plan, ensure_request, known_from_journal
from arqlib.constraints import lint
from arqlib.evaluate import evaluate_files
from arqlib.jira import Jira, JiraError, check_key
from arqlib.journal import journal, read_entries
from arqlib.paths import CONTRACT
from arqlib.preview import render_html
from arqlib.render import assert_rendered, load_template, matches_template
from arqlib.structure import base_labels, build_plan, followup_plan
from arqlib.timebox import add_business_days, is_overdue

APPLY_HINT = ("dry run: no se escribió nada. Para ejecutarlo, el usuario corre el mismo comando con --apply "
              "(en Claude Code, con !).")
PUBLIC_TEMPLATES = {"jsm-pedido-info.md": "esperando-info", "jsm-devolucion.md": "publicado",
                    "jsm-cierre.md": "propuesta-rechazo"}


class Context:
    def __init__(self, repo: Path, env: Mapping[str, str], client_factory: Optional[Callable[[], object]],
                 today: date):
        self.repo, self.env, self.client_factory, self.today = repo, env, client_factory, today

    def client(self, command: str):
        if self.client_factory is not None:
            return self.client_factory()
        base, email, token = cfg.credentials(self.env)
        return Jira(base, email, token, journal=journal(self.repo, command))


def _init(ctx: Context, args) -> int:
    created = cfg.init_repo(ctx.repo)
    print("\n".join(f"creado {p}" for p in created) or "el repo ya estaba inicializado")
    return 0


def _path(ctx: Context, args) -> int:
    print(CONTRACT)
    return 0


def _new(ctx: Context, args) -> int:
    review.check_pry(args.pry)
    review.check_email(args.contacto)
    pedido = sys.stdin.read() if args.pedido == "-" else Path(args.pedido).read_text(encoding="utf-8")
    path = review.new_review(ctx.repo, args.pry, args.nombre, pedido, args.contacto, args.head or "")
    print(f"creado {path.relative_to(ctx.repo)} (estado: recibido)")
    return 0


def _show(ctx: Context, args) -> int:
    meta, _ = review.load(ctx.repo, args.pry)
    for key, value in meta.items():
        print(f"{key}: {value}")
    return 0


def _triage(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    if meta.get("epica"):
        raise ValueError(f"{args.pry} ya tiene épica ({meta['epica']}): el nivel no se puede cambiar")
    nivel = triage.classify(triage.parse_answers(args.answers))
    meta = state.transition(meta, "triado")
    meta["nivel"] = nivel
    review.save(ctx.repo, args.pry, meta, body)
    print(f"nivel: {nivel}")
    return 0


def _set(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    updates = fields.parse_updates(args.updates)
    review.save(ctx.repo, args.pry, fields.apply_updates(meta, updates), body)
    print("actualizado: " + ", ".join(updates))
    return 0


def _state(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    meta = state.transition(meta, args.to, args.resultado or "")
    review.save(ctx.repo, args.pry, meta, body)
    print(f"estado: {meta['estado']}")
    return 0


def _timebox(ctx: Context, args) -> int:
    today = date.fromisoformat(args.today) if args.today else ctx.today
    meta, body = review.load(ctx.repo, args.pry)
    if not meta.get("vence"):
        meta["vence"] = add_business_days(today, cfg.load_config(ctx.repo)["timebox_dias_habiles"]).isoformat()
        review.save(ctx.repo, args.pry, meta, body)
    overdue = is_overdue(meta["vence"], today)
    print(f"vence: {meta['vence']} ({'vencido' if overdue else 'en plazo'})")
    if overdue and meta.get("estado") == "esperando-info":
        print(f"siguiente paso: arq state {args.pry} --to propuesta-rechazo")
    return 0


def _lint(ctx: Context, args) -> int:
    path = Path(args.file) if args.file else CONTRACT / "constraints.md"
    errors = lint(path.read_text(encoding="utf-8"))
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"ok: {path}")
    return 0


def _print_plan(plan: dict) -> None:
    print(f"épica     {plan['epic']['summary']}  [{' '.join(plan['epic']['labels'])}]")
    for item in plan["items"]:
        print(f"  {item['type']:<8}{item['summary']}")
        for sub in item["subtasks"]:
            print(f"    sub-task {sub['summary']}  [{sub['labels'][-1]}]")


def _jira(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    config = cfg.load_config(ctx.repo, require_jsm=args.apply)
    plan = build_plan(meta, validacion=args.con_validacion)
    _print_plan(plan)
    if args.html:
        Path(args.html).write_text(render_html(plan, meta), encoding="utf-8")
        print(f"vista previa: {args.html}")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    client = ctx.client("jira")
    labels = base_labels(meta)
    known, known_jsm = known_from_journal(read_entries(ctx.repo), labels[0], meta["pry"])
    result = apply_plan(plan, client, config["jira_project"], config["issue_types"], known=known)
    meta["epica"] = result["epica"]
    review.save(ctx.repo, args.pry, meta, body)

    def on_created(key: str) -> None:
        meta["jsm"] = key
        review.save(ctx.repo, args.pry, meta, body)

    def on_ready() -> None:
        meta["jsm_listo"] = "si"
        review.save(ctx.repo, args.pry, meta, body)

    description = (f"Pedido {meta['pry']} ({meta.get('nombre', '')}). En este ticket conversamos con Arquitectura "
                   "hasta cerrar la revisión.")
    try:
        jsm, created = ensure_request(meta, client, config, description, labels, on_created, on_ready,
                                      known_jsm=known_jsm)
    except JiraError as exc:
        if meta.get("jsm"):
            raise JiraError(f"{exc}. El pedido {meta['jsm']} quedó creado: volver a correr "
                            f"`arq jira {args.pry} --apply` para completar labels, participantes y link") from exc
        raise
    print(f"épica: {result['epica']} (creados {len(result['created'])}, existentes {len(result['reused'])})")
    print(f"jsm: {jsm} ({'creado' if created else 'ya existía'}; labels, participantes y link al día)")
    return 0


def _jsm(ctx: Context, args) -> int:
    meta, _ = review.load(ctx.repo, args.pry)
    text = Path(args.file).read_text(encoding="utf-8").strip()
    assert_rendered(text)
    if args.public:
        if args.template not in PUBLIC_TEMPLATES:
            raise ValueError(f"una respuesta pública necesita --template ({', '.join(PUBLIC_TEMPLATES)})")
        if not matches_template(load_template(args.template), text):
            raise ValueError(f"el texto no sigue la plantilla {args.template}: redactarlo desde ella")
        needed = PUBLIC_TEMPLATES[args.template]
        if meta.get("estado") != needed:
            raise ValueError(f"{args.template} se publica en estado {needed}; el pedido está en {meta.get('estado')}")
    if not meta.get("jsm"):
        raise ValueError(f"{args.pry} no tiene pedido JSM: correr `arq jira {args.pry} --apply` primero")
    check_key(meta["jsm"])
    kind = "respuesta pública al requirente" if args.public else "nota interna"
    print(f"{kind} en {meta['jsm']}:\n\n{text}\n")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    ctx.client("jsm").comment(meta["jsm"], text, public=args.public)
    print(f"publicado: {kind} en {meta['jsm']}")
    return 0


def _seguimiento(ctx: Context, args) -> int:
    meta, _ = review.load(ctx.repo, args.pry)
    if meta.get("veredicto") != "aprobar-con-condiciones" or meta.get("estado") not in ("publicado", "cerrado"):
        raise ValueError("las sub-tasks de seguimiento son para un veredicto aprobar-con-condiciones ya publicado")
    follow = followup_plan(meta, args.condiciones)
    print(f"bajo {follow['parent_summary']}:")
    for sub in follow["subtasks"]:
        print(f"  sub-task {sub['summary']}")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    config = cfg.load_config(ctx.repo)
    label = base_labels(meta)[0]
    known, _ = known_from_journal(read_entries(ctx.repo), label, meta["pry"])
    result = apply_followups(follow, label, ctx.client("seguimiento"), config["jira_project"], config["issue_types"],
                             known=known)
    print(f"seguimiento: creadas {len(result['created'])}, existentes {len(result['reused'])}")
    return 0


def _link(ctx: Context, args) -> int:
    check_key(args.inward)
    check_key(args.outward)
    link_type = cfg.load_config(ctx.repo)["link_type"]
    print(f"link {link_type}: {args.inward} → {args.outward}")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    ctx.client("link").link(args.inward, args.outward, link_type)
    print("linkeado")
    return 0


def _eval(ctx: Context, args) -> int:
    failures = evaluate_files(Path(args.golden), Path(args.review))
    for failure in failures:
        print(f"✗ {failure}")
    if failures:
        return 1
    print("ok: cumple la rúbrica")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arq", description="Revisión de Arquitectura de pedidos PRY.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, handler: Callable, help_text: str) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text)
        command.set_defaults(handler=handler)
        return command

    add("init", _init, "inicializa el repo de reviews (.arq/config.json y reviews/)")
    add("path", _path, "imprime la carpeta del contrato")
    p = add("new", _new, "registra un pedido nuevo")
    p.add_argument("pry")
    p.add_argument("--nombre", required=True)
    p.add_argument("--pedido", required=True, help="archivo con el texto del pedido, o - para leer de stdin")
    p.add_argument("--contacto", required=True, help="email del contacto principal (requirente)")
    p.add_argument("--head", help="email del head o stakeholder (participante del pedido JSM)")
    p = add("show", _show, "muestra el estado de un pedido")
    p.add_argument("pry")
    p = add("triage", _triage, "clasifica el pedido en simple o complejo (se puede repetir hasta crear la épica)")
    p.add_argument("pry")
    p.add_argument("--answers", required=True, help="id=si|no separados por coma (ver contract/triage.md)")
    p = add("set", _set, "actualiza campos del architect o el firmante")
    p.add_argument("pry")
    p.add_argument("updates", nargs="+", metavar="campo=valor")
    p = add("state", _state, "cambia el estado del pedido")
    p.add_argument("pry")
    p.add_argument("--to", required=True)
    p.add_argument("--resultado")
    p = add("timebox", _timebox, "arranca o consulta el plazo")
    p.add_argument("pry")
    p.add_argument("--today", help="AAAA-MM-DD (por defecto, hoy)")
    p = add("lint", _lint, "valida constraints.md")
    p.add_argument("--file")
    p = add("jira", _jira, "crea épica, tareas y pedido JSM (dry run salvo --apply)")
    p.add_argument("pry")
    p.add_argument("--html")
    p.add_argument("--con-validacion", action="store_true", help="incluye la historia opcional de validación técnica")
    p.add_argument("--apply", action="store_true")
    p = add("jsm", _jsm, "comenta en el pedido JSM (dry run salvo --apply)")
    p.add_argument("pry")
    p.add_argument("--file", required=True)
    p.add_argument("--template", help="plantilla del mensaje público (" + ", ".join(PUBLIC_TEMPLATES) + ")")
    channel = p.add_mutually_exclusive_group(required=True)
    channel.add_argument("--public", action="store_true", help="respuesta al requirente")
    channel.add_argument("--internal", action="store_true", help="nota interna")
    p.add_argument("--apply", action="store_true")
    p = add("seguimiento", _seguimiento, "una sub-task por condición de un aprobar-con-condiciones (dry run salvo --apply)")
    p.add_argument("pry")
    p.add_argument("condiciones", nargs="+")
    p.add_argument("--apply", action="store_true")
    p = add("link", _link, "linkea dos issues (dry run salvo --apply)")
    p.add_argument("inward")
    p.add_argument("outward")
    p.add_argument("--apply", action="store_true")
    p = add("eval", _eval, "evalúa un review contra un golden case")
    p.add_argument("golden")
    p.add_argument("review")
    return parser


def main(argv: Optional[List[str]] = None, env: Optional[Mapping[str, str]] = None, cwd: Optional[str] = None,
         client_factory: Optional[Callable[[], object]] = None, today: Optional[date] = None) -> int:
    args = build_parser().parse_args(argv)
    ctx = Context(Path(cwd or os.getcwd()).resolve(), os.environ if env is None else env, client_factory,
                  today or date.today())
    try:
        return args.handler(ctx, args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Smoke test manual**

```bash
chmod +x arq.py
./arq.py --help
./arq.py lint
./arq.py path
```
Expected: la ayuda lista los 14 subcomandos; `lint` imprime `ok: .../contract/constraints.md`; `path` imprime la
carpeta `contract`.

- [ ] **Step 6: Commit**

```bash
git add arq.py arqlib/cli.py tests/test_cli.py
git commit -m "feat: add arq CLI"
```

---

### Task 14: Skills, instalación y README

**Files:**
- Create: `skills/arq-manager/SKILL.md`, `skills/arq-architect/SKILL.md`, `install.sh`, `README.md`,
  `tests/test_skills.py`

**Interfaces:**
- Consumes: los subcomandos de `arq` (Task 13). Los drafts del architect viven junto al review:
  `reviews/PRY-XXXX.jsm.md` (mensaje JSM) y `reviews/PRY-XXXX.comentario.md` (comentario para la plataforma).

- [ ] **Step 1: Escribir el test que falla**

`tests/test_skills.py`:
```python
from __future__ import annotations

import re
import unittest

import helpers
from arqlib.cli import build_parser

SKILLS = helpers.ROOT / "skills"


def subcommands():
    parser = build_parser()
    action = next(a for a in parser._actions if a.dest == "command")
    return set(action.choices)


class SkillsTest(unittest.TestCase):
    def test_both_skills_exist(self):
        found = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
        self.assertEqual(found, ["arq-architect", "arq-manager"])

    def test_frontmatter(self):
        for name in ("arq-manager", "arq-architect"):
            text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith(f"---\nname: {name}\ndescription: Use when "), name)

    def test_every_arq_command_mentioned_exists(self):
        known = subcommands()
        for path in SKILLS.glob("*/SKILL.md"):
            used = set(re.findall(r"`!? ?arq (\w+)", path.read_text(encoding="utf-8")))
            self.assertTrue(used, path)
            self.assertEqual(used - known, set(), path)

    def test_skills_never_run_apply_themselves(self):
        for path in SKILLS.glob("*/SKILL.md"):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "--apply" in line and "arq " in line:
                    self.assertIn("!", line, f"{path.parent.name}: {line}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL con `FileNotFoundError` en `skills/arq-manager/SKILL.md`

- [ ] **Step 3: Escribir `skills/arq-manager/SKILL.md`**

````markdown
---
name: arq-manager
description: Use when a PRY-YYYY-NNNN project request arrives for Architecture validation and someone has to register it, triage it, open its Jira epic and JSM ticket, watch its deadline, or publish the signed decision. Coordination only; technical judgment belongs to arq-architect.
---

# arq-manager

Coordina la revisión de Arquitectura de un pedido PRY: registro, triage, Jira y JSM, plazo y publicación. **No emite
juicio técnico**: eso es de `arq-architect`. Todo pasa por el CLI `arq`, parado en el repo de reviews del equipo.

## Antes de empezar

1. Si no existe `.arq/config.json`, correr `arq init` y pedirle al usuario `jsm_project`, `jsm_service_desk_id` y
   `jsm_request_type_id` (y `jira_project` si no es `ARQ`) para completarlo.
2. `arq show PRY-AAAA-NNNN` y actuar en este orden:

| Condición | Qué hace el manager |
|---|---|
| El review no existe | Paso 1: registrar |
| `estado: recibido` | Paso 2: triage |
| `epica` vacía (en cualquier estado) | Paso 3: Jira y JSM |
| `jsm_listo` vacío | Paso 3 otra vez: el mismo comando completa lo que falta |
| `triado`, `esperando-info`, `en-analisis` | Le toca a `arq-architect`. Controlar el plazo (paso 4) y publicar el pedido de información que deje redactado |
| `en-firma` | Paso 5: firma |
| `publicado` | Paso 6: devolución y cierre |
| `propuesta-rechazo` | Paso 7 |

## 1. Registrar

Transcribir el pedido **textual** (de texto pegado o screenshot de la plataforma) a un archivo en el scratchpad, sin
resumir ni corregir: es evidencia. El "Contacto principal" es el requirente y el "Head / Stakeholder" es el head:

`arq new PRY-AAAA-NNNN --nombre "<nombre>" --pedido <archivo> --contacto <email del contacto> --head <email del head>`

## 2. Triage

Leer `triage.md` en la carpeta que imprime `arq path`. Para cada pregunta, proponer sí o no citando la frase del
pedido que lo justifica, y **pedirle confirmación al usuario**: contesta la persona que coordina, no el modelo. Ante la
duda, "sí". Con las respuestas confirmadas: `arq triage PRY-AAAA-NNNN --answers "<id>=si|no,..."`. Si hubo un error,
se puede repetir mientras no exista la épica.

## 3. Jira y JSM

1. `arq jira PRY-AAAA-NNNN --html <scratchpad>/PRY-AAAA-NNNN.html`: mostrar el árbol y abrir el HTML. En nivel
   `complejo`, preguntar si hace falta la historia opcional de validación técnica (`--con-validacion`).
2. Esperar un sí explícito.
3. Darle al usuario el comando para que lo corra él: `! arq jira PRY-AAAA-NNNN --apply` (con `--con-validacion` si
   corresponde). **Nunca correr `--apply`.**
4. El pedido JSM se crea a nombre del contacto, que se busca en Jira por email, y el head queda como participante. Si
   el CLI dice que no encontró a alguien, hay que darlo de alta como cliente del Service Desk y repetir el mismo
   comando.
5. Ante cualquier falla, el mismo `! arq jira PRY-AAAA-NNNN --apply` reanuda sin duplicar.

## 4. Plazo y pedido de información

`arq timebox PRY-AAAA-NNNN` fija el vencimiento la primera vez y después lo consulta. Si dice `vencido` estando en
`esperando-info`, ir al paso 7.

Cuando el architect deja `reviews/PRY-AAAA-NNNN.jsm.md` con el estado en `esperando-info`, mostrarlo en dry run con
`arq jsm PRY-AAAA-NNNN --file reviews/PRY-AAAA-NNNN.jsm.md --public --template jsm-pedido-info.md` y, con el ok, darle
al usuario `! arq jsm PRY-AAAA-NNNN --file reviews/PRY-AAAA-NNNN.jsm.md --public --template jsm-pedido-info.md --apply`.
El debate técnico va con `--internal`, nunca con `--public`.

## 5. Firma

Firma una persona según el nivel: `simple` → alguien del track técnico; `complejo` → el Sr Expert. Es política
interna: no se escribe en los tickets. Quien firma revisa `reviews/PRY-AAAA-NNNN.md` y, si está de acuerdo,
`arq set PRY-AAAA-NNNN firmante=<usuario>`. Después: `arq state PRY-AAAA-NNNN --to publicado` (el CLI exige firmante).

## 6. Devolución y cierre

1. Con el estado en `publicado`, publicar la devolución:
   `arq jsm PRY-AAAA-NNNN --file reviews/PRY-AAAA-NNNN.jsm.md --public --template jsm-devolucion.md` (dry run) y
   `! arq jsm PRY-AAAA-NNNN --file reviews/PRY-AAAA-NNNN.jsm.md --public --template jsm-devolucion.md --apply`.
2. Si el veredicto es `aprobar-con-condiciones`, una sub-task por condición de la sección "Condiciones" del review:
   `arq seguimiento PRY-AAAA-NNNN "<condición 1>" "<condición 2>"` (dry run) y
   `! arq seguimiento PRY-AAAA-NNNN "<condición 1>" "<condición 2>" --apply`.
3. Mostrarle al usuario `reviews/PRY-AAAA-NNNN.comentario.md` para pegar en la plataforma PRY. **El click en Aprobar o
   Rechazar lo hace una persona; el agente nunca.** "Aprobar con condiciones" se publica como Aprobar.
4. Leer `templates/escalar-rfc.md`. Si aplica, sugerir la skill `product-brain` para el RFC y linkear la épica de
   delivery: `arq link <EPICA-ARQ> <EPICA-DELIVERY>` (dry run) y `! arq link <EPICA-ARQ> <EPICA-DELIVERY> --apply`.
5. Cuando la persona confirma el click: `arq state PRY-AAAA-NNNN --to cerrado --resultado <resultado>`; el resultado
   tiene que corresponder al veredicto (`aprobar` → `aprobado`, `aprobar-con-condiciones` → `condicionado`,
   `rechazar` → `rechazado`).

## 7. Plazo vencido

`arq state PRY-AAAA-NNNN --to propuesta-rechazo`. Redactar `reviews/PRY-AAAA-NNNN.jsm.md` desde
`templates/jsm-cierre.md` y publicarlo con `--template jsm-cierre.md` como en el paso 4. La persona rechaza en la
plataforma con el motivo y el link al JSM, y se cierra con `arq state PRY-AAAA-NNNN --to cerrado --resultado rechazado`.

## Reglas

- Nunca juicio técnico, ni siquiera "parece razonable".
- Nunca `--apply` por cuenta propia: siempre se lo da al usuario con `!`.
- Lo público sale de las plantillas `jsm-*.md` del contrato; el CLI rechaza lo que no las sigue.
- Labels y tareas hablan del trabajo, nunca de la seniority de las personas.
````

- [ ] **Step 4: Escribir `skills/arq-architect/SKILL.md`**

````markdown
---
name: arq-architect
description: Use when a triaged PRY request needs Architecture's technical review - checking its minimum input, analyzing it against the constraints, proposing the original plus two options for its weakest component, signals for Cloud, Security and FinOps, and a proposed verdict. Technical judgment only; tickets, deadlines and publishing belong to arq-manager.
---

# arq-architect

Hace la revisión técnica de un pedido PRY y deja todo escrito en `reviews/PRY-AAAA-NNNN.md` (repo de reviews del
equipo). No crea tickets, no maneja plazos y no publica: eso es de `arq-manager`.

## Antes de empezar

1. `arq show PRY-AAAA-NNNN`. Se trabaja en `triado`, `esperando-info` (si el requirente respondió) o `en-analisis`.
   Otro estado → decirlo y no avanzar.
2. Leer el contrato en la carpeta que imprime `arq path`: `constraints.md`, `minimum-input.md` y
   `templates/analisis.md`. `arq lint` tiene que dar ok.
3. Leer el pedido y todos los links de documentación accesibles. Lo que no se pueda abrir se lista como `[verificar]`.

## 1. Gap check

Para cada ID de input del nivel (`minimum-input.md`), decidir si está, citando el artefacto concreto que lo cubre. El
test: cada afirmación tiene que apuntar a un número, componente, diagrama o métrica. Si no, es prosa y falta.

`arq set PRY-AAAA-NNNN faltantes=<id1>,<id2>` (vacío si no falta nada).

- **Falta input** → `arq state PRY-AAAA-NNNN --to esperando-info`. Escribir en el review las secciones "Lo que
  entendimos", "Input faltante" y "Análisis preliminar (sin veredicto)" con los pasos 2, 3 y 7 del método, y fijar
  `arq set PRY-AAAA-NNNN componente_debil=<c> senales=<s>`. Redactar `reviews/PRY-AAAA-NNNN.jsm.md` desde
  `templates/jsm-pedido-info.md`, completando solo los placeholders y sin tocar el texto fijo (el CLI rechaza lo que
  no sigue la plantilla): por cada faltante, una pregunta **concreta para este pedido** (nunca genérica) y por qué se
  pide. Avisar que le toca a `arq-manager` publicarlo.
- **Input completo** → `arq state PRY-AAAA-NNNN --to en-analisis` y seguir.

## 2. Método

1. **Reformular** el pedido en un párrafo.
2. **Descomponer** en componentes: `computo, datos, identidad, red, aprovisionamiento, operacion, costo`.
3. **Evaluar** cada uno contra las constraints y los pilares Well-Architected pertinentes: `ok | débil | bloqueante`.
4. **Viabilidad.** El original es viable si ninguna bloqueante queda sin solución posible. Viable → Opción 0 = original
   y **2 opciones solo para el componente más débil** (mayor severidad; si empatan, mayor costo o riesgo). No viable →
   2 alternativas completas y qué tendría que cambiar el original.
5. **Opciones.** Cada una cumple todas las bloqueantes y se diferencia en un eje real (costo vs. control, rapidez vs.
   reversibilidad). Trae costo en orden de magnitud, esfuerzo, riesgo, reversibilidad y constraints que toca.
6. **Recomendación** con el porqué y condiciones verificables ("se cumple cuando…").
7. **Señales** para Cloud, Seguridad y FinOps, sin veredicto: "⚠ FinOps podría observar: X, porque Y".
8. **Evidencia.** Cada afirmación lleva `[pedido]`, `[C-XXX-NN]`, `[supuesto]` o `[verificar]`. Ningún número sin
   etiqueta.

| Situación | Veredicto |
|---|---|
| Bloqueante sin solución | `rechazar`, con opciones que cumplen |
| Bloqueante resoluble o condicionantes | `aprobar-con-condiciones` |
| Todo ok | `aprobar`, con recomendaciones |

## 3. Escribir

1. Completar en el review las secciones de `templates/analisis.md`, debajo de "Pedido original". En "Condiciones",
   una condición verificable por bullet: `arq-manager` crea una sub-task de seguimiento por cada una.
2. `arq set PRY-AAAA-NNNN componente_debil=<c> senales=<s> veredicto=<v>`. El CLI rechaza un veredicto con input
   faltante.
3. Redactar `reviews/PRY-AAAA-NNNN.jsm.md` desde `templates/jsm-devolucion.md` y `reviews/PRY-AAAA-NNNN.comentario.md`
   desde `templates/comentario-pry.md`, completando solo los placeholders y sin tocar el texto fijo.
4. `arq state PRY-AAAA-NNNN --to en-firma` (el CLI exige veredicto y nada faltante) y decir quién firma: nivel
   `simple` → track técnico; `complejo` → Sr Expert.

## Reglas

- Nunca un veredicto sobre Cloud, Seguridad o FinOps: solo señales.
- Nunca reescribir todo el pedido cuando el original es viable: mejorar el componente más débil.
- Lo que lee el requirente va en tono profesional y con recomendaciones; el debate técnico crudo va como nota interna
  (`arq jsm ... --internal`, lo publica `arq-manager`).
- Para tunear: `arq eval tests/golden/<PRY> reviews/<PRY>.md` contra los golden cases del repo `arq-review`. Cada
  revisión real que salga mal se convierte en un golden case nuevo.
````

- [ ] **Step 5: Escribir `install.sh`**

```bash
#!/usr/bin/env bash
# Install arq-review for Claude Code, Codex and Cursor.
#   ./install.sh
# Skills: ~/.agents/skills/<skill> points at this repo's skills/<skill>; ~/.claude/skills and ~/.codex/skills point
# at ../../.agents/skills/<skill>; Cursor reads ~/.agents/skills natively (same layout as WayOfWork and jira-kanban).
# CLI: ~/.local/bin/arq points at arq.py. Re-running is safe. A real file or directory with the same name is never
# replaced: the script stops with exit 1.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
  "") ;;
  *) echo "unknown argument: $1" >&2; exit 2 ;;
esac

link() {  # link <target> <path>: create or refresh a symlink, never replace a real file or directory
  if [ -e "$2" ] && [ ! -L "$2" ]; then
    echo "refusing to replace $2: it is not a symlink; move it away and re-run" >&2
    return 1
  fi
  mkdir -p "$(dirname "$2")"
  ln -sfn "$1" "$2"
}

status=0
for skill in arq-manager arq-architect; do
  link "$REPO/skills/$skill" "$HOME/.agents/skills/$skill" || exit 1
  for host in .claude .codex; do
    link "../../.agents/skills/$skill" "$HOME/$host/skills/$skill" || status=1
  done
done
chmod +x "$REPO/arq.py"
link "$REPO/arq.py" "$HOME/.local/bin/arq" || status=1
command -v python3 >/dev/null || { echo "note: python3 is not on PATH; arq needs it" >&2; status=1; }
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "note: add ~/.local/bin to PATH to use arq" >&2 ;; esac
echo "skills: arq-manager, arq-architect (Claude Code, Codex, Cursor) -> $REPO/skills"
echo "cli: arq -> $REPO/arq.py"
exit "$status"
```

- [ ] **Step 6: Escribir `README.md`**

````markdown
# arq-review

Revisión de Arquitectura de pedidos `PRY-AAAA-NNNN`: input mínimo, análisis contra constraints, original + 2 opciones
para el componente más débil, señales para Cloud/Seguridad/FinOps y veredicto propuesto. Jira (épica por pedido) y JSM
(conversación con el requirente) como sistema de registro; el análisis vive en git.

- Diseño: `docs/superpowers/specs/2026-10-07-arq-review-design.md`
- Skills: `arq-manager` (coordinación) y `arq-architect` (juicio técnico)
- Contrato (lo mantiene Arquitectura): `contract/`

## Instalar

```bash
./install.sh
export JIRA_BASE_URL=https://<sitio>.atlassian.net JIRA_EMAIL=<mail> JIRA_API_TOKEN=<token>
```

## Uso, en el repo de reviews del equipo

```bash
arq init                                             # .arq/config.json y reviews/
arq new PRY-2026-0028 --nombre "PoC modelos IA Locales" --pedido pedido.txt \
  --contacto requester@example.com --head reviewer@example.com
arq triage PRY-2026-0028 --answers "multi_cuenta=no,..."
arq jira PRY-2026-0028 --html vista.html             # dry run
arq jira PRY-2026-0028 --apply                       # lo corre una persona
arq timebox PRY-2026-0028
arq jsm PRY-2026-0028 --file reviews/PRY-2026-0028.jsm.md --public --template jsm-pedido-info.md
arq show PRY-2026-0028
```

Ninguna escritura en Jira/JSM ocurre sin `--apply`, y todas quedan en `.arq/jira-writes.jsonl`. El pedido JSM se crea
a nombre del contacto (buscado en Jira por email) con el head como participante. Las respuestas públicas tienen que
seguir una plantilla `jsm-*.md` y respetar el estado del pedido. Nada aprueba ni rechaza en la plataforma PRY: eso lo
hace una persona.

## Tests

```bash
python3 -m unittest discover -s tests -v
/usr/bin/python3 -m unittest discover -s tests       # compatibilidad 3.9
```
````

- [ ] **Step 7: Correr la suite completa con ambos intérpretes**

Run: `python3 -m unittest discover -s tests -v && /usr/bin/python3 -m unittest discover -s tests`
Expected: PASS en los dos.

- [ ] **Step 8: Verificar la instalación sin tocar el HOME real**

Run: `HOME="$(mktemp -d)" bash -c './install.sh && ls -l "$HOME/.claude/skills" "$HOME/.local/bin"'`
Expected: `arq-manager` y `arq-architect` como symlinks en `.claude/skills`; `arq` en `.local/bin`; exit 0 (puede
avisar que `~/.local/bin` no está en el PATH del HOME temporal).

- [ ] **Step 9: Commit**

```bash
chmod +x install.sh
git add skills install.sh README.md tests/test_skills.py
git commit -m "feat: add arq-manager and arq-architect skills with installer"
```
