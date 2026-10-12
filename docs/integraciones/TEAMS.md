# Integración con Microsoft Teams

> Fase 2, incremento I7 del [plan](../PLAN_FASE2_GOOGLE_CLOUD.md). Sustituye a
> Slack para avisos y aprobaciones.

## Qué hace

| Evento | Qué recibe Teams |
|--------|------------------|
| Una solicitud necesita aprobación (hardware, licencia) | Tarjeta 1:1 al **manager** con *Aprobar* / *Rechazar* y un comentario opcional |
| El manager responde | La tarjeta cambia a "✅ Aprobada por …" o "❌ Rechazada por …"; la conversación se reanuda, el ticket se resuelve o se cierra y el solicitante recibe aviso |
| Cambio de estado de un ticket | Tarjeta informativa (modo Workflows) |

## Modos

El modo se elige solo, según las variables configuradas (`/api/health/detail` → `notification_mode`):

| Modo | Variables | Aprobaciones |
|------|-----------|--------------|
| `bot` | `TEAMS_BOT_APP_ID`, `TEAMS_BOT_APP_PASSWORD`, `TEAMS_TENANT_ID` | Interactivas, 1:1 con el manager |
| `workflow` | `TEAMS_WORKFLOW_URL` | La tarjeta llega a un canal, **sin botones**; la decisión se registra con la API (ver abajo) |
| `demo` | ninguna | No se envía nada; útil en desarrollo |

Si el bot falla (por ejemplo, el manager no tiene la app instalada), la
aprobación cae al modo `workflow` y no se pierde.

## Configurar el modo `bot` (recomendado)

Requiere un administrador de Microsoft 365 / Entra ID y una suscripción de
Azure (el canal de Teams del Azure Bot es gratuito).

### 1. Registro de la aplicación en Entra ID

1. *Entra ID → App registrations → New registration*. Nombre: `Help Desk IA`. Tipo: **Single tenant**.
2. Anotar el **Application (client) ID** → `TEAMS_BOT_APP_ID` y el **Directory (tenant) ID** → `TEAMS_TENANT_ID`.
3. *Certificates & secrets → New client secret* → `TEAMS_BOT_APP_PASSWORD`. Anotar la fecha de vencimiento y programar la rotación.
4. *API permissions → Microsoft Graph → Application permissions → `User.Read.All`* → **Grant admin consent**. Se usa para obtener el ID de Teams del manager a partir de su correo.

### 2. Azure Bot

1. *Azure portal → Create → Azure Bot*. Tipo de app: **Single Tenant**, con el App ID y el tenant del paso 1.
2. *Configuration → Messaging endpoint*: `https://<url-de-cloud-run>/api/teams/messages`.
3. *Channels → Microsoft Teams → Apply*.

### 3. Configurar el servicio

```bash
printf '%s' "$SECRETO" | gcloud secrets versions add teams-bot-app-password --data-file=-
```

En `infra/terraform/envs/<entorno>.tfvars`:

```hcl
teams_bot_app_id = "<application-client-id>"
teams_tenant_id  = "<tenant-id>"
secret_env = {
  API_KEYS               = "api-keys"
  TEAMS_BOT_APP_PASSWORD = "teams-bot-app-password"
}
```

y `make gcp-plan gcp-apply ENV=<entorno>`.

### 4. Publicar la app de Teams

```bash
TEAMS_BOT_APP_ID=<application-client-id> \
TEAMS_APP_DEVELOPER="Nombre de la organización" \
TEAMS_APP_WEBSITE=https://helpdesk.ejemplo.com \
make teams-app            # → dist/teams-app.zip
```

En el **Teams Admin Center**: *Teams apps → Manage apps → Upload new app*
con `dist/teams-app.zip`. Después, en *Setup policies*, **instalar la app
para los managers** (o para toda la organización). El bot solo puede escribir
1:1 a quien tenga la app instalada.

Los íconos de `teams-app/` son genéricos; se pueden reemplazar por los de la
marca (192×192 a color y 32×32 de contorno blanco sobre transparente).

### 5. Probar

1. En el chat del Help Desk, con un usuario cuyo manager tenga la app: "Quiero una laptop nueva".
2. El manager recibe la tarjeta en Teams y pulsa *Aprobar*.
3. La tarjeta muestra "✅ Aprobada por …" y `GET /api/conversations/<id>` devuelve `status: resolved`.

## Configurar el modo `workflow`

1. En el canal de Teams: *Workflows → "Post to a channel when a webhook request is received"*.
2. Copiar la URL generada y guardarla como secreto:
   `printf '%s' "$URL" | gcloud secrets versions add teams-workflow-url --data-file=-`.
3. Agregar `TEAMS_WORKFLOW_URL = "teams-workflow-url"` a `secret_env`.

## Registrar una decisión sin el bot

Para el modo `workflow`, para un agente de mesa de ayuda o para un flujo de
Power Automate (plan B del ADR-003):

```bash
curl "$URL/api/approvals" -H "X-API-Key: $KEY_AGENTE"                  # pendientes
curl -X POST "$URL/api/approvals/<approval_id>/decision" \
  -H "X-API-Key: $KEY_AGENTE" -H "Content-Type: application/json" \
  -d '{"decision": "approved", "decided_by": "María González", "comment": "ok"}'
```

Requiere una API key con rol `agent` o `admin`. Solo la primera decisión
cuenta; las siguientes devuelven `409`.

## Seguridad

- `/api/teams/messages` no usa API keys. Valida el **JWT de Bot Framework**: firma (claves públicas de Microsoft), emisor, audiencia (= App ID), vigencia y `serviceUrl` ([security/botframework.py](../../backend/security/botframework.py)).
- Solo el manager registrado en la aprobación puede responderla (se compara su `aadObjectId`); cualquier otro usuario recibe un aviso y la aprobación sigue pendiente.
- Cada decisión, aceptada o rechazada, queda en la auditoría (`approval.approved` / `approval.rejected`, con `outcome`).
- Las aprobaciones expiran a las `APPROVAL_TTL_HOURS` (72 h por defecto). Una respuesta tardía no ejecuta la acción: escala el caso a Nivel 2.

## Pendiente

- Recordatorio automático al manager a las 24 h y escalado al siguiente nivel del organigrama al expirar (Cloud Scheduler; plan, I7.b). Hoy la expiración se detecta cuando alguien responde.
- Mensajes de texto al bot (conversar con el asistente desde Teams). Hoy el bot solo procesa las acciones de las tarjetas.
