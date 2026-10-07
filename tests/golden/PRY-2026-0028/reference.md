---
pry: PRY-2026-0028
nombre: PoC modelos IA Locales
contacto: requester@example.com
head: reviewer@example.com
estado: esperando-info
nivel: simple
epica: ARQ-1
jsm: JSM-1
jsm_listo: si
vence: 2026-10-21
firmante:
resultado:
faltantes: hipotesis_medible, duracion_y_baja, costo_estimado, via_aprovisionamiento, responsable
componente_debil: costo
senales: finops
veredicto:
---

## Pedido original

Habilitar una instancia G6e.xlarge L40S de 44 GiB de VRAM para validar que modelos locales reducen el costo frente a
Cursor y GitHub Copilot.

## Lo que entendimos

Plataforma quiere una GPU en AWS para correr modelos de IA propios y comparar su costo contra las licencias SaaS de
asistentes de código `[pedido]`.

## Input faltante

- `hipotesis_medible`: no hay métrica, valor actual ni umbral; "reducir el costo" no se puede refutar `[pedido]`.
- `duracion_y_baja`: no dice cuánto dura la PoC ni cuándo se da de baja la instancia `[pedido]`.
- `costo_estimado`: no hay costo mensual de la instancia ni del gasto SaaS actual `[pedido]`.
- `via_aprovisionamiento`: no dice si la instancia se crea desde platform `[C-PLAT-01]`.
- `responsable`: no hay responsable del recurso mientras exista `[pedido]`.

## Análisis preliminar (sin veredicto)

| Componente | Estado | Hallazgo |
|---|---|---|
| costo | débil | GPU dedicada sin horario ni fecha de baja; del orden de US$1.3k/mes si corre 24/7 `[verificar]` |
| aprovisionamiento | débil | Falta confirmar que pasa por platform `[C-PLAT-01]` |
| computo | ok | La L40S tiene 48 GB de VRAM, no 44 GiB `[verificar]` |

La hipótesis compara productos de IDE por asiento contra inferencia cruda: el business case tiene que medir
equivalencia funcional, no solo costo `[supuesto]`.

## Señales para otros sectores (sin veredicto)

- ⚠ FinOps podría observar: costo de una GPU encendida sin horario ni presupuesto con alerta, porque no hay fecha de
  baja `[pedido]`.
