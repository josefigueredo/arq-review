# Triage de pedidos PRY

Lo corre quien coordina (`arq-manager`). Se contesta sí o no, sin conocimiento técnico.
**Un solo "sí" → nivel `complejo`.** Todo "no" → nivel `simple`. Ante la duda, contestar "sí".

| ID | Pregunta |
|---|---|
| `multi_cuenta` | ¿Toca más de una cuenta, empresa o vertical? |
| `migracion` | ¿Es una migración o mueve datos existentes? |
| `fecha_comprometida` | ¿La fecha es comprometida (no negociable)? |
| `otros_equipos` | ¿Involucra a otros equipos además del que pide? |
| `datos_sensibles_o_ia` | ¿Incluye datos de clientes o personales, o servicios de IA externos? |
| `larga_o_productiva` | ¿Dura más de 3 meses o queda productivo? |

Uso: `arq triage PRY-2026-0028 --answers "multi_cuenta=no,migracion=no,fecha_comprometida=no,otros_equipos=no,datos_sensibles_o_ia=no,larga_o_productiva=no"`
