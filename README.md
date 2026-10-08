# arq-review

Revisión de Arquitectura de pedidos `PRY-AAAA-NNNN` de la plataforma de requerimientos: input mínimo, análisis contra
constraints, propuesta original + 2 opciones para el componente más débil, señales para Cloud/Seguridad/FinOps y
veredicto propuesto. Jira es el sistema de registro (una épica por pedido y un ticket donde conversa el requirente); el
análisis vive en git.

- Diseño: `docs/superpowers/specs/2026-10-07-arq-review-design.md` (decisiones D1–D14, lecciones de la primera corrida)
- Skills: `arq-manager` (coordinación) y `arq-architect` (juicio técnico)
- Contrato (lo mantiene Arquitectura): `contract/` — `constraints.md`, `triage.md`, `minimum-input.md`, `templates/`
- Guía para agentes que modifican este repo: `AGENTS.md`
- Diagramas de los boards de Jira y de la secuencia completa: `docs/diagrams/jira-flujo.md`

## Instalar

```bash
./install.sh            # skills en ~/.claude, ~/.codex y ~/.agents (Cursor); CLI en ~/.local/bin/arq
```

Las escrituras en Jira necesitan `JIRA_BASE_URL` (https), `JIRA_EMAIL` y `JIRA_API_TOKEN` en el entorno. Por ejemplo,
cargándolas desde un `.env` existente en la misma línea del comando:

```bash
set -a && source <ruta>/.env && set +a && arq jira PRY-2026-0028 --apply
```

## Repo de reviews del equipo

`arq` trabaja sobre el directorio actual, que es el repo de reviews (separado de esta herramienta):

```
<repo-reviews>/
├── .arq/config.json            # ver abajo
├── .arq/jira-writes.jsonl      # journal de cada escritura en Jira (se commitea)
└── reviews/
    ├── PRY-2026-0028.md        # frontmatter de estado + análisis
    ├── PRY-2026-0028.jsm.md    # mensaje al requirente (lo redacta arq-architect)
    └── PRY-2026-0028.comentario.md  # comentario corto para la plataforma PRY
```

`.arq/config.json`, tal como se usa en ACME (canal `software`: el requirente conversa en un proyecto de Software usado
como help desk):

```json
{
  "jira_project": "PLATE",
  "issue_types": {"epic": "Epic", "story": "Story (migrated)", "task": "Tarea", "subtask": "Subtarea"},
  "link_type": "Relates",
  "timebox_dias_habiles": 10,
  "canal_requirente": "software",
  "helpdesk_project": "PEHD",
  "helpdesk_issue_type": "Tarea"
}
```

Con `"canal_requirente": "jsm"` se usan en cambio `jsm_project`, `jsm_service_desk_id` y `jsm_request_type_id`.

## Comandos

| Comando | Qué hace |
|---|---|
| `arq init` | crea `.arq/config.json` y `reviews/` |
| `arq path` · `arq lint` | carpeta del contrato · valida `constraints.md` |
| `arq new PRY --nombre N --pedido F --contacto EMAIL [--head EMAIL]` | registra un pedido (`recibido`) |
| `arq show PRY` | muestra el estado del review (local) |
| `arq ver PRY [--sin-links]` | solo lectura en Jira: ticket del requirente y árbol de la épica con el estado, el responsable y el avance de cada issue; las claves son links clickeables en la terminal (OSC 8) |
| `arq triage PRY --answers "id=si,..."` | nivel `simple`/`complejo`; se puede repetir hasta crear la épica |
| `arq jira PRY [--html F] [--con-validacion] [--apply]` | épica, historias y sub-tasks + ticket del requirente, linkeados |
| `arq timebox PRY [--today AAAA-MM-DD]` | arranca o consulta el plazo |
| `arq set PRY campo=valor ...` | `faltantes`, `componente_debil`, `senales`, `veredicto`, `firmante` |
| `arq state PRY --to ESTADO [--resultado R]` | cambia de estado (con guardas) |
| `arq jsm PRY --file F (--public --template T \| --internal) [--apply]` | comenta en el ticket del requirente |
| `arq seguimiento PRY "condición" ... [--apply]` | una sub-task por condición de un aprobar-con-condiciones |
| `arq link A B [--apply]` | linkea dos issues (por ejemplo, la épica de delivery de Product Brain) |
| `arq eval tests/golden/PRY reviews/PRY.md` | evalúa un review contra un golden case |

## Garantías

- **Nada se escribe en Jira sin `--apply`**, y el `--apply` lo corre una persona. Nada aprueba ni rechaza en la
  plataforma PRY: eso también lo hace una persona.
- **El ticket del requirente se crea a su nombre**, buscado en Jira por email: pedido JSM con el head como
  participante, o issue del help desk con el contacto de reporter y el head de watcher. Si no se puede confirmar la
  identidad o Jira rechaza el reporter, no se crea nada.
- **Volver a correr no duplica.** Cada issue lleva un ID estable (entity property `arq.node`); renombrarlo en Jira es
  seguro. La búsqueda por label `pry:` y el journal cubren la demora del índice de Jira.
- **Lo público tiene guardas:** sigue una plantilla `jsm-*.md`, nombra su PRY, respeta el estado del pedido (una
  devolución nunca sale antes de la firma) y no se publica dos veces el mismo mensaje.
- **La firma queda atada al veredicto:** se firma solo en `en-firma`; reabrir el análisis la anula.
- **Jira es un espejo del review.** La épica muestra el resumen del análisis y cada tarea dice qué hacer y cuándo
  está terminada. Cada `arq jira PRY --apply` reescribe las descripciones que cambiaron: **no editarlas a mano** (se
  pisan); las notas van en comentarios y los responsables no se tocan.

## Tests

```bash
python3 -m unittest discover -s tests -v
/usr/bin/python3 -m unittest discover -s tests       # compatibilidad 3.9
```
