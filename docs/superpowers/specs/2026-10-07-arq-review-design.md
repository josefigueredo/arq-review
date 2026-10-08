# arq-review — Diseño

- **Fecha:** 2026-10-07
- **Estado:** borrador para revisión
- **Dueño:** Sr Expert de Arquitectura

## 1. Propósito

Los pedidos de proyecto (`PRY-YYYY-NNNN`) llegan a la plataforma de requerimientos descritos de forma pobre, porque
quien los escribe no sabe qué pedir. Cloud, Arquitectura, Seguridad y FinOps tienen que validarlos, y la plataforma solo
permite **Aprobar** o **Rechazar** con un comentario (obligatorio al rechazar). No tiene hilo de conversación ni
feedback, y no hay documentación ni journey de la plataforma.

`arq-review` automatiza la parte de **Arquitectura** de esa validación:

1. Exige el **input mínimo** según la complejidad del pedido y distingue un diseño revisable de prosa aspiracional.
2. Analiza el pedido contra las **constraints** publicadas por Arquitectura.
3. Si la propuesta original es viable, la conserva y propone **2 alternativas para el componente más débil**. Si no lo
   es, propone 2 alternativas completas y dice qué tendría que cambiar el original.
4. Devuelve un análisis profesional **con recomendaciones**, un veredicto propuesto y **señales sin veredicto** para
   Cloud, Seguridad y FinOps.
5. Da **visibilidad fuerte dentro y fuera del equipo** a través de Jira (Software y Service Desk).

**Éxito:** cada PRY tiene una épica en Jira, una conversación auditable con el requirente en JSM y un análisis
versionado en git. Ninguna decisión depende de chats por fuera del registro, y el veredicto cita reglas, no opiniones.

## 2. Decisiones tomadas

| # | Decisión | Motivo |
|---|---|---|
| D1 | Entrada manual (pegar texto o screenshot) ahora; MCP de **solo lectura** sobre el backend de la plataforma después. | Valor inmediato. El análisis consume un pedido normalizado, así que cambiar de adaptador no lo toca. |
| D2 | Comentario corto en la plataforma + análisis completo en markdown en git (fuente de verdad), con proyecciones a Confluence o a un RFC de Product Brain. | El comentario es la decisión y el documento es la justificación. Las copias nunca se editan a mano. |
| D3 | Veredicto solo de Arquitectura + señales sin veredicto para Cloud, Seguridad y FinOps. | No pisar la autoridad de otros sectores y evitar rechazos en serie. |
| D4 | Revisión por niveles: `simple` la firma alguien del track técnico; `complejo` la firma el Sr Expert. El EM hace el triage. | Evitar el cuello de botella en una sola persona y dar crecimiento al equipo. |
| D5 | Requirentes conversan en el **Service Desk (JSM)**; el trabajo interno vive en Jira Software. | La plataforma no tiene comentarios. Jira es el sistema de registro. |
| D6 | Labels neutros: `track:coordinacion`, `track:tecnica`, `nivel:simple`, `nivel:complejo`, `pry:YYYY-NNNN`. Nunca labels de seniority. | Los artefactos describen trabajo; los roles describen personas. Evitar roces. |
| D7 | Nunca rechazar por falta de input al principio: el PRY queda pendiente con un **timebox** mientras se itera en JSM. | El rechazo en la plataforma parece terminal (ver S1). |
| D8 | **Épica siempre**, una por PRY. Nivel simple: épica mínima. Nivel complejo: épica con 4 historias. | Un solo patrón en el tablero, legible para el EM. |
| D9 | Cliente propio de Jira y JSM, **solo stdlib**, inspirado en los patrones de `jira-kanban` (dry run, preview HTML, `--apply` ejecutado por el usuario, journal, reanudar sin duplicar). Sin depender de que `jk` esté instalado. | `jk` no cubre JSM, links, comentarios ni búsqueda por label, y vive en una sola máquina. |
| D10 | Dos skills de rol (`arq-manager`, `arq-architect`) sobre un **contrato compartido** y scripts determinísticos. Ninguna skill invoca a la otra; el estado vive en el archivo del review. | Separar el juicio técnico de la orquestación sin duplicar reglas. |
| D11 | La herramienta (`arq-review`) y los datos (repo de reviews del equipo) son repos separados. | Que cada revisión no ensucie el historial de la herramienta, y que la herramienta sirva a más de un equipo. |
| D12 | El ticket del requirente (pedido JSM o issue del help desk, según D14) se crea **a nombre del requirente** (`raiseOnBehalfOf`), buscado en Jira por el email que trae la plataforma, con el head como participante. Si no existe en Jira, o si Jira oculta su email y no se puede confirmar la identidad, no se crea nada. | Si lo crea el usuario de la API, el requirente nunca recibe notificaciones y D5 no sirve. Nunca se crea un ticket a nombre de otra persona. |
| D14 | El canal del requirente es configurable (`canal_requirente`): `jsm` (pedido de Service Management, `raiseOnBehalfOf`, participantes, notas internas) o `software` (issue en un proyecto de Software usado como help desk, hoy PEHD con tipo `Tarea`: el requirente es el *reporter*, el head es *watcher*, todo comentario es público y no hay notas internas; el debate técnico va en la épica). Si Jira rechaza el reporter, no se crea nada. | ACME no tiene un JSM de Arquitectura; los requirentes tienen licencia de Jira y ya trabajan con PEHD. El análisis y las guardas no cambian: solo el adaptador hacia Jira. |
| D15 | **arq es dueño de las descripciones** de los issues que crea. La épica muestra el **resumen del review** (estado, faltantes, componente más débil, señales, veredicto y las secciones del análisis, convertidas a formato Jira); cada tarea dice por qué, qué, cómo (con los comandos de su PRY) y cuándo está terminada. Cada `arq jira --apply` reescribe solo las descripciones que cambiaron (hash guardado en `arq.node`). Las notas van en comentarios, que arq nunca toca. | Visibilidad en Jira sin abrir git, sin crear una segunda fuente de verdad: git manda y Jira es un espejo. |
| D16 | **El estado de las tareas sigue al review.** En cada `arq jira --apply`, las tareas cuyo "Terminado cuando" ya se cumple pasan a Done (transición a la categoría *done* del workflow), las historias cuando terminan todas sus sub-tasks y la épica al cerrar. La primera sub-task sin terminar (en orden de ejecución, salteando la validación técnica), su historia y la épica pasan a En curso si estaban por hacer. Solo hacia adelante: nunca se reabre nada ni se pisa lo que una persona cerró. La validación técnica y el seguimiento de condiciones no se mueven solos. | El tablero tiene que contar la verdad sin trabajo manual; derivarlo del review evita una segunda fuente de verdad. |
| D13 | Lo público tiene doble guarda: el texto tiene que seguir una plantilla `jsm-*.md` y el pedido tiene que estar en el estado de esa plantilla. | Que nunca salga una devolución antes de la firma ni un texto libre al requirente. |

## 3. Supuestos no verificados

- **S1.** Un rechazo en la plataforma es **terminal** (no se puede reabrir el mismo PRY). Se diseña para el peor caso.
  Si resulta falso, el diseño sigue sirviendo y solo gana flexibilidad.
- **S2.** ~~Hay un proyecto JSM disponible y los requirentes pueden usar su portal.~~ **Falso** (2026-10-07): el sitio
  `example.atlassian.net` no tiene un JSM de Arquitectura. Resuelto con D14: canal `software` sobre PEHD.
- **S3.** ~~La instancia de Jira usa la jerarquía estándar.~~ **Verificado** (2026-10-07): PLATE usa Epic →
  Story (migrated) / Tarea → Subtarea, y `parent` funciona en los tres niveles.

## 4. Layout

Herramienta (`~/CurrentCode/SPECKIT/Harness/arq-review`):

```
arq-review/
├── install.sh                  # symlinks como WayOfWork / jira-kanban (~/.agents/skills → ~/.claude, ~/.codex)
├── arq.py                      # CLI `arq` (stdlib)
├── arqlib/                     # frontmatter, state, triage, constraints, inputs, timebox, config, review, render,
│                               # structure, journal, jira (Jira + JSM), apply, preview, fields, evaluate, cli
├── contract/
│   ├── constraints.md          # escrito por Arquitectura
│   ├── triage.md
│   ├── minimum-input.md
│   └── templates/
│       ├── analisis.md         # estilo MADR
│       ├── comentario-pry.md
│       ├── jsm-pedido-info.md  # se publica en esperando-info
│       ├── jsm-devolucion.md   # se publica en publicado
│       ├── jsm-cierre.md       # se publica en propuesta-rechazo
│       └── escalar-rfc.md
├── skills/
│   ├── arq-manager/SKILL.md
│   └── arq-architect/SKILL.md
├── tests/
│   ├── test_*.py               # determinístico
│   └── golden/PRY-2026-0026/, PRY-2026-0028/   # input.md + expected.json
└── docs/superpowers/specs/
```

Repo de reviews del equipo (cualquier ruta; el CLI trabaja sobre el cwd):

```
<repo-reviews>/
├── .arq/config.json            # jira_project, issue_types, link_type, timebox_dias_habiles, canal_requirente,
│                               # jsm_project/jsm_service_desk_id/jsm_request_type_id (canal jsm) o
│                               # helpdesk_project/helpdesk_issue_type (canal software)
├── .arq/jira-writes.jsonl      # journal de escrituras
├── reviews/PRY-2026-0028.md    # frontmatter de estado + análisis
├── reviews/PRY-2026-0028.jsm.md         # borrador del mensaje JSM (lo redacta el architect)
└── reviews/PRY-2026-0028.comentario.md  # comentario para la plataforma PRY
```

Credenciales por variables de entorno (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`), nunca en archivos del repo.

## 5. Flujo y responsabilidades

```
PRY nuevo
 └─ arq-manager
     1. Intake: normaliza el pedido → reviews/PRY-XXXX.md (estado: recibido)
     2. Triage sí/no (arq triage) → nivel (estado: triado)
     3. Épica + tareas + request JSM, todo linkeado (dry run → el usuario aplica)
     4. Arranca el timebox
 └─ arq-architect
     5. Gap check vs minimum-input del nivel
        ├─ falta → redacta jsm-pedido-info (estado: esperando-info) ─┐
        │                                   respuesta del requirente ◄┘ → vuelve a 5
        └─ OK → estado: en-analisis
     6-9. Método (sección 7) → análisis + veredicto propuesto (estado: en-firma)
 └─ HUMANO firma: track técnico si es simple, Sr Expert si es complejo (`arq set firmante=...`)
 └─ arq-manager
     10. Pasa a publicado (exige firmante) y recién ahí publica la devolución en JSM, crea una sub-task de
         seguimiento por condición (`arq seguimiento`) y entrega el comentario corto para PRY
     11. Un humano hace click en Aprobar/Rechazar en la plataforma (estado: cerrado, resultado acorde al veredicto)
     12. Timebox vencido sin respuesta → propone rechazo por falta de información (estado: propuesta-rechazo) y
         publica jsm-cierre
```

Las skills pueden repetir un paso sin miedo: pedir el estado actual no hace nada, y `arq jira --apply` reanuda sin
duplicar. El triage se puede repetir mientras no exista la épica.

- El EM nunca emite juicio técnico. El architect nunca gestiona tickets ni plazos.
- **El agente nunca hace click en Aprobar/Rechazar**, tampoco con el MCP.
- "Aprobar con condiciones" se publica como **Aprobar**, con las condiciones en el comentario, y cada condición queda
  como sub-task de seguimiento.

### 5.1 Máquina de estados (frontmatter)

```
recibido → triado → esperando-info ⇄ en-analisis → en-firma → publicado → cerrado
                         └── timebox vencido → propuesta-rechazo → cerrado
```

`cerrado` lleva `resultado: aprobado | condicionado | rechazado`. Frontmatter:
`pry, nombre, contacto, head, estado, nivel, epica, jsm, jsm_listo, vence, firmante, resultado, faltantes,
componente_debil, senales, veredicto`. `arq state` valida las transiciones; una transición inválida falla.

Guardas: `en-firma` exige veredicto y nada faltante; `publicado` exige firmante; cerrar desde `publicado` exige el
resultado del veredicto (`aprobar` → `aprobado`, `aprobar-con-condiciones` → `condicionado`, `rechazar` →
`rechazado`); cerrar desde `propuesta-rechazo` solo como `rechazado`. Pedir el estado actual no hace nada.

## 6. Contrato

### 6.1 `constraints.md`

Cada constraint con ID estable y estos campos: **Regla**, **Severidad** (`bloqueante | condicionante |
recomendación`), **Por qué**, **Cómo verificar** y **Excepción**. `arq lint` valida que los IDs sean únicos, la
severidad válida y los campos completos. El contenido inicial lo escribe Arquitectura (al menos: IdP platform,
AWS como única cloud, ningún recurso por fuera de platform).

### 6.2 `triage.md`

Basta un solo "sí" para que el pedido sea `complejo`:

1. ¿Toca más de una cuenta, empresa o vertical?
2. ¿Es una migración o mueve datos existentes?
3. ¿La fecha es comprometida?
4. ¿Involucra a otros equipos además del que pide?
5. ¿Incluye datos de clientes o personales, o servicios de IA externos?
6. ¿Dura más de 3 meses o queda productivo?

### 6.3 `minimum-input.md`

El test: cada afirmación del pedido tiene que poder apuntar a un artefacto concreto (número, componente, diagrama o
métrica). Si no puede, es prosa.

- **Simple:** problema + hipótesis medible (métrica y umbral), recursos (tipo, tamaño, cantidad), duración y fecha de
  baja, costo mensual estimado, responsable, vía de aprovisionamiento.
- **Complejo:** todo lo anterior + diagrama C4 de nivel 1-2, flujos y clasificación de datos, cuentas y entornos de
  origen y destino, plan de rollback, dependencias con dueño, requisitos no funcionales.

### 6.4 Plantillas

`analisis.md` sigue MADR: lo que entendimos, input faltante, drivers, evaluación, opciones consideradas, decisión,
recomendación, condiciones, consecuencias, señales y veredicto.
`comentario-pry.md` entra en el textarea de la plataforma: veredicto, 3-5 líneas, condiciones y link.
`escalar-rfc.md` define cuándo escalar: nivel `complejo` **y** (más de 3 meses **o** más de 2 equipos) → RFC en Product
Brain.

## 7. Método del architect

1. **Reformular** el pedido en un párrafo.
2. **Descomponer** en componentes: cómputo, datos, identidad y acceso, red, aprovisionamiento, operación, costo.
3. **Evaluar** cada componente contra las constraints y los pilares Well-Architected pertinentes: `ok | débil |
   bloqueante`.
4. **Viabilidad.** El original es viable si ninguna bloqueante queda sin solución posible.
   - Viable → Opción 0 = original; 2 opciones **solo para el componente más débil** (mayor severidad; si empatan, el
     de mayor costo o riesgo).
   - No viable → 2 alternativas completas + qué tendría que cambiar el original.
5. **Opciones.** Cada una cumple todas las bloqueantes y se diferencia de las otras en un eje real. Trae costo en orden
   de magnitud, esfuerzo, riesgo, reversibilidad y constraints que toca.
6. **Recomendación** con el porqué y condiciones verificables ("se cumple cuando…").
7. **Señales** para Cloud, Seguridad y FinOps, sin veredicto.
8. **Evidencia.** Cada afirmación lleva `[pedido]`, `[C-XXX-NN]`, `[supuesto]` o `[verificar]`.

| Situación | Veredicto |
|---|---|
| Falta input mínimo | No se emite; se pide la información por JSM |
| Bloqueante sin solución | Rechazar, con opciones que cumplen |
| Bloqueante resoluble o condicionantes | Aprobar con condiciones |
| Todo ok | Aprobar con recomendaciones |

## 8. Jira y JSM

**Nivel simple:** épica `[PRY-2026-0028] <nombre>` con una task "Revisión PRY" y sub-tasks: Triage y apertura
(`track:coordinacion`), Gap check (`track:tecnica`), Análisis y opciones (`track:tecnica`), Revisión y firma
(`track:tecnica`), Publicar devolución (`track:coordinacion`).

**Nivel complejo:** épica con las historias Intake y triage (`track:coordinacion`), Análisis y opciones
(`track:tecnica`) y Decisión y comunicación (ambos tracks), cada una con sus sub-tasks. La historia Validación técnica
(`track:tecnica`) es opcional y se crea solo con `arq jira --con-validacion`.

**Seguimiento:** con un veredicto `aprobar-con-condiciones` publicado, `arq seguimiento` crea una sub-task por
condición bajo la task de revisión (simple) o la historia Decisión y comunicación (complejo).

Todo **sin asignar**, con `pry:` y `nivel:` en todos los issues, incluido el pedido JSM, que queda linkeado a la
épica, creado a nombre del contacto y con el head como participante.

Reglas del cliente (`arqlib/jira.py` cubre Jira y JSM):

- **Dry run por defecto**, con preview HTML. Las escrituras solo con `--apply`, que corre el usuario con `!`.
- **Journal** de cada escritura en `.arq/jira-writes.jsonl`.
- **Idempotencia en tres capas:** (1) búsqueda JQL `labels = "pry:YYYY-NNNN"`; (2) las claves del journal que la
  búsqueda todavía no devuelve se confirman una por una, porque `search/jql` de Jira Cloud es eventualmente
  consistente; (3) en JSM, `jsm` se guarda apenas existe el pedido y `jsm_listo=si` solo cuando tiene labels,
  participantes y link, así un re-run completa lo que falta. Cada issue lleva un **ID estable** en la entity property `arq.node` (por ejemplo `intake/abrir-ticket`, o `condicion/<hash>` para el seguimiento): se lo reconoce por ese ID, no por su texto, así que renombrarlo a mano en Jira o cambiar el texto en el código no lo duplica. Un issue creado antes de que existieran los IDs se reconoce una sola vez por (summary, padre) y se le graba el ID. Un issue que ya existe se **reutiliza tal cual**: no se
  modifica, porque el nivel no cambia una vez creada la épica y no hay otro campo que actualizar.
- **Claves validadas** (`[A-Z][A-Z0-9]+-\d+`) antes de entrar en cualquier URL; `JIRA_BASE_URL` tiene que ser https.
- **JSM:** `arq jsm --public` (Reply to customer) y `arq jsm --internal` (nota interna) son canales distintos. El
  público exige `--template` con una plantilla `jsm-*.md`, que el texto la siga y que el pedido esté en el estado de esa
  plantilla.
- **Verificado en la primera corrida real** (PEHD-86, 2026-10-08): repetir `add` de labels, watchers y un link
  idéntico no duplica nada en Jira.
- **Product Brain:** la épica ARQ es de *revisión*. Si el pedido escala a RFC, la épica de *delivery* la crea el flujo
  de Product Brain, y las dos se linkean sin fusionarse.

## 9. Publicación

1. `reviews/PRY-XXXX.md` en git.
2. Respuesta pública en el ticket del requirente (JSM o help desk).
3. Comentario corto para pegar en la plataforma (el click lo hace un humano).
4. Copia en Confluence, o RFC en Product Brain según `escalar-rfc.md`, con el banner "generado desde git, no editar
   acá". La publicación en Confluence queda fuera del MVP (ver sección 12).

## 10. Fase 2: MCP de la plataforma

Servidor MCP de **solo lectura** sobre el backend de la plataforma, con el token de la sesión del usuario. Expone
`get_request(pry)` y `list_pending(area)`, y sigue los links de documentación (Google Docs, GitHub) cuando el usuario
tiene acceso. Devuelve el mismo pedido normalizado que el intake manual. Sin endpoints de aprobar ni rechazar.

## 11. Pruebas

- **Determinístico (TDD, `unittest`, sin red):** triage, transiciones de estado, lint de constraints, payloads de
  Jira/JSM contra un `opener` falso, idempotencia por label, reanudación por journal, render de plantillas.
- **Golden cases:** `tests/golden/<PRY>/input.md` + `expected.json` (la stdlib no trae YAML) con propiedades obligatorias (nivel, estado
  esperado, input que debe pedir, constraints que debe citar, componente más débil, señales, cosas que no debe hacer).
  `arq eval` compara la salida del architect contra la rúbrica. Cada PRY real que salga mal se convierte en un golden
  case nuevo.
- Golden cases iniciales: **PRY-2026-0028** (simple, esperando-info: falta hipótesis medible, fecha de baja, costo y
  vía de aprovisionamiento; señal FinOps) y **PRY-2026-0026** (complejo, esperando-info: diagrama C4 revisable,
  rollback, clasificación de datos para Bedrock, dependencia de la base de datos con dueño; señales Seguridad y Cloud).

## 12. Fuera de alcance (MVP)

- MCP de la plataforma (fase 2).
- Publicación automática en Confluence (en el MVP la copia se hace a mano desde el markdown).
- Métricas y dashboard de SLA más allá de los nativos de JSM.
- Cualquier acción de aprobar o rechazar en la plataforma.

## 13. Definiciones del usuario (resueltas)

- `constraints.md`: 21 reglas aprobadas, con la excepción de Bedrock en C-PLAT-01 (2026-10-07).
- Jira: épicas en **PLATE**; canal del requirente `software` sobre **PEHD**, tipo `Tarea`; link `Relates`.
- Timebox de 10 días hábiles y umbral de 3 meses: en uso desde la primera corrida, sin cambios pedidos.
- Repo de reviews del equipo: `~/CurrentCode/SPECKIT/arq-reviews`.
- Criterio de "cross" para el triage: consumible desde otras cuentas AWS, empresas o verticales cuenta como "sí".

## 14. Lecciones de la primera corrida

- **Identidad estable.** Reconocer los issues por su texto duplicaba issues al renombrarlos; ahora se usa `arq.node`.
  Cambiar el ID de un nodo en `structure.py` equivale a crear issues nuevos en todos los pedidos abiertos.
- **Documentación vigente.** El diagrama adjunto a PRY-2026-0026 era de mayo, y había uno sincronizado con el código
  del día anterior en otra rama. El architect verifica contra el código la fecha de la documentación que lee.
- **Plazo vs. fecha comprometida.** Si la fecha comprometida del pedido es anterior al vencimiento del plazo, la
  revisión está en el camino crítico: el pedido de información prioriza lo que bloquea esa fecha.
- **Goldens.** Se corrigen solo cuando cambia la evidencia (triage real, documentación vigente), nunca para que pase
  una salida del architect.
- **Workflows con otros nombres.** En PLATE el estado "en curso" se llama PROCESANDO; las transiciones se buscan por
  categoría de status y el nombre solo desempata.
- **"Movidas: 0" no es un error.** Un `--apply` repetido no mueve lo que ya avanzó; el tablero real se confirma con
  `arq ver`.
- **Documentación compartible.** Las guías y presentaciones viven como archivos locales (Markdown fuente + HTML
  autocontenido), no como artefactos de claude.ai, porque esos no se pueden compartir con el equipo.
- **Iniciativas como submódulos.** El material que se comparte con el equipo de un pedido (en PRY-2026-0028, una
  calculadora autocontenida) vive en `iniciativas/PRY-AAAA-NNNN/` del repo de reviews, como submódulo con su propio
  remote (`PRY-AAAA-NNNN`). Así el equipo del pedido tiene acceso sin ver las demás revisiones.
- **Evidencia antes que supuestos (PRY-2026-0028).** Los scores de los proveedores no son comparables: Qwen3.6-27B se
  anuncia con 77,2 % en SWE-bench Verified y saca 31,2 % en SWE-rebench. Un supuesto de contexto (48k tokens) quedó
  siete veces corto frente al uso medido (p50 341k). Medir primero y modelar el uso por perfiles, no un promedio.
