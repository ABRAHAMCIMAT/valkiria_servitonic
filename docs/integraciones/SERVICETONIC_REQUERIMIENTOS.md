# Requerimientos de ServiceTonic para la integración con el Help Desk Multiagente

> **Estado 23/10/2026:** 🟡 Recibidos `idProject` (1), agente técnico, nombres de
> campos, prioridades y licencia ([hallazgos](SERVICETONIC_HALLAZGOS.md)). Pendientes:
> estados completos, valores de los desplegables, campo para el ID de conversación y
> que el proveedor desbloquee la creación de tickets por API. Ver
> [contrato API revisado](SERVICETONIC_API.md) y
> [estado consolidado](../ESTADO_DESARROLLO.md).

> **Para:** administrador de ServiceTonic de la organización y/o contacto técnico del proveedor
> **De:** equipo del Sistema Multiagente de Help Desk
> **Contexto:** [Plan de Fase 2, incremento I0](../PLAN_FASE2_GOOGLE_CLOUD.md#i0--descubrimiento-y-prerrequisitos)
> **Fecha:** 12 de octubre de 2026

> Referencia funcional pública:
> [ServiceTonic — aplicación de ticketing](https://www.servicetonic.com/es/ticketing-aplicacion/).
> La página confirma ticketing omnicanal, automatización, SLA, reporting, base
> de conocimiento e integraciones. No sustituye la documentación técnica de la
> API, que continúa siendo un prerrequisito bloqueante.

---

## 1. Qué vamos a construir

Un asistente conversacional (chat) que atiende a los empleados y usa
ServiceTonic como **sistema de registro**. Desde el chat, el asistente:

1. **Crea tickets** (incidentes y solicitudes) con categoría, prioridad y grupo asignados automáticamente.
2. **Consulta el estado** de los tickets del usuario ("¿cómo va mi ticket?").
3. **Actualiza tickets**: cambia el estado, agrega notas y registra la resolución.
4. **Escala a un técnico** (Nivel 2/3) dejando un resumen del diagnóstico como nota interna.
5. **Responde preguntas** usando los artículos de la **base de conocimiento**.
6. **Identifica al manager** del solicitante para pedir aprobaciones (las aprobaciones se responden en Microsoft Teams).

La integración corre en **Google Cloud (Cloud Run)** y llama a la **API REST** de
ServiceTonic como un usuario técnico. No se instala nada dentro de ServiceTonic.

---

## 2. Resumen de lo que necesitamos

Prioridad: **B** = bloqueante (sin esto no podemos empezar) · **N** = necesario para la versión completa · **D** = deseable.

| # | Requerimiento | Prioridad | Sección |
|---|---------------|-----------|---------|
| 1 | Documentación de la API REST de su versión (OpenAPI/Swagger o equivalente) | B | 3 |
| 2 | Instancia de pruebas (sandbox) separada de producción | B | 4 |
| 3 | Usuario técnico de integración y método de autenticación | B | 5 |
| 4 | Operaciones de tickets: crear, consultar, buscar por solicitante, actualizar, agregar notas | B | 6 |
| 5 | Catálogos: estados, prioridades, categorías, procesos y grupos | B | 7 |
| 6 | Campo para una referencia externa (ID de conversación) buscable por API | N | 6.6 |
| 7 | Búsqueda de contactos/usuarios por correo y su manager | N | 8 |
| 8 | Acceso a la base de conocimiento por API (o exportación) | N | 9 |
| 9 | Eventos/webhooks de cambio de estado | D | 10 |
| 10 | Información de aprobaciones nativas de ServiceTonic | D | 11 |
| 11 | Datos de prueba en el sandbox | B | 12 |
| 12 | Requisitos de red, límites y seguridad | B | 13 |

---

## 3. Documentación de la API (bloqueante)

Necesitamos la referencia de la API **de la versión que tiene instalada la organización**:

- [ ] **Versión** de ServiceTonic y de la API (por ejemplo `/api/v1`).
- [ ] **Especificación OpenAPI/Swagger** o, en su defecto, una colección de Postman o la documentación PDF del proveedor.
- [ ] **URL base** de la API en el sandbox y en producción (p. ej. `https://<cliente>.myservicetonic.com/api/v1`).
- [ ] **Formato** de solicitudes y respuestas (JSON o XML), codificación (UTF-8: el contenido lleva acentos y "ñ"), formato de fechas y **zona horaria**.
- [ ] **Paginación y filtros**: cómo listar resultados (tamaño de página, cursor u offset) y filtrar por campos (solicitante, estado, fecha de modificación).
- [ ] **Formato de errores**: códigos HTTP que devuelve y estructura del cuerpo de error.
- [ ] **Política de versiones**: cómo se avisan los cambios incompatibles y cuánto tiempo conviven dos versiones.
- [ ] ¿La API requiere un **módulo o licencia adicional**? ¿Está habilitada en nuestra instancia?

---

## 4. Entornos (bloqueante)

- [ ] **Instancia de pruebas (sandbox)** con la misma configuración que producción (procesos, formularios, categorías y grupos), pero sin datos reales.
- [ ] Confirmación de que podemos **crear y modificar tickets en el sandbox** libremente durante el desarrollo y las pruebas automáticas.
- [ ] Procedimiento para **mantener sincronizada la configuración** del sandbox con producción cuando cambien los catálogos.

---

## 5. Autenticación y usuario técnico (bloqueante)

- [ ] **Método de autenticación** de la API: token de API, usuario/contraseña (Basic), OAuth 2.0 (*client credentials*) u otro.
- [ ] **Usuario técnico** dedicado a la integración (p. ej. `integracion.helpdesk-ia`), uno para sandbox y otro para producción. No debe ser una cuenta personal.
- [ ] **Permisos mínimos** de ese usuario:
  - crear, leer y actualizar tickets de los procesos de incidentes y solicitudes;
  - agregar notas internas y públicas;
  - leer contactos/usuarios (incluido su manager);
  - leer la base de conocimiento (solo artículos publicados).
  - **No** necesita: administración, borrado de tickets ni acceso a otros módulos.
- [ ] **Vigencia y rotación** de las credenciales: ¿caducan? ¿cómo se renuevan sin interrumpir el servicio?
- [ ] ¿Cómo aparecen en ServiceTonic las acciones del usuario técnico (auditoría)? ¿Se puede registrar el ticket **a nombre del solicitante** aunque lo cree la integración?

Las credenciales se guardarán en **Google Secret Manager**. Les pedimos enviarlas por un canal seguro, nunca por correo en texto plano.

---

## 6. Tickets (bloqueante)

Para cada operación necesitamos el **endpoint, el método HTTP, los campos obligatorios y un ejemplo de solicitud y respuesta**.

### 6.1 Crear ticket

El asistente enviará estos datos. Indíquennos el **nombre del campo en ServiceTonic** y si es obligatorio:

| Dato del asistente | Ejemplo | Campo en ServiceTonic |
|--------------------|---------|-----------------------|
| Título / resumen | "Usuario no puede acceder al CRM" | ? |
| Descripción | Texto original del usuario | ? |
| Tipo / proceso | Incidente o Solicitud de servicio | ? |
| Categoría y subcategoría | Acceso a cuentas / Bloqueo | ? |
| Prioridad (o impacto + urgencia) | P2 (impacto 2, urgencia 2) | ? |
| Grupo / equipo asignado | IT Service Desk | ? |
| Solicitante | correo del empleado | ? |
| Origen / canal | "Asistente IA" | ? |
| Referencia externa | ID de conversación (ver 6.6) | ? |

- [ ] ¿Qué devuelve la creación: **ID interno**, **número visible** del ticket o ambos?
- [ ] ¿El número visible tiene un formato fijo (prefijo, longitud)?
- [ ] ¿Distintos procesos o formularios exigen **campos obligatorios distintos**?

### 6.2 Consultar un ticket

- [ ] Obtener un ticket por **número visible** y/o por **ID interno**.
- [ ] La respuesta debe incluir: estado, prioridad, categoría, grupo y técnico asignado, fechas de creación y última modificación, y las notas.

### 6.3 Listar los tickets de un solicitante

- [ ] Filtrar por **solicitante** (por correo o ID de contacto) y por **estado** (abiertos/cerrados), ordenados por fecha de modificación.

### 6.4 Actualizar un ticket

- [ ] Cambiar **estado**, **prioridad**, **grupo asignado** y **técnico asignado**.
- [ ] Registrar la **resolución** al cerrar (notas de resolución, código de cierre si existe).
- [ ] ¿Qué **transiciones de estado** permite el flujo? (p. ej. ¿se puede pasar de "Nuevo" a "Resuelto" directamente?)
- [ ] ¿Se usa `PUT` (reemplazo completo) o se permite actualizar **solo algunos campos**?

### 6.5 Notas / comentarios

- [ ] Agregar una nota **interna** (solo visible para técnicos), que usaremos para el resumen de diagnóstico al escalar.
- [ ] Agregar una nota **pública** (visible para el solicitante).
- [ ] ¿Las notas públicas generan **notificación** automática al solicitante por correo? (Para no duplicar avisos con Teams).

### 6.6 Referencia externa e idempotencia (necesario)

Si una llamada falla por red, el asistente reintenta. Para **no crear tickets duplicados** necesitamos:

- [ ] Un **campo** (estándar o personalizado) donde guardar el ID de la conversación del asistente.
- [ ] Poder **buscar tickets por ese campo** mediante la API.
- [ ] Si no existe, autorización para **crear un campo personalizado** con ese fin.

### 6.7 Adjuntos (deseable)

- [ ] ¿La API permite subir adjuntos (p. ej. capturas de pantalla)? Límite de tamaño y tipos permitidos.

---

## 7. Catálogos y configuración (bloqueante)

El asistente clasifica cada caso automáticamente. Para que **solo proponga valores que existen** en ServiceTonic necesitamos los catálogos **con sus identificadores** (no solo los nombres):

- [ ] **Procesos / tipos de ticket** (incidente, solicitud, cambio, etc.) y cuáles debemos usar.
- [ ] **Estados** por proceso y sus **transiciones** permitidas.
- [ ] **Prioridades** y, si aplica, la **matriz impacto × urgencia** que las calcula.
- [ ] **Categorías y subcategorías** (árbol completo).
- [ ] **Grupos / equipos de soporte** y qué categorías atiende cada uno.
- [ ] **SLA** por prioridad (tiempos de respuesta y resolución) para informar al usuario.
- [ ] **Catálogo de servicios** (si existe): elementos para solicitudes de hardware, software y licencias.
- [ ] ¿Se pueden **obtener estos catálogos por API**? Si no, una exportación (Excel/CSV) y el procedimiento para avisarnos cuando cambien.

Con esto armamos la tabla de equivalencias del asistente ↔ ServiceTonic. Los estados del asistente son: `nuevo`, `en curso`, `en espera de aprobación`, `resuelto`, `cerrado` y `rechazado`. Necesitamos saber a qué estado de ServiceTonic corresponde cada uno.

---

## 8. Contactos, usuarios y manager (necesario)

- [ ] Buscar un **contacto/usuario por correo electrónico** (el identificador que usaremos para el empleado).
- [ ] ¿El contacto tiene **manager** o responsable? ¿Se puede leer por API?
- [ ] ¿El contacto tiene **departamento**, **ubicación** y **empresa**?
- [ ] ¿Los contactos se **sincronizan desde Active Directory / Entra ID**? Si es así, quizá tomemos el manager directamente de Entra ID.
- [ ] ¿Qué pasa si el solicitante **no existe** como contacto? ¿La integración debe crearlo o rechazar la solicitud?

---

## 9. Base de conocimiento (necesario)

- [ ] ¿La API permite **buscar artículos** por texto? ¿Y **obtener el contenido completo** de un artículo?
- [ ] Campos del artículo: ID, título, contenido (formato: texto, HTML), categoría, idioma, estado de publicación, fecha de modificación y **URL pública en el portal**.
- [ ] ¿Cómo distinguimos los artículos **publicados para usuarios finales** de los internos para técnicos?
- [ ] Si la API no expone la base de conocimiento: ¿existe una **exportación** (completa o incremental) que podamos programar cada noche?
- [ ] Volumen aproximado de artículos e idiomas.

Usaremos los artículos para responder con pasos concretos y citar el artículo de origen con su enlace al portal.

---

## 10. Eventos / webhooks (deseable)

Para avisar al usuario en Teams cuando su ticket cambie:

- [ ] ¿ServiceTonic puede **enviar notificaciones salientes** (webhooks o llamadas HTTP) cuando cambia el estado de un ticket o un técnico agrega una nota?
- [ ] ¿Cómo se **autentican** esas llamadas (firma, token, IP de origen)?
- [ ] Si no hay webhooks: confirmar que podemos **consultar los tickets modificados desde una fecha** (filtro por fecha de modificación) para revisarlos cada pocos minutos.

---

## 11. Aprobaciones (deseable)

Las aprobaciones (p. ej. de una laptop nueva) se pedirán al manager **en Microsoft Teams**. Necesitamos saber:

- [ ] ¿ServiceTonic tiene un **flujo de aprobación nativo**? ¿Se puede iniciar y resolver por API?
- [ ] Si lo tiene: ¿prefieren que la decisión tomada en Teams **se registre en esa aprobación nativa** (para la auditoría) o basta con un cambio de estado y una nota en el ticket?
- [ ] ¿Qué estado debe tener un ticket mientras espera la aprobación?

---

## 12. Datos de prueba en el sandbox (bloqueante)

- [ ] **3–5 contactos de prueba**, al menos uno con **manager asignado** y otro sin manager.
- [ ] **Tickets de ejemplo** en distintos estados (nuevo, en curso, resuelto, cerrado).
- [ ] **5–10 artículos de la base de conocimiento** publicados (contraseñas, desbloqueo de cuenta, VPN, licencias, solicitud de hardware).
- [ ] Permiso para que las **pruebas automáticas** creen y cierren tickets en el sandbox (se identificarán con el origen "Asistente IA – pruebas").

---

## 13. Red, límites y seguridad (bloqueante)

- [ ] ¿La instancia es **SaaS** (alojada por ServiceTonic) o **en las instalaciones** de la organización? Si es local, ¿cómo se accede desde internet (VPN, proxy, lista blanca)?
- [ ] ¿Existe una **lista blanca de IPs**? Si es así, les daremos una **IP de salida fija** de Google Cloud (Cloud NAT) para autorizarla.
- [ ] **Límites de uso** de la API (solicitudes por minuto/hora) y qué respuesta devuelve al superarlos (p. ej. HTTP 429 y encabezado `Retry-After`).
- [ ] **Disponibilidad** comprometida y **ventanas de mantenimiento** programadas.
- [ ] Versión mínima de **TLS** y certificados (¿certificado propio o de una autoridad pública?).
- [ ] **Residencia de datos** y acuerdo de tratamiento de datos: el asistente enviará a ServiceTonic el nombre, el correo y la descripción de los problemas de los empleados.
- [ ] Contacto de **soporte técnico** del proveedor para incidencias de la API y tiempo de respuesta.

---

## 14. Entregables esperados y cómo validaremos

| Entregable | Formato |
|------------|---------|
| Documentación de la API | OpenAPI, colección de Postman o PDF |
| URL del sandbox y de producción | Texto |
| Credenciales del usuario técnico (sandbox) | Canal seguro (gestor de contraseñas compartido) |
| Catálogos con IDs | Exportación CSV/Excel o endpoints de la API |
| Respuestas a las secciones 6–13 | Este documento con las casillas completadas |
| Contacto técnico | Nombre, correo y horario |

**Prueba de aceptación** (la ejecutaremos en el sandbox al recibir lo anterior):

1. Autenticarse con el usuario técnico.
2. Crear un ticket con categoría, prioridad, grupo, solicitante y referencia externa.
3. Recuperarlo por número y buscarlo por la referencia externa.
4. Listar los tickets abiertos del solicitante.
5. Agregar una nota interna y una pública.
6. Cambiar el estado a "en espera de aprobación" y después a "resuelto" con notas de resolución.
7. Leer el manager del solicitante.
8. Buscar un artículo de la base de conocimiento y leer su contenido completo.

Cuando los 8 pasos funcionen, empieza el desarrollo del adaptador (incremento I5 del plan).

---

## Anexo: correspondencia con el código del asistente

Para el equipo de desarrollo: cada operación de `TicketingPort` (plan, I1) y el requerimiento que la habilita.

| Operación del adaptador | Usada por | Requerimiento |
|-------------------------|-----------|---------------|
| `create_ticket` | Coordinador (incidente, solicitud, aprobación) | 6.1, 6.6, 7 |
| `get_ticket` | Seguimiento | 6.2 |
| `list_tickets(caller)` | Coordinador ("¿cómo va mi ticket?"); hoy lee `_tickets` en memoria | 6.3, 8 |
| `update_ticket` | Coordinador (resolución, espera de aprobación), Escalación | 6.4, 7 |
| `add_note` | Escalación (resumen a Nivel 2), Seguimiento | 6.5 |
| `search_kb` | Agente de Conocimiento (RAG) | 9 |
| `get_manager` | Coordinador (aprobaciones) | 8 |
| `unlock_account`, `reset_password`, `assign_license` | Agente de Ejecución | Se registran como tickets/notas; la ejecución real va por Entra ID (plan, I6) |
