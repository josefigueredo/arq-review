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
Si quien firma pide cambios: `arq state PRY-AAAA-NNNN --to en-analisis`. Eso anula la firma, y el veredicto y los
faltantes solo se pueden cambiar ahí; al volver a `en-firma` hay que firmar de nuevo.

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
