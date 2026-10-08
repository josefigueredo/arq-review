# Revisión de Arquitectura · Flujo con agente

El mismo proceso de la [guía del flujo manual](flujo-manual.md), pero con un **agente de código** (Claude Code, Codex o
Cursor) que hace el trabajo repetitivo. Leé primero el flujo manual: acá no se repite qué es cada paso, solo cómo se
hace con el agente.

## 1. Qué cambia y qué no

| Lo hace el agente | Lo sigue haciendo una persona |
|---|---|
| Pasar el pedido a un review con el formato correcto | Pegarle el pedido (hoy no lo lee solo de la plataforma) |
| Proponer las respuestas de clasificación, citando el pedido | **Confirmar** cada respuesta |
| Armar la épica, las historias, las sub-tasks y el ticket del requirente | **Aprobar** la vista previa y correr el comando que escribe en Jira |
| Calcular el plazo | — |
| Revisar la información mínima y redactar preguntas concretas | Leer las preguntas antes de publicarlas |
| Analizar, proponer opciones y un veredicto | **Firmar** o devolver con cambios |
| Redactar la devolución y el comentario corto | **Hacer el click** en la plataforma PRY |
| Mover las tareas de Jira según el estado del review | Asignar las tareas a las personas |

La regla de fondo: **el agente prepara, una persona decide y publica.** Nada sale hacia afuera (Jira, el requirente o
la plataforma) sin que una persona lo apruebe y ejecute.

## 2. Las piezas

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Agente de código** | Claude Code, Codex o Cursor | Le hablás en lenguaje natural y trabaja con las otras piezas |
| **Skill `arq-manager`** | Instrucciones de coordinación para el agente | Registrar, clasificar, abrir los tickets, cuidar el plazo, publicar. No opina de lo técnico |
| **Skill `arq-architect`** | Instrucciones de revisión técnica para el agente | Información mínima, análisis contra constraints, opciones y veredicto. No crea tickets ni publica |
| **Herramienta `arq`** | Un comando que usan las dos skills | Guarda el estado, valida las reglas y escribe en Jira solo cuando se lo pedís |
| **Repo de reviews** | La carpeta `arq-reviews` | Donde vive cada review. Es la fuente de verdad |
| **MCP de la plataforma PRY** | Conector para que el agente lea los pedidos directamente | **Fase 2: todavía no existe.** Hoy el pedido se pega como texto o captura |

Las dos skills nunca se llaman entre sí. Cada una mira el estado del review y sabe si le toca actuar.

## 3. Antes de empezar

Una sola vez, con ayuda de alguien que ya lo tenga andando:

1. **Instalar** la herramienta y las skills: en el repo `arq-review`, `./install.sh`.
2. **Clonar el repo de reviews** (`arq-reviews`) y abrir el agente **parado en esa carpeta**.
3. **Credenciales de Jira** en un archivo `.env` con `JIRA_BASE_URL`, `JIRA_EMAIL` y `JIRA_API_TOKEN`. El token es
   personal: no lo pegues en el chat ni lo compartas.
4. **Probar** que todo responde: pedile al agente "mostrame el estado de PRY-2026-0028".

## 4. Paso a paso con el agente

Para cada paso: **qué le pedís**, **qué hace solo** y **qué confirmás vos**. Las frases son ejemplos; podés pedirlo
con tus palabras.

> **Los comandos que escriben en Jira los corrés vos**, en tu terminal. El agente te los da armados. En Claude Code
> se corren desde el mismo chat poniendo `!` adelante. Todos llevan `--apply` y necesitan las credenciales cargadas:
>
> ```
> set -a && source <ruta>/.env && set +a && arq jira PRY-AAAA-NNNN --apply
> ```

### Paso 1 · Registrar (arq-manager)

- **Le pedís:** "Registrá el PRY-2026-0031", y pegás el pedido completo o una captura de la plataforma.
- **Hace solo:** copia el pedido tal cual, toma el contacto principal y el head, y crea el review en `recibido`.
- **Confirmás:** que los emails del contacto y del head sean los correctos.

### Paso 2 · Clasificar (arq-manager)

- **Le pedís:** "Hacé el triage del PRY-2026-0031".
- **Hace solo:** propone sí o no para cada una de las seis preguntas, citando la frase del pedido que lo justifica.
- **Confirmás:** cada respuesta. **Decidís vos, no el modelo.** Ante la duda, "sí". Con tu ok queda `simple` o
  `complejo` y el estado pasa a `triado`.

### Paso 3 · Abrir los tickets y el plazo (arq-manager)

- **Le pedís:** "Armá el Jira del PRY-2026-0031".
- **Hace solo:** te muestra una **vista previa** de la épica, las historias, las sub-tasks y el ticket del requirente,
  sin escribir nada. Si es complejo, te pregunta si hace falta la historia de validación técnica.
- **Confirmás:** la vista previa. Después corrés vos el comando que te da (`arq jira PRY-2026-0031 --apply`). Crea la
  épica en PLATE y el ticket en PEHD a nombre del requirente, con el head de watcher y los dos linkeados. Si falla a
  la mitad, **corré el mismo comando otra vez**: retoma sin duplicar.
- **Después:** "arrancá el plazo" fija el vencimiento a 10 días hábiles. Si hay fecha comprometida antes, el agente
  te avisa.

### Paso 4 · Revisar la información mínima (arq-architect)

- **Le pedís:** "Hacé el gap check del PRY-2026-0031".
- **Hace solo:** lee el pedido y los links que pueda abrir, verifica que la documentación esté vigente contra el
  código y marca cada dato mínimo como presente o faltante, citando qué lo cubre. Si falta algo, escribe el análisis
  preliminar sin veredicto, redacta las preguntas para el requirente y pasa el estado a `esperando-info`.
- **Confirmás:** que las preguntas sean concretas y entendibles para el requirente.

### Paso 5 · Publicar el pedido de información (arq-manager)

- **Le pedís:** "Publicá el pedido de información del PRY-2026-0031".
- **Hace solo:** te muestra el mensaje exacto que va a salir y controla que siga la plantilla.
- **Confirmás:** el texto. Corrés el comando que te da (`arq jsm ... --apply`) y el comentario aparece en el ticket
  PEHD. Después corrés `arq jira PRY-2026-0031 --apply` para que el tablero refleje el avance.
- **Mientras esperás:** cuando el requirente responda, volvé al paso 4 ("el requirente respondió, revisá de nuevo").
  Si vence el plazo, el agente te lo dice y pasás al paso 9.

### Paso 6 · Analizar (arq-architect)

- **Le pedís:** "Analizá el PRY-2026-0031".
- **Hace solo:** separa el pedido en partes, evalúa cada una contra las constraints, elige el punto más débil y
  propone el original + 2 opciones, la recomendación con condiciones, las señales para Cloud, Seguridad y FinOps, y el
  veredicto. Redacta la devolución y el comentario corto. Estado: `en-firma`.
- **Confirmás:** nada todavía: la revisión real la hace el firmante en el paso siguiente.

### Paso 7 · Firmar (persona)

- **El firmante** lee el review completo (`reviews/PRY-2026-0031.md`).
  - **De acuerdo:** "Firmá el PRY-2026-0031 como `<tu usuario>`". El estado pasa a `publicado`.
  - **Pide cambios:** "Volvé el PRY-2026-0031 a análisis: `<qué cambiar>`". La firma se anula y hay que firmar de
    nuevo cuando vuelva.

### Paso 8 · Publicar y cerrar (arq-manager)

- **Le pedís:** "Publicá la devolución del PRY-2026-0031".
- **Hace solo:** te muestra la devolución y, si hay condiciones, las sub-tasks de seguimiento que va a crear. Te da el
  comentario corto para pegar en la plataforma y te dice si corresponde escalar a RFC en Product Brain.
- **Confirmás y ejecutás vos:** los comandos `--apply` de la devolución y del seguimiento, el comentario pegado en la
  plataforma y **el click en Aprobar o Rechazar**.
- **Al final:** "Ya hice el click, cerrá el PRY-2026-0031". Pasa a `cerrado` y, con un último `arq jira ... --apply`,
  la épica queda en Done.

### Paso 9 · Plazo vencido (arq-manager)

- **Le pedís:** "Venció el plazo del PRY-2026-0031".
- **Hace solo:** pasa a `propuesta-rechazo` y redacta el mensaje de cierre.
- **Ejecutás vos:** la publicación del mensaje, el rechazo en la plataforma (con el motivo y el link al ticket) y el
  cierre.

## 5. Lo que el agente nunca hace

- **Escribir en Jira por su cuenta.** Siempre te da el comando y lo corrés vos.
- **Aprobar o rechazar en la plataforma PRY.**
- **Decidir la clasificación** sin tu confirmación.
- **Firmar.**
- **Publicar texto libre al requirente:** solo sale lo que sigue una plantilla, en el estado correcto y una sola vez.
- **Opinar por Cloud, Seguridad o FinOps.**
- **Asignar tareas o comentar en Jira** por fuera del ticket del requirente.

## 6. Seguimiento diario

| Querés saber | Le pedís al agente | O corrés vos |
|---|---|---|
| En qué estado está un pedido y quién tiene la pelota | "¿Cómo está el PRY-2026-0031?" | `arq show PRY-2026-0031` |
| Cómo va en Jira: tareas hechas, en curso y pendientes, con su responsable | "Mostrame el tablero del PRY-2026-0031" | `arq ver PRY-2026-0031` |
| Cuándo vence el plazo | "¿Cuándo vence el PRY-2026-0031?" | `arq timebox PRY-2026-0031` |

`arq ver` marca cada tarea con ✔ hecha, ◐ en curso y ○ por hacer. En una terminal, las claves de Jira se pueden
clickear. Las tareas avanzan solas cada vez que se corre `arq jira ... --apply`: las cumplidas pasan a Done y la
siguiente a En curso. Nunca se reabre nada.

**Después de cada paso que cambia algo, el agente commitea el repo de reviews.** Ese historial es el registro de qué
se decidió y cuándo.

## 7. Cuando algo falla

| Mensaje o situación | Qué hacer |
|---|---|
| "No se encontró a `<email>` en Jira" | Pedir que den de alta al requirente en Jira y correr el mismo comando |
| "Jira rechazó el reporter" | Pedir para la cuenta el permiso *Modify reporter* en PEHD y repetir |
| El comando falló a la mitad | Correr el mismo comando otra vez: retoma sin duplicar |
| "Sin transición a Done" o "Sin transición a En curso" | Mover esas tareas a mano en Jira; el workflow no tiene esa transición |
| El agente dice que el mensaje no sigue la plantilla | No forzarlo: pedirle que lo rehaga sobre la plantilla |
| "Transición inválida" | El pedido no está en el estado que hace falta para ese paso: preguntale al agente en qué estado está y qué falta |
| Alguien editó la descripción de una tarea en Jira | Se va a pisar en el próximo `--apply`. Las notas van en comentarios |
| Renombraste una tarea en Jira | No pasa nada: `arq` la reconoce por un identificador interno, no por el título |
