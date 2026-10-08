# arq-review — guía para agentes

- Python ≥ 3.9, solo stdlib. TDD. Suite: `python3 -m unittest discover -s tests -v`, también con `/usr/bin/python3`.
- Los tests nunca salen a la red: usar `tests/helpers.FakeJira` o un `opener` falso.
- El contrato (`contract/`) lo mantiene Arquitectura: el código lo lee, nunca lo reescribe.
- Toda escritura en Jira es dry run salvo `--apply`, que corre el usuario. Cada escritura queda en
  `.arq/jira-writes.jsonl` del repo de reviews.
- **Nunca cambiar el ID de un nodo** (`node` en `arqlib/structure.py`, que se graba como entity property `arq.node`):
  equivale a crear issues nuevos en todos los pedidos ya abiertos. Los textos (`summary`, `description`) sí se pueden
  cambiar.
- arq es dueño de las descripciones de los issues (`summary.render_epic` para la épica, `structure.DOCS` para el
  resto) y las reescribe cuando cambian. No escribir nunca en comentarios ni en responsables.
- Un golden case (`tests/golden/`) se corrige solo cuando cambia la evidencia (triage real, documentación vigente),
  nunca para que pase una salida del architect.
- Las skills (`skills/*/SKILL.md`) solo nombran subcomandos que existen y nunca corren `--apply` sin `!`:
  `tests/test_skills.py` lo verifica.
- Commits: conventional commits, sin atribución de IA. Rama corta y merge fast-forward a `main`.
