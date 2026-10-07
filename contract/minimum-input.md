# Input mínimo por nivel

El test: cada afirmación del pedido tiene que poder apuntar a un artefacto concreto (número, componente, diagrama o
métrica). Si no puede, es prosa y cuenta como faltante. El nivel `complejo` exige todo lo de `simple` y además lo suyo.
El architect anota los IDs que faltan en el frontmatter (`faltantes: id1, id2`).

## simple
- `problema` — Qué problema concreto se resuelve y para quién.
- `hipotesis_medible` — Métrica, valor actual y umbral que valida o refuta la hipótesis.
- `recursos` — Tipo, tamaño y cantidad de cada recurso.
- `duracion_y_baja` — Cuánto dura y en qué fecha se da de baja.
- `costo_estimado` — Costo mensual estimado y cómo se calculó.
- `responsable` — Persona responsable del recurso mientras exista.
- `via_aprovisionamiento` — Cómo se aprovisiona (aplicación, scope o servicio de platform).

## complejo
- `diagrama_c4` — Diagrama C4 de nivel 1 y 2 (contexto y contenedores), revisable.
- `flujos_datos` — Flujos de datos y clasificación de la información que circula.
- `cuentas_entornos` — Cuentas y entornos de origen y destino.
- `rollback` — Plan de vuelta atrás y criterio para activarlo.
- `dependencias` — Dependencias con otros equipos, cada una con dueño.
- `rnf` — Requisitos no funcionales: disponibilidad, latencia, RPO/RTO si aplica.
