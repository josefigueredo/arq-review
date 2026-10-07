# arq-review — guía para agentes

- Python ≥ 3.9, solo stdlib. TDD. Suite: `python3 -m unittest discover -s tests -v`, también con `/usr/bin/python3`.
- Los tests nunca salen a la red.
- El contrato (`contract/`) lo mantiene Arquitectura: el código lo lee, nunca lo reescribe.
- Toda escritura en Jira/JSM es dry run salvo `--apply`, que corre el usuario.
- Commits: conventional commits, sin atribución de IA.
