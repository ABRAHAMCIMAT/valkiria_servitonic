# Contrato API ServiceTonic — servidor Valtre

> **Hallazgos contra la instancia real (21–23 oct 2026):** autenticación, nombres de campos,
> cuota de la licencia y bloqueo de la escritura en
> [SERVICETONIC_HALLAZGOS.md](SERVICETONIC_HALLAZGOS.md).

> Revisión técnica: 14 de octubre de 2026.

## Conclusión

La integración con el servidor de pruebas **es viable** para autenticación,
tickets, comentarios, acciones, contactos y elementos de configuración. El
servidor Valtre expone exactamente el mismo contrato OpenAPI v1 que el servidor
demo público.

## Endpoints revisados

- Consola de agentes:
  `https://valtre.myservicetonic.com/ServiceTonic/xhtml/agentes/agent_home.jsf`
- Swagger Valtre:
  `https://valtre.myservicetonic.com/ServiceTonic/docs/api/index.html`
- OpenAPI Valtre:
  `https://valtre.myservicetonic.com/ServiceTonic/strest/openapi.json`
- Swagger demo:
  `https://demoes8.myservicetonic.com/ServiceTonic/docs/api/index.html`

Los documentos OpenAPI de Valtre y demo tienen el mismo SHA-256:

```text
d0e1b37fff42ff45aaef619688dad2d0120c3f58b34b462d8ed374aa94d8c088
```

## Base URL

```text
https://valtre.myservicetonic.com/ServiceTonic
```

La URL de `agent_home.jsf` es la consola web, no la API. La integración debe
usar exclusivamente rutas bajo `/strest/v1`.

## Autenticación

```http
POST /ServiceTonic/strest/v1/auth
Content-Type: application/json
```

Payload `RSCredential`:

```json
{
  "idProject": 123,
  "username": "usuario-tecnico",
  "password": "<SHA-1 binario codificado en Base64>"
}
```

El token devuelto se envía en la cabecera `Authorization`. El esquema OpenAPI
lo declara como `apiKey`, no como OAuth2; durante la prueba contractual debe
confirmarse si el valor se envía directamente o con algún prefijo.

### Reglas de seguridad

- Crear un agente técnico exclusivo; no reutilizar cuentas personales.
- Guardar la contraseña y el token únicamente en Secret Manager.
- Nunca registrar contraseña, hash ni token.
- Cachear el token y volver a autenticar una sola vez ante HTTP 401.
- Todas las llamadas deben usar TLS y timeouts explícitos.
- `idProject` es el identificador interno del servicio ServiceTonic, no el ID
  del proyecto Google Cloud.

## Operaciones disponibles

| Método | Ruta | Operación |
|---|---|---|
| POST | `/strest/v1/auth` | Generar token |
| POST | `/strest/v1/services/{idProject}/tickets` | Crear ticket |
| GET | `/strest/v1/services/{idProject}/tickets/{idIncident}` | Obtener ticket e historial opcional |
| PUT | `/strest/v1/services/{idProject}/tickets/{idIncident}` | Actualizar ticket |
| POST | `/strest/v1/services/{idProject}/tickets/list` | Buscar/listar tickets |
| POST | `/strest/v1/services/{idProject}/tickets/{idIncident}/actions` | Agregar acción/nota de trabajo |
| POST | `/strest/v1/services/{idProject}/tickets/{idIncident}/comments` | Agregar comentario |
| GET | `/strest/v1/services/{idProject}/tickets/files/.../content` | Descargar adjuntos |
| POST | `/strest/v1/services/{idProject}/contacts` | Crear contacto |
| PUT | `/strest/v1/services/{idProject}/contacts/{identContact}` | Actualizar contacto |
| DELETE | `/strest/v1/services/{idProject}/contacts/{identContact}` | Eliminar contacto |
| POST | `/strest/v1/services/{idProject}/contacts/list` | Buscar/listar contactos |
| POST | `/strest/v1/services/{idProject}/cis` | Crear CI |
| PUT | `/strest/v1/services/{idProject}/cis/{idCiCmdb}` | Actualizar CI |
| PUT | `/strest/v1/services/{idProject}/cis/sn` | Actualizar CI por número de serie |

## Formatos relevantes

### Crear/actualizar tickets

La API no recibe el ticket como cuerpo JSON normal. `rsTicket` se envía como
JSON serializado en un parámetro de query y los adjuntos como
`multipart/form-data`. El adaptador debe construir y codificar ambos elementos.

`RSTicket` utiliza campos principales y una `fieldList` dinámica:

```json
{
  "idProject": 123,
  "team": "Service Desk",
  "username": "agente-integracion",
  "contact": {"identContact": "usuario@empresa.com"},
  "fieldList": [
    {"fieldName": "<campo-configurado>", "value": "<valor>"}
  ]
}
```

Los nombres reales de campos, estados, prioridades, categorías y equipos no
están definidos por OpenAPI: dependen de la configuración de Valtre.

### Listar tickets/contactos

Las operaciones `/list` reciben `RSQuery` como JSON:

```json
{
  "logic": "AND",
  "initResult": 0,
  "maxResults": 20,
  "fieldList": [],
  "criterionList": [],
  "orderList": []
}
```

El adaptador debe paginar con `initResult` y `maxResults`. La operación de
lista de tickets documenta HTTP 429, por lo que todas las llamadas deben
respetar backoff y `Retry-After` cuando esté disponible.

## Cobertura frente a `TicketingPort`

| Capacidad Valkiria | API disponible | Estado |
|---|---|---|
| Crear ticket | `createTicket` | ✅ Viable |
| Obtener ticket por ID | `getTicketById` | ✅ Viable |
| Buscar/listar tickets | `getTickets` | ✅ Viable |
| Actualizar ticket | `updateTicket` | ✅ Viable |
| Agregar nota interna | `addAction` | ✅ Viable; confirmar tipos |
| Agregar comentario público | `addComment` | ✅ Viable |
| Adjuntos | endpoints de archivos/multipart | ✅ Viable |
| Buscar contactos | `getContacts` | ✅ Viable |
| Obtener manager | Campos dinámicos de contacto | 🟡 Confirmar campo o usar Graph |
| Base de conocimiento | No aparece en OpenAPI | 🔴 Requiere otra API/exportación |
| Catálogos y metadatos | No aparecen en OpenAPI | 🔴 Requiere exportación/admin |
| Webhooks de cambios | No aparecen en OpenAPI | 🔴 Confirmar con proveedor |
| Aprobaciones nativas | No aparecen en OpenAPI | 🟡 Teams puede registrar decisión como acción/estado |

## Datos necesarios para la prueba

No deben enviarse por chat ni versionarse. Configurarlos como secretos del
entorno de prueba:

```text
SERVICETONIC_BASE_URL=https://valtre.myservicetonic.com/ServiceTonic
SERVICETONIC_PROJECT_ID=<entero>
SERVICETONIC_USERNAME=<agente-tecnico>
SERVICETONIC_PASSWORD=<secreto>
```

Además se necesita:

- Contacto de prueba identificable por correo.
- Equipo autorizado para recibir tickets.
- Nombres internos de campos obligatorios.
- Estados/prioridades válidos.
- Autorización para crear y cerrar tickets marcados como pruebas.

## Secuencia de validación recomendada

1. Autenticar y obtener token.
2. Listar contactos con máximo 1 registro, sin imprimir PII.
3. Listar tickets con máximo 1 registro.
4. Obtener un ticket de prueba conocido con historial.
5. Crear ticket identificado como `VALKIRIA-TEST-<timestamp>`.
6. Agregar comentario y acción.
7. Actualizar estado usando el catálogo confirmado.
8. Consultar nuevamente y comprobar trazabilidad.
9. Cerrar el ticket de prueba.
10. Verificar 401, 403, 429 y reintentos sin exponer secretos.

## Prueba automatizada de solo lectura

El workflow `.github/workflows/servicetonic-contract.yml` utiliza el environment
de GitHub `servicetonic-test`. Configurar:

### Variables

```text
SERVICETONIC_BASE_URL=https://valtre.myservicetonic.com/ServiceTonic
SERVICETONIC_PROJECT_ID=<entero>
SERVICETONIC_TEST_TICKET_ID=<opcional>
SERVICETONIC_AUTH_PREFIX=<vacío salvo confirmación del proveedor>
```

### Secretos

```text
SERVICETONIC_USERNAME
SERVICETONIC_PASSWORD
```

El workflow autentica, lista como máximo un contacto y un ticket, y
opcionalmente consulta un ticket conocido. Solo publica códigos HTTP y forma
de respuesta; nunca imprime registros, contraseña, hash o token.

## Decisión

Se puede iniciar I5.a (lectura y pruebas contractuales) cuando estén disponibles
el `idProject`, el agente técnico y los nombres de campos. I5.b (escritura) debe
esperar autorización explícita para crear tickets en el servicio Valtre.
