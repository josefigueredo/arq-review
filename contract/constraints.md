# Constraints de Arquitectura

Formato fijo: `### C-<AREA>-<NN> · <título>` y los cinco campos. Severidad: `bloqueante | condicionante | recomendación`.
Validar con `arq lint`. El architect cita el ID en cada hallazgo, por ejemplo `[C-PLAT-01]`.

### C-PLAT-01 · Recursos solo vía platform
- **Regla:** Todo recurso de cómputo, datos o red se aprovisiona desde platform. No se crean recursos por consola ni por IaC propia fuera de platform.
- **Severidad:** bloqueante
- **Por qué:** Gobierno, inventario, costos imputables y acceso unificado.
- **Cómo verificar:** El pedido nombra la aplicación, scope o servicio de platform, o dice cómo se va a aprovisionar. Si pide acceso directo a la consola de AWS o crear recursos a mano, incumple.
- **Excepción:** Solo con un ADR firmado por Arquitectura y Cloud.

### C-IDP-01 · IdP platform
- **Regla:** La plataforma de desarrollo interna (IdP) es platform. Aplicaciones, despliegues y parámetros se gestionan desde ahí.
- **Severidad:** bloqueante
- **Por qué:** Una sola puerta para el ciclo de vida de las aplicaciones.
- **Cómo verificar:** El ciclo de vida descrito (build, deploy, parámetros) pasa por platform.
- **Excepción:** Solo con un ADR firmado por Arquitectura.

### C-CLD-01 · AWS como única cloud
- **Regla:** Toda la infraestructura corre en AWS.
- **Severidad:** bloqueante
- **Por qué:** Contratos, seguridad y operación consolidados en un solo proveedor.
- **Cómo verificar:** No aparecen otros proveedores de cloud. Los SaaS se evalúan aparte, como señal para Seguridad y FinOps.
- **Excepción:** Solo con un ADR firmado por Arquitectura, Cloud y FinOps.
