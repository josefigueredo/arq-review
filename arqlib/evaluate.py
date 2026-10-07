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
