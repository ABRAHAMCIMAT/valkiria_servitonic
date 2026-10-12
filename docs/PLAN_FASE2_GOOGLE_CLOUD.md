# Fase 2 — Google Cloud (Vertex AI), ServiceTonic y Microsoft Teams · Plan Incremental

> **Proyecto:** Sistema Multiagente de Help Desk (`ABRAHAMCIMAT/valkiria_servitonic`)
> **Rama:** `feature/integracion-google-cloud` (fusionada en `main`)
> **Prerrequisito:** Fase 0 (seguridad) y Fase 1 (contenedores, CI/CD, pruebas) completadas
> **Duración estimada:** 6–8 semanas (8 incrementos de 2–5 días cada uno)
> **Fecha:** 12 de octubre de 2026

---

## Estado de avance

ServiceTonic queda en espera de sus [requerimientos técnicos](integraciones/SERVICETONIC_REQUERIMIENTOS.md);
mientras tanto se avanza con Google Cloud y Teams manteniendo **ServiceNow** como sistema de tickets.

| # | Incremento | Estado | Notas |
|---|------------|--------|-------|
| I0 | Descubrimiento | 🟡 En curso | Requerimientos de ServiceTonic enviados; faltan proyecto GCP y registro en Entra ID |
| I1 | Puertos | ✅ Código listo | `TicketingPort`/`NotifierPort` en `adapters/ports.py`, fábrica en `adapters/factory.py`. Se conservan los nombres `*_incident` (ServiceNow sigue activo) |
| I2 | Vertex AI | ✅ Código listo | Falta la comparación de evaluaciones con un proyecto real |
| I3 | GCP base + Cloud Run | ✅ Código listo | `infra/terraform/` (validado con `terraform validate`), `deploy-gcp.yml`, [DESPLIEGUE_GCP.md](DESPLIEGUE_GCP.md). Sin aplicar todavía |
| I4 | Firestore + Cloud Logging | ✅ Código listo | Recordatorios y escalado automático de aprobaciones expiradas pendientes |
| I5–I6 | ServiceTonic | ⏸️ En espera | Bloqueado por los requerimientos |
| I7 | Teams | ✅ Código listo | Bot + Workflows + API de decisiones. Faltan el bot en Azure y la app en el tenant ([TEAMS.md](integraciones/TEAMS.md)) |
| I8 | Corte a producción | ⏳ Pendiente | Depende de I5 |

---

## Objetivo de la fase

Llevar el sistema multiagente a **producción en Google Cloud** y sustituir dos
integraciones externas:

| Hoy | Después de la Fase 2 |
|-----|----------------------|
| LLM local (Jan) u OpenAI | **Vertex AI (Gemini)** con identidad de Google Cloud, sin claves estáticas |
| Contenedor en una máquina (`docker compose`) | **Cloud Run** + Artifact Registry + Secret Manager + Firestore + Cloud Logging, todo con Terraform |
| **ServiceNow** como sistema de tickets, KB y organigrama | **ServiceTonic** (portal de usuario help desk) vía su API REST |
| **Slack** para aprobaciones | **Microsoft Teams**: Adaptive Cards con botones *Aprobar / Rechazar* que reanudan el flujo |

### Principios del plan incremental

1. **Cada incremento se fusiona a `main` por separado y se puede desplegar solo.**
   Nada queda "a medias" entre incrementos.
2. **Interruptores por variable de entorno, sin ramas de larga vida.** Cada integración
   nueva entra apagada (`TICKETING_PROVIDER`, `LLM_PROVIDER`, `NOTIFY_CHANNEL`) y se
   enciende cuando está validada. Volver atrás significa cambiar una variable y
   publicar una revisión de Cloud Run nueva.
3. **El modo demo/mock sigue funcionando siempre.** La suite de pruebas actual
   corre sin red ni credenciales y así debe seguir; ningún incremento la rompe.
4. **Puertos antes que adaptadores.** Primero se desacopla el código de
   ServiceNow/Slack (incremento 1) y después se agregan los proveedores nuevos.
   Así cada proveedor nuevo es un archivo adicional, no una reescritura.

**Criterio de salida de la fase (Definition of Done):**
- Servicio en Cloud Run (`APP_ENV=production`) respondiendo `200` en `/api/health`, desplegado por GitHub Actions con Workload Identity Federation (sin llaves JSON).
- `LLM_PROVIDER=vertex` con evaluaciones (`scripts/run_evals.py`) iguales o mejores que la línea base actual.
- `TICKETING_PROVIDER=servicetonic`: crear, consultar y actualizar tickets reales, buscar en la KB y resolver el manager desde ServiceTonic.
- `NOTIFY_CHANNEL=teams`: el manager aprueba o rechaza desde Teams y la conversación pasa de `awaiting_approval` a `resolved` o `rejected` sin intervención manual.
- Ningún secreto en variables de entorno planas: todos vienen de Secret Manager.
- CI en verde y cobertura ≥ 80 % (igual que la Fase 1).

---

## Estado actual (lo que condiciona el plan)

| Hallazgo | Evidencia | Impacto en el plan |
|----------|-----------|--------------------|
| Los agentes dependen de la **clase concreta** `ServiceNowAdapter`, no de una interfaz | `backend/agents/coordinator.py:30`, `escalation.py`, `knowledge.py`, `execution.py`, `diagnostic.py` | El incremento 1 introduce el puerto `TicketingPort` |
| El coordinador lee un atributo privado del adaptador | `coordinator.py:141` usa `self.snow._tickets` | Solo funciona en demo; con ServiceTonic real "estado de mi ticket" fallaría. Se reemplaza por `list_tickets(caller)` |
| Las acciones de autoservicio no hacen nada en modo LIVE | `servicenow.py` (`unlock_account`, `reset_password`, `assign_license`, `request_approval`): `if self.live: pass` | Hay que decidir qué ejecuta ServiceTonic y qué ejecuta otro sistema (AD/Entra). Ver incremento 6 |
| El flujo de aprobación **nunca se reanuda** | `coordinator.py:_handle_approval` deja `status="awaiting_approval"` y no hay endpoint de respuesta | El incremento 7 agrega el callback de Teams y la reanudación |
| El adaptador de Teams usa el formato de **Office 365 Connectors** | `notifications.py` hace POST de `{"text": ...}` a `TEAMS_WEBHOOK_URL` | Microsoft retiró esos conectores; hay que migrar a **Workflows** (Power Automate) o a un **bot** |
| El LLM usa una **API key estática** | `core/llm.py:LLMConfig.api_key` | Vertex solo acepta tokens OAuth de Google que expiran cada hora; hay que renovarlos |
| Estado en memoria y en disco local | `core/state.py`, `security/rate_limit.py`, `DATA_DIR` | En Cloud Run el disco es efímero y hay varias instancias; se migra a Firestore y Cloud Logging |
| El contrato de almacenamiento ya existe | `core/storage.py:ConversationStorage` | Firestore se implementa sin tocar `server.py` |
| La capa LLM ya es compatible con OpenAI | `core/llm.py:OpenAICompatLLM` | Vertex expone un endpoint compatible con OpenAI; el cambio es pequeño |

---

## Mapa de incrementos

```
 I0  Descubrimiento y prerrequisitos (sin código)
  │
 I1  Puertos: TicketingPort / NotifierPort ── refactor sin cambio de comportamiento
  │
  ├──► I2  Vertex AI (Gemini) como LLM ─────── funciona en local con gcloud ADC
  │
  ├──► I3  Infraestructura base GCP + Cloud Run (demo) ── primer despliegue real
  │      │
  │      └──► I4  Firestore + Cloud Logging ── estado durable y multi-instancia
  │
  ├──► I5  ServiceTonic: tickets (lectura → escritura)
  │      │
  │      └──► I6  ServiceTonic: KB, contactos/manager, acciones
  │
  └──► I7  Teams: notificaciones y aprobaciones interactivas
         │
         ▼
 I8  Endurecimiento, corte a producción y retiro de ServiceNow/Slack
```

I2, I3 y I5 pueden avanzar **en paralelo** una vez fusionado I1. I7 necesita I4
(persistencia de aprobaciones pendientes) y es más útil con I5 (para actualizar el
ticket real).

| # | Incremento | Duración | Depende de | Se puede desplegar a producción solo |
|---|------------|----------|------------|--------------------------------------|
| I0 | Descubrimiento y prerrequisitos | 3–5 días (en paralelo con I1) | — | n/a |
| I1 | Puertos de tickets y notificaciones | 2–3 días | — | Sí (sin cambio funcional) |
| I2 | Vertex AI | 2–3 días | I1 | Sí |
| I3 | GCP base + Cloud Run | 4–5 días | I0 (proyecto GCP) | Sí (modo demo) |
| I4 | Firestore + Cloud Logging | 3–4 días | I3 | Sí |
| I5 | ServiceTonic: tickets | 4–5 días | I0 (API ServiceTonic), I1 | Sí, detrás de `TICKETING_PROVIDER` |
| I6 | ServiceTonic: KB, contactos, acciones | 3–5 días | I5 | Sí |
| I7 | Teams: notificaciones y aprobaciones | 5–7 días | I0 (tenant M365), I4 | Sí, detrás de `NOTIFY_CHANNEL` |
| I8 | Endurecimiento y corte | 3–4 días | Todos | Es el corte |

---

## I0 — Descubrimiento y prerrequisitos

**Objetivo:** resolver lo que no depende del código y que puede bloquear los incrementos siguientes.

### Entregables

**ServiceTonic** (es el riesgo principal; ver "Riesgos"). La lista completa para
enviar al administrador o al proveedor está en
[integraciones/SERVICETONIC_REQUERIMIENTOS.md](integraciones/SERVICETONIC_REQUERIMIENTOS.md):
- [ ] Obtener del proveedor o del administrador la **referencia de la API REST** de la versión instalada. La documentación pública solo confirma que la API permite crear y actualizar tickets y contactos bajo `/api/v1/`. No están publicados la autenticación, la KB ni el organigrama.
- [ ] Instancia de **pruebas/sandbox** de ServiceTonic y un usuario técnico de integración con permisos mínimos.
- [ ] Confirmar el método de autenticación de la API (token, usuario/contraseña u OAuth 2.0/OIDC).
- [ ] Inventario de catálogos: **estados**, **prioridades**, **categorías/subcategorías**, **grupos de asignación** y **formularios/procesos** que usa el help desk.
- [ ] ¿La API expone la **base de conocimiento**? ¿Y la jerarquía **empleado → manager** (contactos)? Si no, definir la fuente alternativa (Entra ID / Microsoft Graph para el manager; exportación periódica para la KB).
- [ ] ¿ServiceTonic tiene **webhooks/eventos salientes** de cambio de estado? Habilitarían que el Agente de Seguimiento notifique cambios sin consultar periódicamente.
- [ ] Documentar todo en `docs/integraciones/SERVICETONIC_API.md` con ejemplos `curl` reales.

**Google Cloud:**
- [ ] Proyectos `snow-ma-dev` y `snow-ma-prod` (o uno con dos entornos), con facturación y **alerta de presupuesto**.
- [ ] Región principal (sugerida: `us-central1`, por disponibilidad de modelos Gemini; si hay requisitos de residencia de datos, evaluar `northamerica-south1` u otra y confirmar qué modelos ofrece).
- [ ] Cuotas de Vertex AI para el modelo elegido (`gemini-2.5-flash` como opción base y `gemini-2.5-pro` para el juez LLM, a confirmar con evaluaciones).
- [ ] Bucket de estado remoto de Terraform.

**Microsoft 365 / Teams:**
- [ ] Acceso de administrador del tenant para registrar una app en **Entra ID** y crear un **Azure Bot** (necesario para botones interactivos; ver I7).
- [ ] Canal o chat donde llegan las aprobaciones, y si van al **manager en 1:1** (recomendado) o a un canal compartido.
- [ ] Política de la organización para instalar apps personalizadas de Teams.

**Decisiones a registrar (ADR breves en `docs/adr/`):**
- ADR-001: ServiceTonic como sistema de registro de tickets.
- ADR-002: Vertex AI con el endpoint compatible con OpenAI (frente al SDK `google-genai`).
- ADR-003: Teams con Azure Bot frente a Power Automate para aprobaciones.

**Criterio de salida:** un `curl` autenticado contra el sandbox de ServiceTonic crea un ticket; `gcloud auth application-default login` funciona contra el proyecto dev; existe el registro de la app en Entra ID.

---

## I1 — Puertos de tickets y notificaciones (refactor)

**Objetivo:** que los agentes dependan de **interfaces**, no de ServiceNow ni de Slack. No cambia el comportamiento: las 408 pruebas existentes deben pasar sin modificar sus aserciones.

### Archivos

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `backend/adapters/ports.py` | NUEVO | `TicketingPort` y `NotifierPort` como `typing.Protocol` (mismo patrón que `core/storage.py`) |
| `backend/adapters/demo_ticketing.py` | NUEVO | Extrae el modo DEMO de `servicenow.py` (KB, organigrama y tickets en memoria) a un adaptador propio |
| `backend/adapters/servicenow.py` | MODIFICAR | Solo el modo LIVE; implementa `TicketingPort` |
| `backend/adapters/factory.py` | NUEVO | `build_ticketing()` y `build_notifier()` según `TICKETING_PROVIDER` y `NOTIFY_CHANNEL` |
| `backend/agents/*.py` | MODIFICAR | Tipar con `TicketingPort`; renombrar `self.snow` → `self.ticketing` |
| `backend/agents/coordinator.py` | MODIFICAR | Sustituir `self.snow._tickets` por `self.ticketing.list_tickets(caller=...)` |
| `backend/server.py` | MODIFICAR | Usar la fábrica; `/api/health/detail` informa `ticketing_provider` y `ticketing_mode` (se mantiene `servicenow_mode` un incremento por compatibilidad) |
| `backend/core/models.py` | MODIFICAR | `Ticket`: agregar `external_id` (ID del sistema externo) y desacoplar `number` del prefijo `INC` |
| `tests/unit/test_ports.py` | NUEVO | Verifica que cada adaptador cumple el protocolo (`isinstance(..., TicketingPort)` con `runtime_checkable`) |

### Contrato propuesto

```python
@runtime_checkable
class TicketingPort(Protocol):
    live: bool
    provider: str  # "demo" | "servicenow" | "servicetonic"

    # tickets
    def create_ticket(self, ticket: Ticket) -> Ticket: ...
    def update_ticket(self, ticket: Ticket, fields: dict) -> Ticket: ...
    def add_note(self, ticket: Ticket, note: str, internal: bool = True) -> None: ...
    def get_ticket(self, number: str) -> Ticket | None: ...
    def list_tickets(self, caller: str, open_only: bool = True, limit: int = 5) -> list[Ticket]: ...

    # conocimiento y organización
    def search_kb(self, query: str, top_k: int = 3) -> list[dict]: ...
    def get_manager(self, employee: str) -> dict | None: ...

    # autoservicio
    def unlock_account(self, target: str) -> dict: ...
    def reset_password(self, target: str) -> dict: ...
    def assign_license(self, software: str, user: str) -> dict: ...


@runtime_checkable
class NotifierPort(Protocol):
    channel: str
    live: bool

    def send(self, to: str, subject: str, body: str) -> dict: ...
    def send_approval_request(self, approval: ApprovalRequest) -> dict: ...
    def send_ticket_update(self, user: str, ticket_number: str, state: str, note: str) -> dict: ...
```

Los nombres `create_incident`/`update_incident`/`get_incident` se conservan como
alias durante I1 para no romper las pruebas, y se eliminan en I8.

**Estados normalizados:** se agrega `TicketState` (`StrEnum`: `new`, `in_progress`,
`awaiting_approval`, `resolved`, `closed`, `rejected`). Cada adaptador traduce entre
este enum y los estados del sistema externo. Así el coordinador deja de escribir
cadenas como `"Awaiting Approval"` propias de ServiceNow.

**Criterio de salida:** `make test` y `make lint` en verde; `grep -rn "self.snow" backend/agents` sin resultados; comportamiento idéntico en `scripts/demo.py`.

---

## I2 — Vertex AI (Gemini) como proveedor LLM

**Objetivo:** `LLM_PROVIDER=vertex` funcionando en local (con credenciales de `gcloud`) y listo para Cloud Run (con la cuenta de servicio).

### Enfoque

Vertex AI expone un endpoint **compatible con OpenAI Chat Completions**:

```
https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/endpoints/openapi
modelo: google/gemini-2.5-flash
```

(Para la ubicación `global` el host es `aiplatform.googleapis.com`). Esto permite
**reutilizar `OpenAICompatLLM`** (reintentos, manejo de 429/5xx y `json_mode`).
La única diferencia es la autenticación: Vertex **no acepta API keys** por esta vía,
solo tokens OAuth de Google Cloud, que **expiran a la hora**.

### Archivos

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `backend/core/llm.py` | MODIFICAR | `LLMConfig.from_env()` para `provider == "vertex"`: construye `base_url` desde `GCP_PROJECT`/`VERTEX_LOCATION`; modelo por defecto `google/gemini-2.5-flash` |
| `backend/core/gcp_auth.py` | NUEVO | `GoogleTokenProvider`: `google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])`, cachea el token y lo renueva 5 minutos antes de que expire (seguro entre hilos) |
| `backend/core/llm.py` | MODIFICAR | `OpenAICompatLLM` acepta un `token_provider` opcional; si existe, pide el token en cada solicitud en lugar de usar `api_key`. Se registra la estrategia `"vertex"` en `_provider_strategy` |
| `requirements.txt` | MODIFICAR | `google-auth>=2.30` (solo la autenticación, sin el SDK completo de Vertex) |
| `.env.example`, `docker-compose.yml` | MODIFICAR | `GCP_PROJECT`, `VERTEX_LOCATION`, `LLM_PROVIDER=vertex` documentado |
| `tests/unit/test_llm_vertex.py` | NUEVO | Token falso, renovación al expirar, URL bien formada, 401 → `ProviderError` |
| `docs/llmops/02_DATOS_Y_PROMPTS.md` | MODIFICAR | Notas de comportamiento de Gemini con `response_format=json_object` |

### Validación de calidad (obligatoria antes de encender en producción)

1. Ejecutar `scripts/run_evals.py` con la línea base actual (Jan/OpenAI) y guardar resultados.
2. Ejecutar con `LLM_PROVIDER=vertex` y comparar: precisión de intención, JSON válido, latencia p95 y costo por conversación.
3. Revisar las salidas de los guardrails (`llmops/guardrails.py`) con Gemini: los filtros de seguridad de Gemini pueden bloquear contenido y devolver `finish_reason` distinto de `stop`. Se trata como `ProviderError` con un mensaje claro.
4. Registrar la versión exacta del modelo en `llmops/prompts.py` (fingerprint) para trazabilidad.

**Criterio de salida:** evaluaciones de Vertex ≥ línea base; pruebas en verde sin red (el token provider se simula); `/api/health/detail` reporta `llm_provider: vertex`.

---

## I3 — Infraestructura base de Google Cloud y primer despliegue en Cloud Run

**Objetivo:** el sistema corre en Cloud Run en modo demo (`TICKETING_PROVIDER=demo`, `LLM_PROVIDER=vertex` o `mock`), desplegado automáticamente desde GitHub.

### Stack

| Componente | Servicio GCP | Para qué |
|------------|--------------|----------|
| Cómputo | **Cloud Run** (servicio `snow-multiagent-api`) | API FastAPI, frontend y dashboard estáticos |
| Imágenes | **Artifact Registry** (Docker, `us-central1`) | Sustituye a GHCR como origen del despliegue (GHCR se puede conservar) |
| Secretos | **Secret Manager** | `API_KEYS`, credenciales de ServiceTonic y de Teams/Bot |
| Identidad del servicio | **Cuenta de servicio** `snow-ma-run@` | Mínimo privilegio: `roles/aiplatform.user`, `roles/secretmanager.secretAccessor` (por secreto), `roles/datastore.user` (I4), `roles/logging.logWriter` |
| CI/CD | **Workload Identity Federation** + GitHub Actions | Despliegue sin llaves JSON; el pool solo confía en el repo `ABRAHAMCIMAT/valkiria_servitonic` y la rama `main`/tags |
| IaC | **Terraform** | Todo reproducible; estado remoto en GCS |
| Presupuesto | **Cloud Billing Budget** | Alertas al 50/90/100 % |

### Archivos

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `infra/terraform/` | NUEVO | `main.tf`, `apis.tf` (run, aiplatform, secretmanager, artifactregistry, firestore, iamcredentials), `iam.tf`, `artifact_registry.tf`, `secrets.tf` (solo los contenedores; los valores se cargan fuera de Terraform), `cloud_run.tf`, `wif.tf`, `budget.tf`, `variables.tf`, `envs/dev.tfvars`, `envs/prod.tfvars` |
| `.github/workflows/deploy-gcp.yml` | NUEVO | `google-github-actions/auth` (WIF) → build → push a Artifact Registry → `gcloud run deploy` con `--no-traffic` → smoke test a la URL de la revisión → mover el tráfico |
| `backend/config.py` | MODIFICAR | En Cloud Run (`K_SERVICE` definido): `DATA_DIR=/tmp/data` y logs a stdout; validar que `PORT` venga del entorno |
| `Dockerfile` | REVISAR | Ya es compatible (no-root, `PORT`). El `HEALTHCHECK` de Docker no aplica en Cloud Run; se configuran *startup* y *liveness probes* contra `/api/health` |
| `docs/DESPLIEGUE_GCP.md` | NUEVO | Guía paso a paso: bootstrap de Terraform, carga de secretos, primer despliegue, rollback |
| `Makefile` | MODIFICAR | `make gcp-plan`, `make gcp-apply`, `make gcp-deploy` |

### Configuración de Cloud Run en este incremento

- `--min-instances=0` en dev, `1` en prod (evita arranques en frío en el chat).
- **`--max-instances=1` temporal:** hasta I4 el estado de las conversaciones y el rate limiter viven en memoria. Con más de una instancia, un usuario podría caer en otra instancia y perder su conversación. Se levanta en I4.
- `--concurrency=40`, `--cpu=1`, `--memory=1Gi`, `--timeout=120s` (las llamadas al LLM pueden tardar).
- Secretos montados como variables de entorno desde Secret Manager (`--set-secrets API_KEYS=api-keys:latest,...`): el código no cambia, sigue leyendo `os.getenv`.
- Ingreso: `all` con autenticación de la app (las `API_KEYS` de Fase 0). En I8 se evalúa poner delante un balanceador con Cloud Armor.
- `CORS_ORIGINS` = la URL de Cloud Run o el dominio propio.

**Criterio de salida:** un push a `main` despliega una revisión nueva; `curl https://<url>/api/health` → `200`; una conversación del demo completa funciona por la URL pública con API key; rollback probado (`gcloud run services update-traffic --to-revisions=<anterior>=100`).

---

## I4 — Estado durable y observabilidad en GCP

**Objetivo:** permitir varias instancias de Cloud Run sin perder conversaciones, y llevar logs, telemetría y auditoría a servicios gestionados.

### Archivos

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `backend/core/firestore_store.py` | NUEVO | `FirestoreConversationStore` que implementa `ConversationStorage` (colección `conversations`, TTL de 90 días) |
| `backend/core/approvals.py` | NUEVO | `ApprovalStore` (colección `approvals`): solicitudes pendientes con `approval_id`, `conversation_id`, `ticket_number`, `manager`, `resource`, `expires_at` y `status`. Lo necesita I7 |
| `backend/server.py` | MODIFICAR | `STORAGE_BACKEND=file|firestore` selecciona la implementación |
| `backend/llmops/logging.py` | MODIFICAR | En Cloud Run, logs JSON a stdout con `severity`, `logging.googleapis.com/trace` y `conversation_id` (Cloud Logging los indexa sin agente) |
| `backend/security/audit.py` | MODIFICAR | Auditoría a stdout con la etiqueta `log_type=audit`; un **sink de Cloud Logging** la envía a un bucket de logs con retención de 1 año (o a BigQuery) |
| `backend/observability/telemetry.py` | MODIFICAR | Eventos de telemetría como logs estructurados; un sink los manda a **BigQuery** (`snow_ma.telemetry`). Esto cierra el pendiente de `docs/AUDITORIA_LLMOPS.md` ("persistir histórico") |
| `backend/security/rate_limit.py` | MODIFICAR | Documentar que el límite es por instancia; opción de contador en Firestore o Memorystore si se requiere límite global |
| `infra/terraform/firestore.tf`, `logging.tf`, `monitoring.tf` | NUEVO | Base de datos Firestore (modo nativo), sinks, dataset de BigQuery, alertas (5xx > 2 %, latencia p95 > 15 s, errores de Vertex, presupuesto) |
| `requirements.txt` | MODIFICAR | `google-cloud-firestore>=2.16` |
| `tests/unit/test_firestore_store.py` | NUEVO | Contra el **emulador de Firestore** en CI (job opcional) y con un cliente simulado en la suite principal |

**Criterio de salida:** `--max-instances` sube a 5; una conversación iniciada en una instancia se consulta desde otra; los logs se pueden filtrar por `conversation_id` en Cloud Logging; consulta de costo de tokens por día en BigQuery.

---

## I5 — ServiceTonic: tickets

**Objetivo:** `TICKETING_PROVIDER=servicetonic` crea, consulta y actualiza tickets reales. Se hace en dos sub-pasos para reducir el riesgo.

### I5.a — Solo lectura (1–2 días)

- `get_ticket(number)` y `list_tickets(caller)` contra ServiceTonic.
- Activación en dev con un **modo sombra**: el sistema sigue creando tickets en demo, pero "¿cómo va mi ticket?" consulta ServiceTonic. Así se valida la autenticación, la paginación y el mapeo de estados sin escribir datos.

### I5.b — Escritura (2–3 días)

- `create_ticket`, `update_ticket` (estado, prioridad, grupo, notas de resolución) y `add_note`.
- **Idempotencia:** cada creación envía el `conversation_id` como referencia externa (campo personalizado o etiqueta, según lo que confirme I0) y antes de crear se busca si ya existe. Evita tickets duplicados cuando hay reintentos.

### Archivos

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `backend/adapters/servicetonic.py` | NUEVO | `ServiceTonicAdapter(TicketingPort)`. Mismo patrón que `servicenow.py`: `httpx.Client`, `_request()` con `retry()` en 429/5xx y errores de red, `ProviderError` en 4xx, fail-fast en producción si falta configuración |
| `backend/adapters/servicetonic_mapping.py` | NUEVO | Tablas de traducción **configurables** (cargadas de `config/servicetonic_mapping.yaml`): `TicketState` ↔ estados de ServiceTonic, `Priority` P1–P4 ↔ prioridades, categoría/subcategoría del Clasificador ↔ categorías y procesos, `assignment_group` ↔ grupos/equipos |
| `config/servicetonic_mapping.yaml` | NUEVO | Valores reales del inventario de I0; el despliegue los puede sobrescribir sin cambiar código |
| `backend/agents/classifier.py` | MODIFICAR | La lista de categorías y grupos válidos que se le da al LLM sale del archivo de mapeo, para que el Clasificador solo proponga valores que existen en ServiceTonic |
| `.env.example`, Secret Manager | MODIFICAR | `TICKETING_PROVIDER`, `SERVICETONIC_BASE_URL`, `SERVICETONIC_API_TOKEN` (o usuario/contraseña), `SERVICETONIC_TIMEOUT` |
| `tests/integration/test_servicetonic_adapter.py` | NUEVO | Respuestas HTTP simuladas con `httpx.MockTransport`: creación, 401, 404, 429 con reintento, 500, paginación, mapeo de estados |
| `tests/contract/test_servicetonic_live.py` | NUEVO | Marcadas `@pytest.mark.live`; se ejecutan **solo** contra el sandbox (job manual en CI con secretos) |

### Variables nuevas

```bash
TICKETING_PROVIDER=servicetonic     # demo | servicenow | servicetonic
SERVICETONIC_BASE_URL=https://<cliente>.myservicetonic.com/api/v1
SERVICETONIC_API_TOKEN=             # Secret Manager: servicetonic-api-token
SERVICETONIC_MAPPING_FILE=config/servicetonic_mapping.yaml
```

> Las rutas y los nombres de campos exactos se confirman en I0. El adaptador
> concentra todo lo específico de ServiceTonic en `_url()`, `_headers()` y el
> módulo de mapeo, para que un cambio en la API toque solo esos puntos.

**Criterio de salida:** en dev, una conversación de incidente crea un ticket real en el sandbox de ServiceTonic con categoría, prioridad y grupo correctos; "¿cómo va mi ticket?" devuelve su estado real; la escalación a Nivel 2 deja el resumen ejecutivo como nota interna del ticket.

---

## I6 — ServiceTonic: conocimiento, contactos y acciones de autoservicio

**Objetivo:** completar las capacidades que hoy dependen de ServiceNow.

### Base de conocimiento (Agente de Conocimiento / RAG)

Según lo que confirme I0:

| Escenario | Implementación |
|-----------|----------------|
| ServiceTonic expone la KB por API | `search_kb()` consulta la API y devuelve `{id, title, content, url}` |
| No la expone o la búsqueda es pobre | **Job de sincronización** (Cloud Run Job + Cloud Scheduler, cada noche) que exporta los artículos, genera embeddings con **Vertex AI Embeddings** (`text-embedding-005` o el vigente) y los guarda en **Firestore con búsqueda vectorial**. `search_kb()` hace búsqueda semántica. Mejora además el RAG actual, que solo coincide por palabras clave (`servicenow.py:search_kb`) |

### Manager / organigrama

- Si ServiceTonic guarda el manager en el contacto: `get_manager()` lo lee de allí.
- Si no: `get_manager()` consulta **Microsoft Graph** (`/users/{upn}/manager`) con la misma app de Entra ID de I7. Es la fuente de verdad más habitual para el organigrama y además da el UPN o el ID de Teams para enviar la aprobación al manager correcto.

### Acciones de autoservicio

Hoy `unlock_account`, `reset_password` y `assign_license` **no hacen nada en modo LIVE**. ServiceTonic registra la solicitud, pero en general no ejecuta acciones en Active Directory/Entra. Se propone:

| Acción | Ejecutor propuesto | Registro |
|--------|--------------------|----------|
| Desbloquear cuenta | Microsoft Graph / Entra ID (o un runbook existente) | Nota en el ticket de ServiceTonic |
| Restablecer contraseña | Redirigir al flujo SSPR de Entra (no generar contraseñas desde el chat) | Nota en el ticket |
| Asignar licencia | Microsoft Graph `assignLicense` tras la aprobación | Ticket actualizado y cerrado |

Cada ejecutor queda detrás de un interruptor (`SELF_SERVICE_EXECUTOR=none|graph`). Con `none`, la acción se convierte en un ticket para el grupo correspondiente en lugar de reportar un éxito falso. **Esto corrige el comportamiento actual**, que devuelve `success: True` sin haber hecho nada.

**Criterio de salida:** una pregunta de la KB responde con un artículo real de ServiceTonic; una solicitud de hardware encuentra al manager real; ninguna acción de autoservicio reporta éxito sin haberse ejecutado.

---

## I7 — Microsoft Teams: notificaciones y aprobaciones interactivas

**Objetivo:** reemplazar Slack. El manager recibe en Teams una tarjeta con **Aprobar / Rechazar**, y su respuesta reanuda la conversación y actualiza el ticket en ServiceTonic.

### Contexto técnico

- Microsoft **retiró los conectores de Office 365** (los *Incoming Webhooks* clásicos) en Teams. El adaptador actual (`notifications.py`) usa ese formato y dejará de entregar mensajes.
- Para **notificaciones de una sola vía** el reemplazo es **Workflows** (Power Automate, disparador "cuando se recibe una solicitud de webhook de Teams"), con payload de **Adaptive Card**.
- Para **botones con respuesta**, Microsoft recomienda `Action.Execute` (Universal Actions), que entrega el clic a un **bot** como una invocación `adaptiveCard/action`. El bot puede responder con una tarjeta actualizada ("Aprobado por María González").

### I7.a — Notificaciones a Teams vía Workflows (1–2 días)

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `backend/adapters/teams.py` | NUEVO | `TeamsNotifier(NotifierPort)`: arma Adaptive Cards (actualización de ticket, escalación) y las envía al webhook de Workflows (`TEAMS_WORKFLOW_URL`, en Secret Manager) |
| `backend/adapters/cards/*.json` | NUEVO | Plantillas de Adaptive Card (versión 1.5) |
| `backend/adapters/notifications.py` | MODIFICAR | Slack y WhatsApp quedan como implementaciones legadas; `NOTIFY_CHANNEL=teams` por defecto en `.env.example` |
| `tests/unit/test_teams_cards.py` | NUEVO | Las tarjetas validan contra el esquema y no incluyen PII que no corresponda (se reutiliza `security/redaction.py`) |

Esto ya sustituye a Slack en las notificaciones, pero la aprobación todavía se
hace "fuera" del sistema. Es el paso intermedio seguro.

### I7.b — Aprobaciones interactivas con bot (3–5 días)

**Arquitectura:**

```
Coordinador ──(1) crea ApprovalRequest en Firestore (I4) ──┐
     │                                                      │
     └──(2) TeamsNotifier.send_approval_request ──► Bot Framework ──► Teams (1:1 con el manager)
                                                                         │
             Manager pulsa "Aprobar" ── Action.Execute ──────────────────┘
                                                │
(3) POST /api/teams/messages (Cloud Run) ◄──────┘
     ├─ valida el JWT de Bot Framework (emisor, audiencia = App ID)
     ├─ valida que quien aprueba = manager registrado en ApprovalRequest
     ├─ marca la aprobación (idempotente: un segundo clic no repite la acción)
     ├─ (4) coordinator.resume_approval(conversation_id, decision)
     │        ├─ aprobado  → Agente de Ejecución → ticket "resolved" en ServiceTonic
     │        └─ rechazado → ticket "rejected" + nota con el motivo
     ├─ (5) notifica al solicitante (Teams y la conversación del chat)
     └─ responde con la tarjeta actualizada ("✅ Aprobado por …, 12/10 10:42")
```

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `backend/adapters/teams_bot.py` | NUEVO | Cliente de Bot Framework: token de Entra ID (client credentials), envío proactivo 1:1 al manager (necesita su `conversation reference`; se obtiene al instalar la app o con Graph) |
| `backend/api/teams.py` | NUEVO | `POST /api/teams/messages`: validación del JWT de Bot Framework (JWKS de `login.botframework.com`), manejo de `adaptiveCard/action`. **Excluido** de la autenticación por API key (tiene la suya propia) |
| `backend/agents/coordinator.py` | MODIFICAR | `resume_approval(approval_id, decision, approver, comment)`: carga la conversación, ejecuta o rechaza, actualiza el ticket y agrega los mensajes al historial. Estado nuevo `rejected` |
| `backend/core/approvals.py` | MODIFICAR | Expiración (p. ej. 72 h): un job de Cloud Scheduler recuerda al manager a las 24 h y escala al nivel siguiente del organigrama a las 72 h |
| `teams-app/manifest.json` | NUEVO | Manifiesto de la app de Teams (bot, ámbitos `personal` y `team`) + íconos, empaquetado como `.zip` para el administrador |
| `infra/terraform/secrets.tf` | MODIFICAR | `teams-bot-app-id`, `teams-bot-secret` (o certificado), `teams-tenant-id` |
| `tests/integration/test_teams_approval.py` | NUEVO | Flujo completo con JWT firmado por una clave de prueba: aprobar, rechazar, clic duplicado, aprobador no autorizado (403), aprobación expirada |
| `docs/integraciones/TEAMS.md` | NUEVO | Registro en Entra ID, Azure Bot (endpoint = URL de Cloud Run), instalación de la app, permisos de Graph |

**Alternativa sin bot (si no se aprueba registrar un Azure Bot):** un flujo de
Power Automate con la acción *"Publicar tarjeta adaptable y esperar una respuesta"*
que, al recibir la respuesta, llama a `POST /api/approvals/{id}/decision` en Cloud
Run. Requiere menos desarrollo, pero suele necesitar **licencia premium** de Power
Automate para el conector HTTP, deja parte de la lógica fuera del repositorio
(más difícil de probar y versionar) y la autenticación de la llamada de vuelta
debe resolverse con una API key de rol `agent`. Se documenta como plan B en ADR-003.

**Criterio de salida:** una solicitud de laptop en dev genera una tarjeta en el
Teams del manager; al aprobar, el ticket queda resuelto en ServiceTonic, el
solicitante recibe aviso y la tarjeta muestra quién aprobó; un segundo clic no
ejecuta nada.

---

## I8 — Endurecimiento, corte a producción y retiro de ServiceNow/Slack

### Endurecimiento

- [ ] **Cloud Armor** delante de Cloud Run (balanceador HTTPS externo y dominio propio con certificado gestionado): límite de solicitudes por IP y reglas OWASP. Dejar el ingreso de Cloud Run en `internal-and-cloud-load-balancing`.
- [ ] Revisión de IAM: la cuenta de servicio sin roles de proyecto amplios; acceso a secretos por secreto.
- [ ] Rotación de secretos documentada (API keys, token de ServiceTonic y secreto del bot), con alerta de vencimiento del secreto de Entra ID.
- [ ] Pruebas de carga (p. ej. `locust`, 50 conversaciones concurrentes) para dimensionar `concurrency`, `max-instances` y la cuota de Vertex.
- [ ] Panel en Cloud Monitoring: tasa de resolución, escalaciones, aprobaciones pendientes, latencia por agente y costo de tokens (desde BigQuery).
- [ ] `docs/SEGURIDAD.md` actualizado: nuevos flujos de datos (Google, ServiceTonic, Microsoft) y qué PII sale hacia cada uno.

### Corte a producción

1. Desplegar en `prod` con `TICKETING_PROVIDER=servicetonic`, `LLM_PROVIDER=vertex`, `NOTIFY_CHANNEL=teams` y **0 % de tráfico** (`--no-traffic`).
2. Pruebas de humo contra la URL etiquetada de la revisión (`--tag=candidate`).
3. Piloto con un grupo reducido de usuarios (API keys separadas) durante 1 semana.
4. Mover el 100 % del tráfico. **Rollback:** `update-traffic` a la revisión anterior (< 1 minuto).

### Limpieza (después de 2 semanas estables)

- [ ] Eliminar `backend/adapters/servicenow.py`, las variables `SNOW_*` y `SLACK_WEBHOOK_URL`, y los alias `*_incident` de I1.
- [ ] Renombrar textos visibles "ServiceNow" en `frontend/`, `dashboard/`, `README.md` y docs C4 a un nombre neutro (p. ej. "Help Desk Multiagente").
- [ ] Decidir si se renombra el repositorio.
- [ ] Actualizar `docs/c4/` (contexto y contenedores) con GCP, ServiceTonic y Teams.

---

## Variables de entorno: resumen

| Variable | Origen | Incremento |
|----------|--------|-----------|
| `TICKETING_PROVIDER` | env | I1 |
| `LLM_PROVIDER=vertex`, `GCP_PROJECT`, `VERTEX_LOCATION`, `LLM_MODEL` | env | I2 |
| `API_KEYS` | Secret Manager | I3 |
| `STORAGE_BACKEND=firestore` | env | I4 |
| `SERVICETONIC_BASE_URL`, `SERVICETONIC_MAPPING_FILE` | env | I5 |
| `SERVICETONIC_API_TOKEN` | Secret Manager | I5 |
| `SELF_SERVICE_EXECUTOR`, `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID` | env | I6 |
| `GRAPH_CLIENT_SECRET` | Secret Manager | I6 |
| `NOTIFY_CHANNEL=teams`, `TEAMS_WORKFLOW_URL` | env / Secret Manager | I7.a |
| `TEAMS_BOT_APP_ID`, `TEAMS_BOT_SECRET`, `TEAMS_TENANT_ID` | Secret Manager | I7.b |
| `SNOW_*`, `SLACK_WEBHOOK_URL` | — | Se eliminan en I8 |

---

## Riesgos y mitigaciones

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|--------|-------|---------|------------|
| R1 | **La API de ServiceTonic no está documentada públicamente**; puede no exponer KB, organigrama o campos personalizados | Alta | Alto | I0 obtiene la referencia antes de I5; el adaptador aísla rutas y mapeos; alternativas definidas (Graph para el manager, sincronización para la KB) |
| R2 | Gemini se comporta distinto a los modelos actuales (formato JSON, filtros de seguridad, español) | Media | Medio | Evaluaciones comparativas obligatorias en I2; ajuste de prompts versionado; `LLM_PROVIDER` reversible |
| R3 | La organización no permite registrar un Azure Bot o instalar apps personalizadas en Teams | Media | Alto | Plan B con Power Automate (I7); I7.a no requiere bot |
| R4 | Cuotas o latencia de Vertex en la región elegida | Baja | Medio | Pruebas de carga en I8; reintentos ya existentes; opción de ubicación `global` |
| R5 | Datos personales (PII) salen a Google, ServiceTonic y Microsoft | Media | Alto | La redacción de Fase 0 se mantiene; revisar acuerdos de tratamiento de datos; residencia de datos en I0 |
| R6 | Acciones de autoservicio que hoy reportan éxito falso | Alta (ya ocurre en LIVE) | Alto | I6 las convierte en tickets reales hasta tener un ejecutor |
| R7 | Arranques en frío de Cloud Run degradan el chat | Media | Bajo | `min-instances=1` en prod |
| R8 | Costos no previstos (tokens, Firestore, BigQuery) | Media | Medio | Presupuesto con alertas (I3), costo por conversación en BigQuery (I4) |

---

## Estimación de costo mensual (orientativa, a validar con la calculadora de GCP)

| Componente | Supuesto | Orden de magnitud |
|------------|----------|-------------------|
| Cloud Run | 1 instancia mínima, 1 vCPU / 1 GiB | Decenas de USD |
| Vertex AI (Gemini Flash) | 5,000 conversaciones/mes × ~4 llamadas × ~2k tokens | Decenas de USD |
| Firestore, Secret Manager, Artifact Registry, Logging | Volumen bajo | Unidades a decenas de USD |
| BigQuery | < 10 GB | Prácticamente sin costo |

Las licencias de ServiceTonic y Microsoft 365 (y Power Automate premium si se elige el plan B) no se incluyen.

---

## Siguientes pasos inmediatos

1. Arrancar **I0** (solicitar la documentación de la API de ServiceTonic y el acceso al tenant de Microsoft 365 en paralelo, porque son los plazos que no dependen del equipo).
2. Mientras tanto, implementar **I1** en esta rama (no depende de nada externo).
3. Con el proyecto de GCP listo, implementar **I2** e **I3**.
