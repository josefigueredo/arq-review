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
3. Leer el pedido y todos los links de documentación accesibles. Lo que no se pueda abrir se lista como `[verificar]`
   y se le pide al requirente que lo comparta.
4. **Verificar que la documentación esté vigente.** Comparar la fecha del documento adjunto con la del código del
   repo (`git log -1 -- <archivo>`, ramas recientes de `origin`, versiones Mermaid sincronizadas). Si hay una versión
   más nueva, se usa esa y se avisa en el pedido de información. En "Lo que entendimos" se deja escrito qué se revisó:
   repo, rama, commit y fecha. Lo que diga el código vence a lo que diga un diagrama.

## 1. Gap check

Para cada ID de input del nivel (`minimum-input.md`), decidir si está, citando el artefacto concreto que lo cubre. El
test: cada afirmación tiene que apuntar a un número, componente, diagrama o métrica. Si no, es prosa y falta.

`arq set PRY-AAAA-NNNN faltantes=<id1>,<id2>` (vacío si no falta nada).

- **Falta input** → `arq state PRY-AAAA-NNNN --to esperando-info`. Escribir en el review las secciones "Lo que
  entendimos", "Input faltante" y "Análisis preliminar (sin veredicto)" con los pasos 2, 3 y 7 del método, y fijar
  `arq set PRY-AAAA-NNNN componente_debil=<c> senales=<s>`. Redactar `reviews/PRY-AAAA-NNNN.jsm.md` desde
  `templates/jsm-pedido-info.md`, completando solo los placeholders y sin tocar el texto fijo (el CLI rechaza lo que
  no sigue la plantilla): por cada faltante, una pregunta **concreta para este pedido** (nunca genérica) y por qué se
  pide. `{{vence}}` es el campo `vence` de `arq show`; si está vacío, pedirle a `arq-manager` que arranque el plazo.
  Si la fecha comprometida del pedido es anterior a `vence`, ordenar las preguntas: primero las que bloquean esa
  fecha. Avisar que le toca a `arq-manager` publicarlo.
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
- Lo que lee el requirente va en tono profesional y con recomendaciones. El debate técnico crudo va como nota interna
  (`arq jsm ... --internal`, lo publica `arq-manager`) en el canal `jsm`; en el canal `software` no hay notas internas
  (todo comentario lo ve el requirente) y el debate va en la épica.
- Para tunear: `arq eval tests/golden/<PRY> reviews/<PRY>.md` contra los golden cases del repo `arq-review`. Cada
  revisión real que salga mal se convierte en un golden case nuevo. Un golden se corrige solo si cambia la evidencia,
  nunca para que pase la salida.
