# Constraints de Arquitectura

Formato fijo: `### C-<AREA>-<NN> · <título>` y los cinco campos. Severidad: `bloqueante | condicionante | recomendación`.
Validar con `arq lint`. El architect cita el ID en cada hallazgo, por ejemplo `[C-PLAT-01]`.

Una **bloqueante** violada sin solución lleva a rechazar o a proponer opciones que la cumplan; una **condicionante**,
a aprobar con condiciones; una **recomendación** va a la sección de recomendaciones.

## Plataforma

### C-PLAT-01 · Recursos solo vía platform
- **Regla:** Todo recurso de cómputo, datos o red se aprovisiona desde platform. No se crean recursos por consola ni por IaC propia fuera de platform.
- **Severidad:** bloqueante
- **Por qué:** Gobierno, inventario, costos imputables y acceso unificado.
- **Cómo verificar:** El pedido nombra la aplicación, scope o servicio de platform, o dice cómo se va a aprovisionar. Si pide acceso directo a la consola de AWS o crear recursos a mano, incumple.
- **Excepción:** Los servicios gestionados de AWS que platform todavía no ofrece (hoy: Amazon Bedrock) se habilitan por cuenta a través de Cloud, y el análisis del PRY registra la excepción con el servicio, la cuenta y el motivo. Cualquier otro caso, solo con un ADR firmado por Arquitectura y Cloud.

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

## Identidad y acceso

### C-IAM-01 · Acceso humano solo por SSO
- **Regla:** Las personas acceden a las cuentas de AWS solo por el SSO corporativo. No se crean usuarios IAM con credenciales de larga duración.
- **Severidad:** bloqueante
- **Por qué:** Las credenciales de larga duración se filtran, no rotan y no se pueden auditar por persona.
- **Cómo verificar:** El pedido no menciona usuarios IAM, access keys ni credenciales compartidas para personas.
- **Excepción:** Solo con un ADR firmado por Arquitectura y Seguridad.

### C-IAM-02 · Acceso entre cuentas por roles
- **Regla:** El acceso entre cuentas se hace con roles asumibles de mínimo privilegio, nunca con claves compartidas.
- **Severidad:** bloqueante
- **Por qué:** Un rol asumible deja traza, se revoca en un lugar y limita el alcance; una clave compartida no.
- **Cómo verificar:** Si el pedido cruza cuentas (por ejemplo, una migración entre cuentas), dice qué rol se asume y con qué permisos.
- **Excepción:** Solo con un ADR firmado por Arquitectura y Seguridad.

## Datos

### C-DAT-01 · Clasificación de datos declarada
- **Regla:** Todo dato que el pedido mueve o procesa tiene clasificación declarada: público, interno, confidencial o personal.
- **Severidad:** condicionante
- **Por qué:** Sin clasificación no se puede decidir cifrado, residencia ni si el dato puede ir a un modelo de IA.
- **Cómo verificar:** El pedido nombra los datos involucrados y su clasificación.
- **Excepción:** No aplica: sin clasificación, la aprobación queda condicionada a declararla.

### C-DAT-02 · Residencia de datos personales y de clientes
- **Regla:** Los datos personales y de clientes no salen de las regiones de AWS aprobadas.
- **Severidad:** bloqueante
- **Por qué:** Obligaciones legales y contractuales sobre dónde viven los datos.
- **Cómo verificar:** El pedido dice en qué región se guardan y procesan los datos personales o de clientes, incluidos los servicios de IA que los reciben.
- **Excepción:** Solo con un ADR firmado por Arquitectura y Seguridad, con aval legal.

### C-DAT-03 · Cifrado en reposo y en tránsito
- **Regla:** Los datos se cifran en reposo (KMS) y en tránsito (TLS).
- **Severidad:** bloqueante
- **Por qué:** Es la base de protección que exigen Seguridad y las auditorías.
- **Cómo verificar:** El pedido usa servicios con cifrado habilitado y comunicaciones por TLS; si no lo dice, se pide.
- **Excepción:** Solo con un ADR firmado por Arquitectura y Seguridad.

### C-DAT-04 · Migraciones con backup y rollback
- **Regla:** Toda migración tiene un backup verificado y un plan de rollback probado antes del corte.
- **Severidad:** condicionante
- **Por qué:** Una migración sin vuelta atrás convierte cualquier error en pérdida de datos o caída larga.
- **Cómo verificar:** El pedido describe el backup, cómo se verifica, el rollback y el criterio para activarlo.
- **Excepción:** No aplica: sin backup y rollback, la aprobación queda condicionada a presentarlos.

## IA y modelos

### C-IA-01 · Modelos desde servicios aprobados
- **Regla:** Los modelos de IA se consumen desde servicios aprobados (por ejemplo, Amazon Bedrock en cuentas aprobadas). Un proveedor nuevo pasa por Seguridad.
- **Severidad:** condicionante
- **Por qué:** Controlar qué proveedores reciben datos y bajo qué contrato.
- **Cómo verificar:** El pedido nombra el servicio y la cuenta desde donde se consume el modelo.
- **Excepción:** Un proveedor nuevo, solo con aprobación de Seguridad registrada en el PRY.

### C-IA-02 · Datos sensibles y modelos de IA
- **Regla:** No se mandan datos confidenciales ni personales a un modelo de IA sin clasificación (C-DAT-01) y aprobación de Seguridad.
- **Severidad:** bloqueante
- **Por qué:** Un prompt es una transferencia de datos al proveedor del modelo.
- **Cómo verificar:** Si el pedido usa IA, dice qué datos recibe el modelo y su clasificación.
- **Excepción:** Solo con aprobación de Seguridad registrada en el PRY.

### C-IA-03 · GPU con apagado programado
- **Regla:** Las instancias GPU tienen apagado programado o escalan a cero cuando no se usan.
- **Severidad:** condicionante
- **Por qué:** Una GPU encendida sin uso es el gasto ocioso más caro de la cuenta.
- **Cómo verificar:** El pedido dice el horario de uso y cómo se apaga la instancia fuera de él.
- **Excepción:** Uso 24/7 justificado con métricas de utilización, aprobado por FinOps.

## Red

### C-NET-01 · Sin exposición directa a internet
- **Regla:** Nada se expone directo a internet; el ingreso es por un balanceador o gateway gestionado.
- **Severidad:** bloqueante
- **Por qué:** Un solo punto de entrada controlado (WAF, TLS, autenticación) en lugar de instancias expuestas.
- **Cómo verificar:** El pedido no pide IPs públicas en instancias ni puertos abiertos a internet.
- **Excepción:** Solo con un ADR firmado por Arquitectura, Cloud y Seguridad.

### C-NET-02 · Conectividad privada entre cuentas
- **Regla:** La conectividad entre cuentas usa mecanismos privados aprobados (PrivateLink, Transit Gateway), no IPs públicas.
- **Severidad:** condicionante
- **Por qué:** El tráfico entre cuentas no tiene por qué pasar por internet.
- **Cómo verificar:** Si el pedido conecta servicios de cuentas distintas, dice por qué mecanismo.
- **Excepción:** Solo con aprobación de Cloud registrada en el PRY.

## Costos

### C-FIN-01 · Tags de costo obligatorios
- **Regla:** Todo recurso lleva los tags de costo: empresa, área, PRY y owner.
- **Severidad:** bloqueante
- **Por qué:** Sin tags no hay costo imputable ni dueño a quien preguntar.
- **Cómo verificar:** El pedido nombra la empresa, el área y el owner, y el aprovisionamiento aplica los tags.
- **Excepción:** No aplica.

### C-FIN-02 · Presupuesto con alerta para recursos temporales
- **Regla:** Todo recurso temporal (PoC) tiene un presupuesto con alerta en AWS Budgets.
- **Severidad:** condicionante
- **Por qué:** Un PoC olvidado sigue costando; la alerta lo hace visible antes de que sea caro.
- **Cómo verificar:** El pedido dice el presupuesto mensual y quién recibe la alerta.
- **Excepción:** No aplica: sin presupuesto, la aprobación queda condicionada a definirlo.

### C-FIN-03 · Business case contra la línea base
- **Regla:** El business case compara el costo total (infraestructura, operación y esfuerzo) contra la línea base actual, no solo el costo de infraestructura.
- **Severidad:** recomendación
- **Por qué:** Comparar solo infraestructura esconde el costo de operar y mantener la alternativa.
- **Cómo verificar:** El pedido muestra la línea base actual y el costo total de la propuesta.
- **Excepción:** No aplica.

## Operación y ciclo de vida

### C-OPS-01 · Observabilidad mínima para productivo
- **Regla:** Nada pasa a productivo sin logs, métricas y alertas mínimas.
- **Severidad:** condicionante
- **Por qué:** Lo que no se observa no se puede operar ni diagnosticar.
- **Cómo verificar:** Si el pedido queda productivo, dice qué se loguea, qué se mide y qué alerta y a quién.
- **Excepción:** No aplica a PoC con fecha de baja; sí a todo lo productivo.

### C-OPS-02 · Productivo separado de no productivo
- **Regla:** Productivo y no productivo no comparten cuenta.
- **Severidad:** condicionante
- **Por qué:** Un error en un entorno de prueba no puede afectar a productivo.
- **Cómo verificar:** El pedido dice en qué cuenta y entorno corre cada parte.
- **Excepción:** Solo con aprobación de Cloud registrada en el PRY.

### C-LIF-01 · PoC no pasa a productivo sin revisión
- **Regla:** Lo que nace como PoC no pasa a productivo sin una nueva revisión de Arquitectura.
- **Severidad:** bloqueante
- **Por qué:** Un PoC se aprueba con condiciones de prueba; productivo exige otras.
- **Cómo verificar:** Si el pedido es un PoC, la aprobación lo dice y nombra la fecha de baja.
- **Excepción:** No aplica: pasar a productivo requiere un PRY nuevo.

### C-LIF-02 · Dependencias acordadas por escrito
- **Regla:** Toda dependencia de otro equipo tiene dueño y fecha acordada por escrito.
- **Severidad:** condicionante
- **Por qué:** Una dependencia sin dueño ni fecha es el riesgo de calendario más común en una fecha comprometida.
- **Cómo verificar:** El pedido nombra cada equipo del que depende, la persona responsable y la fecha acordada.
- **Excepción:** No aplica: sin acuerdo escrito, la aprobación queda condicionada a conseguirlo.
