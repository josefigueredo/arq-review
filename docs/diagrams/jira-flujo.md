# Jira: boards, orden de ejecución y secuencia

Estado al 2026-10-08, con los pedidos reales PRY-2026-0028 y PRY-2026-0026 (nivel `complejo`).

## 1. Boards PLATE y PEHD: issues, jerarquía y orden de ejecución

- Cada issue: **número de orden de ejecución · clave de Jira · nombre**.
- El anidamiento muestra la jerarquía de Jira: épica → historia → sub-task.
- Las flechas sólidas son la **precedencia** (1 → 8): un paso empieza cuando termina el anterior.
- Las punteadas son los vínculos con el ticket del requirente: el paso 3 lo crea y lo linkea con `Relates`; en el paso 4
  se le pide información y el requirente responde ahí.
- La historia opcional "Validación técnica" (`--con-validacion`) no se creó en ninguno de los dos pedidos.

```mermaid
%%{init: {"flowchart": {"subGraphTitleMargin": {"top": 6, "bottom": 22}}}}%%
flowchart LR
    subgraph PLATE["Board PLATE"]
        direction TB
        subgraph E28["Épica PLATE-614 · PRY-2026-0028 PoC modelos IA Locales"]
            direction TB
            subgraph S28a["PLATE-615 · Intake y triage"]
                A1["1 · PLATE-616<br/>Normalizar pedido"]
                A2["2 · PLATE-617<br/>Triage"]
                A3["3 · PLATE-626<br/>Abrir ticket del requirente y plazo"]
            end
            subgraph S28b["PLATE-619 · Análisis y opciones"]
                A4["4 · PLATE-620<br/>Gap check de input mínimo"]
                A5["5 · PLATE-621<br/>Análisis vs constraints"]
                A6["6 · PLATE-622<br/>Opciones y recomendación"]
            end
            subgraph S28c["PLATE-623 · Decisión y comunicación"]
                A7["7 · PLATE-624<br/>Revisión y firma"]
                A8["8 · PLATE-625<br/>Publicar devolución"]
            end
        end
        subgraph E26["Épica PLATE-627 · PRY-2026-0026 Product Brain"]
            direction TB
            subgraph S26a["PLATE-628 · Intake y triage"]
                B1["1 · PLATE-629<br/>Normalizar pedido"]
                B2["2 · PLATE-630<br/>Triage"]
                B3["3 · PLATE-631<br/>Abrir ticket del requirente y plazo"]
            end
            subgraph S26b["PLATE-632 · Análisis y opciones"]
                B4["4 · PLATE-633<br/>Gap check de input mínimo"]
                B5["5 · PLATE-634<br/>Análisis vs constraints"]
                B6["6 · PLATE-635<br/>Opciones y recomendación"]
            end
            subgraph S26c["PLATE-636 · Decisión y comunicación"]
                B7["7 · PLATE-637<br/>Revisión y firma"]
                B8["8 · PLATE-638<br/>Publicar devolución"]
            end
        end
    end

    subgraph PEHD["Board PEHD"]
        direction TB
        T28["PEHD-86 · Tarea<br/>PRY-2026-0028 · PoC modelos IA Locales<br/>reporter: Juan Pablo Fernández"]
        T26["PEHD-87 · Tarea<br/>PRY-2026-0026 · Product Brain<br/>reporter: Gabriel Colman"]
    end

    A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7 --> A8
    B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7 --> B8

    A3 -. "crea + Relates PLATE-614" .-> T28
    A4 -. "pedido de información" .-> T28
    T28 -. "respuesta" .-> A4
    A8 -. "devolución" .-> T28
    B3 -. "crea + Relates PLATE-627" .-> T26
    B4 -. "pedido de información" .-> T26
    T26 -. "respuesta" .-> B4
    B8 -. "devolución" .-> T26
```

## 2. Secuencia ideal: creación y actualización hasta el cierre

Camino feliz de un pedido, desde que entra a la plataforma PRY hasta que se cierra con un "aprobar con condiciones".
Cada `--apply` lo corre una persona; cada paso que cambia el review se commitea en `arq-reviews`. El estado de las
tareas en PLATE se mueve a mano (todavía no hay transición automática).

```mermaid
sequenceDiagram
    autonumber
    actor Req as Requirente
    participant PRY as Plataforma PRY
    actor EM as Coordinación<br/>(arq-manager)
    actor Arq as Architect<br/>(arq-architect)
    actor Firma as Firmante
    participant CLI as arq CLI
    participant Git as arq-reviews (git)
    participant PLATE as Jira PLATE
    participant PEHD as Jira PEHD

    Req->>PRY: carga el pedido PRY-AAAA-NNNN
    PRY-->>EM: pedido pendiente de Arquitectura

    rect rgba(120, 160, 220, 0.12)
        Note over EM,PEHD: Intake (historia "Intake y triage")
        EM->>CLI: arq new (pedido textual, contacto, head)
        CLI->>Git: reviews/PRY.md · estado recibido
        EM->>CLI: arq triage --answers (confirmadas por la persona)
        CLI->>Git: nivel · estado triado
        EM->>CLI: arq jira --apply
        CLI->>PLATE: crea épica, historias y sub-tasks (labels pry/nivel/track, ID estable arq.node)
        CLI->>PEHD: crea el ticket a nombre del requirente (reporter) y suma al head (watcher)
        CLI->>PEHD: labels + link Relates a la épica
        CLI->>PLATE: descripción de la épica = resumen del review
        CLI->>Git: epica, jsm, jsm_listo · journal
        EM->>CLI: arq timebox
        CLI->>Git: vence (10 días hábiles)
    end

    rect rgba(220, 170, 90, 0.12)
        Note over Arq,PEHD: Gap check (sub-task "Gap check de input mínimo")
        loop hasta completar el input mínimo
            Arq->>CLI: arq set faltantes + análisis preliminar
            CLI->>Git: estado esperando-info · borrador del pedido de información
            EM->>CLI: arq jsm --public --template jsm-pedido-info --apply
            CLI->>PEHD: comentario con las preguntas concretas
            EM->>CLI: arq jira --apply
            CLI->>PLATE: actualiza la descripción de la épica (faltantes, hallazgos)
            Req->>PEHD: responde en su ticket
        end
        Arq->>CLI: arq set faltantes= (vacío) · arq state --to en-analisis
        CLI->>Git: estado en-analisis
    end

    rect rgba(120, 190, 140, 0.12)
        Note over Arq,PLATE: Análisis (sub-tasks "Análisis vs constraints" y "Opciones y recomendación")
        Arq->>Git: evaluación por componente, original + 2 opciones, recomendación, condiciones, señales
        Arq->>CLI: arq set veredicto=aprobar-con-condiciones · arq state --to en-firma
        CLI->>Git: estado en-firma · borradores de devolución y comentario PRY
        EM->>CLI: arq jira --apply
        CLI->>PLATE: la épica muestra el análisis y el veredicto propuesto
    end

    rect rgba(190, 140, 210, 0.12)
        Note over Firma,PEHD: Decisión (sub-tasks "Revisión y firma" y "Publicar devolución")
        Firma->>Git: revisa reviews/PRY.md
        Firma->>CLI: arq set firmante · arq state --to publicado
        CLI->>Git: estado publicado
        EM->>CLI: arq jsm --public --template jsm-devolucion --apply
        CLI->>PEHD: devolución con recomendaciones y condiciones
        EM->>CLI: arq seguimiento "condición" --apply
        CLI->>PLATE: una sub-task por condición bajo "Decisión y comunicación"
        EM->>PRY: pega el comentario corto
        Firma->>PRY: click en Aprobar (una persona, nunca el agente)
        EM->>CLI: arq state --to cerrado --resultado condicionado
        CLI->>Git: estado cerrado
        EM->>CLI: arq jira --apply
        CLI->>PLATE: la épica queda con el veredicto final
    end

    Note over CLI,PEHD: arq ver PRY muestra en cualquier momento el ticket y el árbol con su estado
```
