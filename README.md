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
