---
pry: PRY-2026-0028
nombre: PoC modelos IA Locales
contacto: requester@example.com
head: reviewer@example.com
estado: esperando-info
nivel: complejo
epica: PLATE-614
jsm: PEHD-86
jsm_listo: si
vence: 2026-10-21
firmante:
resultado:
faltantes: hipotesis_medible, duracion_y_baja, costo_estimado, via_aprovisionamiento, responsable, diagrama_c4, cuentas_entornos
componente_debil: costo
senales: finops, cloud
veredicto:
---

## Pedido original

Habilitar una instancia G6e.xlarge L40S de 44 GiB de VRAM para validar que modelos locales reducen el costo frente a
Cursor y GitHub Copilot. El producto es cross: lo podrían consumir otras cuentas, empresas o verticales.

## Lo que entendimos

Plataforma quiere una GPU en AWS para correr modelos de IA propios, consumibles desde otras cuentas del grupo, y
comparar su costo contra las licencias SaaS de asistentes de código `[pedido]`.

## Input faltante

- `hipotesis_medible`: no hay métrica, valor actual ni umbral; "reducir el costo" no se puede refutar `[pedido]`.
- `duracion_y_baja`: no dice cuánto dura la PoC ni cuándo se da de baja la instancia `[pedido]`.
- `costo_estimado`: no hay costo mensual de la instancia ni del gasto SaaS actual `[pedido]`.
- `via_aprovisionamiento`: no dice si la instancia se crea desde platform `[C-PLAT-01]`.
- `responsable`: no hay responsable del recurso mientras exista `[pedido]`.
- `diagrama_c4`: siendo cross, falta el diagrama de dónde vive el servicio y quién lo consume `[pedido]`.
- `cuentas_entornos`: falta en qué cuenta vive y desde qué cuentas se accede, y por qué mecanismo privado `[C-NET-02]`.

## Análisis preliminar (sin veredicto)

| Componente | Estado | Hallazgo |
|---|---|---|
| costo | débil | GPU dedicada sin horario ni fecha de baja; del orden de US$1.3k/mes si corre 24/7 `[verificar]` `[C-IA-03]` |
| red | débil | Consumo desde otras cuentas sin mecanismo de conectividad definido `[C-NET-02]` |
| aprovisionamiento | débil | Falta confirmar que pasa por platform `[C-PLAT-01]` |
| computo | ok | La L40S tiene 48 GB de VRAM, no 44 GiB `[verificar]` |

La hipótesis compara productos de IDE por asiento contra inferencia cruda: el business case tiene que medir
equivalencia funcional, no solo costo `[supuesto]` `[C-FIN-03]`.

## Señales para otros sectores (sin veredicto)

- ⚠ FinOps podría observar: costo de una GPU encendida sin horario ni presupuesto con alerta, porque no hay fecha de
  baja `[pedido]`.
- ⚠ Cloud podría observar: dónde ubicar el servicio en la red para que otras cuentas lo consuman sin exponerlo a
  internet `[C-NET-01]` `[C-NET-02]`.
