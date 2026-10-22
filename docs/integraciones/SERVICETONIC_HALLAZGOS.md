# ServiceTonic — hallazgos contra la instancia Valtre

> Complementa el [contrato de la API](SERVICETONIC_API.md) con lo **comprobado** contra
> `https://valtre.myservicetonic.com/ServiceTonic` (`idProject=1`) entre el 21 y el 23 de octubre
> de 2026, y con la ayuda oficial de ServiceTonic. Copia de la especificación OpenAPI:
> [servicetonic/openapi-v1.json](servicetonic/openapi-v1.json) (idéntica en la demo del proveedor y
> en Valtre, ServiceTonic 12.0.8 / 12.0.11).

## Resumen

| Tema | Estado |
|------|--------|
| Autenticación | ✅ SHA-1 binario en Base64; token de 32 caracteres en texto plano; `Authorization: <token>` sin prefijo |
| Lectura | ✅ Responde, pero el servicio no devuelve tickets y el único contacto sale vacío (sección 4) |
| **Escritura** | ❌ **Bloqueada del lado del servidor**: `302` a `login.jsf` o `401` (sección 4). Caso abierto con el proveedor |
| Nombres internos de campos | ✅ Sección 5 |
| Prioridades | ✅ Crítica, Alta, Normal, Baja |
| Estados | 🟡 Nuevo, Abierta, En espera usuario; faltan resuelto, cerrado y espera de aprobación |
| **Cuota de la licencia** | ⚠️ **1 000 llamadas REST al mes y 50 por minuto** (sección 3) |

## Cambios en el adaptador derivados de estos hallazgos

- Las escrituras envían un multipart con una parte `files` vacía; sin cuerpo, Valtre responde
  `400 Missing start boundary`.
- `SERVICETONIC_VALUE_MAP` traduce estados y prioridades a los literales de ServiceTonic.
- `work_notes` y `resolution_notes` se registran como actuaciones (interna, y pública + solución).
- `ERR012-Expected ticket` → `get_incident()` devuelve `None`.
- La descripción y las notas se recortan para no superar el límite de la URL.
- Los errores 4xx conservan el mensaje del servidor (código de negocio) para diagnosticar.

---

## 1. Comprobado contra `valtre` (22 oct 2026)

Con el agente técnico y un script de sondeo de solo lectura (hoy cubierto por [scripts/probe_servicetonic.py](../../scripts/probe_servicetonic.py))
(solo lectura):

| Prueba | Resultado |
|--------|-----------|
| `POST /auth` | ✅ `200`. La contraseña va como **Base64 del SHA-1 binario** (la variante hexadecimal no hace falta). La respuesta es el token en **texto plano** (32 caracteres, sin JSON ni comillas) |
| Encabezado | ✅ `Authorization: <token>`, **sin** prefijo `Bearer` |
| `POST tickets/list` | `200` con `[]`: el agente **no ve ningún ticket** en el servicio 1 (o el servicio está vacío). La respuesta es un arreglo JSON directo |
| `GET tickets/{id}` | IDs 1–30, 100 y 1000 → `400 ERR012-Expected ticket` (no existe o no es visible) |
| `POST contacts/list` | `200` con `{"status":"OK","message":…,"numTotal":1,"initResult":0,"numResults":0,"itemList":[]}`: hay **1 contacto**, pero no se devuelve. Cambiar `initResult`, `logic` o pedir columnas con nombres genéricos (`Email`, `Nombre`, `Correo`…) no cambia el resultado; hacen falta los `fieldName` reales de la plantilla |
| Usuarios técnicos | `valkiria_API_Read_Only` se autentica (22 oct) y ve lo mismo: 0 tickets, 1 contacto sin devolver. `valkiria_API_Write_Only` → `401` (no está dado de alta como agente del servicio o le falta acceso a la API) |
| Límite de peticiones | ~50 peticiones seguidas → `429 ERR033-Too many requests`, **también en `GET`** (la especificación solo lo documenta en `tickets/list`). El adaptador reintenta con espera exponencial; no hay que hacer sondeos agresivos |
| Escritura (`POST tickets`, usuario `ricardo.valadez`, 22 oct) | ❌ No se ha logrado crear ningún ticket. Con un multipart **vacío** → `400 MIMEParsingException: Missing start boundary` (el servidor exige al menos una parte; el adaptador ya envía una parte `files` vacía). Con una parte (`files` u otra) → **`302` a `/ServiceTonic/login.jsf`**, aunque el mismo token lee sin problema y sin token la respuesta es `401`. Hipótesis: el usuario no tiene permiso o licencia de agente para escribir por la API, o la creación exige otra cosa que la especificación no documenta. **Hay que preguntarlo al proveedor** |
| `RSQuery` sin `orderList` | ❌ `500` (`NullPointerException` en `getOrderList()`). **Siempre** hay que enviar `fieldList`, `criterionList` y `orderList`, aunque sea vacíos |

Formatos de respuesta distintos según el recurso: `tickets/list` devuelve un arreglo;
`contacts/list`, un objeto con `itemList` y totales para la paginación. Los errores de negocio
traen un código (`ERR012-…`).

**Pendiente para terminar el descubrimiento:**
1. Las **plantillas** de ticket y de contacto (nombres internos de los campos).
2. Confirmar en la interfaz de ServiceTonic si el servicio 1 tiene tickets y si el agente
   Valkiria Valtre los puede ver (permisos o equipo del agente).
3. Si el servicio está vacío: autorización para **crear un ticket de prueba**, el único
   modo de ver por la API la estructura completa de un ticket.

---

## 2. Lo que dice la ayuda oficial (23 oct 2026)

Fuente: base de conocimiento de soporte de ServiceTonic (`support.servicetonic.com`, temas por `idTopic`).

### Dónde están los nombres internos de los campos

- **[Mostrar variables](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2101)**: en *Administración → Service Desk → Integración con Sistemas
  Externos → Mostrar variables* hay una tabla con tres columnas: **Campo** (literal), **AS (nombre
  interno del campo)** y **Variable**. Es la fuente del mapeo (`ticket_fields`, `contact_fields`).
  También aparece en *Correo → Plantillas → Mostrar variables* ([tema 2061](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2061)).
- **[Campos de sistema](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2027)**: el ticket trae Título, Prioridad y Estado; el contacto, Nombre,
  Apellido y Email. Los demás campos los crea el administrador en *Gestión de Campos*
  ([2052](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2052)); los de contactos, en *Administración → Sistema → Administración de contactos*.
- **[Estados y prioridades](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2092)**: *Administración → Service Desk → Niveles de Servicio →
  Gestión de Prioridades*. Los estados se crean en *Gestión de campos → campo "Estado"*. Por
  defecto, "Cerrado" es el único estado no vigente.
- **[Tipos de actuación](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2213)**: *Administración → Service Desk → Administración Service Desk
  → Tipos de Actuación*. Son los valores de `actionType`. Cada actuación admite como máximo 60 KB
  ([2061](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2061)); aunque el límite real lo pone antes la URL (el JSON viaja en `?rsAction=` y Tomcat acepta por defecto ~8 KB de línea de petición). El adaptador recorta la descripción del ticket y las notas a 5 000 caracteres **ya codificados** (`fit_for_url` en [servicetonic.py](../../backend/adapters/servicetonic.py)).

### Por qué los usuarios de la API no ven tickets ni contactos

[Rol Agente](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2078) (*Administración → Servicio → Agentes → Roles*) define:
- **Visibilidad de tickets**: solo los asignados al agente, los de su equipo y los personales, o
  **todos los del servicio**. Un usuario de integración necesita **todos**; si no, `tickets/list`
  sale vacío aunque existan tickets.
- **Tiquets: crear / editar / eliminar**: el usuario de integración necesita **crear y editar**.
- **Búsqueda de contactos** (módulos funcionales) y la herramienta **Contactos**: sin ellas, el
  agente no puede consultar la lista de contactos. Explicaría que `contacts/list` responda
  `numTotal: 1` con `itemList` vacío.

### API REST según la ayuda

[Webservices (API REST)](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2298): crear tickets "indicando datos de contacto, estado, prioridad,
asignación, campos personalizados", modificar tickets, crear y modificar contactos, y
traspasar comentarios y acciones. No hay más detalle que la especificación OpenAPI.

### Licencias

[Gestión de la licencia](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2094): la licencia fija cuántos agentes pueden entrar y si son
**fijos o concurrentes**. Si son concurrentes y no queda ninguna libre, o si el usuario de la
API no tiene licencia, la escritura podría rechazarse. Es una hipótesis para el `302` al login.

### Base de conocimiento

Los usuarios la consultan como **[Soluciones](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2004)**: un árbol de soluciones organizado en
**librerías**, con buscador y votos. Se administra en *Administración → Sistema → Conocimiento*
([2146](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2146)). La API no la expone, así que sigue haciendo falta la exportación.

---

## 3. Configuración real de `valtre` (capturas del 23 oct 2026)

### Licencia: cuota de llamadas a la API ⚠️

| Concepto | Valor |
|----------|-------|
| Versión | CORPORATIVA, vence el **05/11/2026** (confirmar el formato de fecha: si es día/mes, faltan dos semanas) |
| Agentes fijos | 5 autorizados, 4 en uso; 0 concurrentes |
| **Llamadas REST mensuales** | **1 000 autorizadas**; 117 realizadas al 23 oct (casi todas de estas pruebas) |
| **Llamadas REST por minuto** | **50** (explica el `ERR033` que vimos) |
| Módulo de Integración | Activo |

**Impacto en el diseño:** una conversación con ticket consume entre 3 y 6 llamadas (autenticación,
búsqueda, creación, notas, cambio de estado). Con 1 000 al mes caben unas **150–300 conversaciones
con ticket**, sin contar el seguimiento periódico. Consecuencias:
- El token se reutiliza entre peticiones (el adaptador ya lo hace) y solo se renueva ante un `401`.
- Nada de consultas periódicas frecuentes. El seguimiento de cambios necesita otra estrategia
  (por ejemplo, consultar solo cuando el usuario pregunta).
- "¿Cómo va mi ticket?" debería leer el estado guardado en la conversación y consultar
  ServiceTonic solo si han pasado varios minutos.
- Hay que **ampliar la cuota con el proveedor** antes de producción y vigilar el consumo
  (métrica de llamadas por día).
- Las pruebas contra la instancia gastan cuota: correr el descubrimiento solo cuando haga falta.

### Plantilla de contactos `Contact` (usada por el servicio "valtre Service Desk")

Campos: `MAIL`, `NAME`, `SURNAME1`, `PHONE`, `MOBILE_PHONE`, todos de texto. **No hay campo de
manager**: `get_manager()` tendrá que consultar Microsoft Graph (`/users/{correo}/manager`), como
preveía el plan (I6).

### Prioridades y estados

- **Prioridades** (4, confirmado): 1 Crítica (rojo), 2 Alta (naranja), 3 Normal (verde), 4 Baja (azul). P1 → Crítica, P2 → Alta, P3 → Normal, P4 → Baja. Falta confirmar si la API espera el texto o el número 1–4.
- **Estados** visibles: Nuevo, Abierta, En espera usuario. Faltan el resto de la lista y decidir
  cuál representa "en espera de aprobación del manager". Como la plantilla admite estados nuevos
  ([tema 2092](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2092)),
  se puede crear uno, por ejemplo "En espera aprobación".

### Pendiente

- La captura "Mostrar variables" muestra el formulario de integradores, **no la tabla de
  variables**. Hace falta pulsar el botón *Mostrar variables* y capturar la tabla
  Campo / AS / Variable, que tiene los nombres internos de los campos del ticket.
  La segunda captura ("mostrar tabla") es la pestaña *Tabla* de un integrador y tampoco la
  incluye. La ruta más directa según la ayuda: *Administración → Service Desk → Correo →
  Plantillas → Mostrar variables*.

---

## 4. Escritura bloqueada: caso para el soporte de ServiceTonic (23 oct 2026)

Con `svc_valkiria_api` (y antes con `ricardo.valadez`) la autenticación y las lecturas
funcionan, pero **ninguna variante de `POST /services/1/tickets` crea el ticket**:

| Variante | Respuesta |
|----------|-----------|
| `?rsTicket=<json>` + multipart con una parte `files` (como indica la especificación) | `302` → `/ServiceTonic/login.jsf` |
| `?rsTicket=<json>` + multipart con una parte de texto cualquiera | `302` → `login.jsf` |
| `rsTicket` como parte de texto del multipart (con o sin el parámetro de consulta) | `401` (página HTML de Tomcat) |
| Multipart sin partes | `400 MIMEParsingException: Missing start boundary` |
| Sin `Authorization` | `401` (JSON) |

El mismo token, en la misma sesión, lee `tickets/list` con `200`. La causa no es el usuario
(dos cuentas distintas con permisos de crear), ni la licencia (módulo de Integración activo y
cuota disponible). **Solo lo puede resolver el proveedor.** Mensaje sugerido:

> Instancia valtre.myservicetonic.com (código de instalación 00019336Q), ServiceTonic 12.0.8.
> Con un token válido de `POST /strest/v1/auth`, `POST /strest/v1/services/1/tickets/list` responde 200,
> pero `POST /strest/v1/services/1/tickets` (multipart/form-data, JSON en `rsTicket`) responde
> 302 a `login.jsf`; si `rsTicket` va como parte del multipart, responde 401. Además,
> `POST /strest/v1/services/1/contacts/list` devuelve `numTotal: 1` con `itemList` vacío, aunque
> pidamos las columnas `MAIL`, `NAME` y `SURNAME1`. ¿Qué falta para
> crear tickets por la API? ¿Pueden enviarnos un `curl` de creación que funcione en nuestra
> instancia?

---

## 5. Nombres internos de los campos del ticket (23 oct 2026)

De *Mostrar variables* (sin los `##`). **Mayúsculas y minúsculas cuentan.**

| Dato del asistente | Campo ServiceTonic | Nombre interno |
|--------------------|--------------------|----------------|
| Título | Título | `TITLE` |
| Descripción | Descripción | `DESCRIPTION` |
| Estado | Estado | `STATUS` |
| Prioridad | Prioridad | `PRIORITY` |
| Categoría / subcategoría | Categoría / Subcategoría | `Category` / `Subcategory` |
| Impacto / urgencia | Impacto / Urgencia | `Impact` / `Urgency` |
| Incidente o solicitud | Tipo de ticket | `Type` |
| Origen | Canal de entrada | `ENTRY_CHANNEL` |
| Equipo / técnico | Equipo / Asignado a | `TEAM` / `ASSIGNED_TO` |
| Solicitante (contacto) | Mail / Nombre / Apellido | `MAIL` / `NAME` / `SURNAME1` |
| Fechas | Creación / Últ. modificación / Resolución / Cierre | `CREATION_DATE` / `LAST_UPDATE_DATE` / `RESOL_DATE` / `CLOSE_DATE` |
| Referencia externa (ID de conversación) | — | **No existe**: hay que crear un campo personalizado |

Se configuran en `SERVICETONIC_FIELD_MAP` ([.env.poc.example](../../.env.poc.example)).
Faltan los **valores** válidos de `Category`, `Subcategory`, `Type`, `Impact`, `Urgency` y
`ENTRY_CHANNEL` (son desplegables), y confirmar si la API espera el texto o un ID.

**Aprobaciones nativas:** existe la variable `##APPROVAL fieldName=?,value=?##` ("URL de
aprobación/denegación") y la ayuda tiene un tema de [aprobación vía correo](https://support.servicetonic.com/ServiceTonic/xhtml/agentes/tools/km/mostrar_kb.jsf?language=ESP&perfil=agente&idTopic=2194).
Es una alternativa, o un complemento, a la aprobación por Teams que conviene evaluar.
