# Guía de despliegue — Google Cloud (Cloud Run + Vertex AI)

> Fase 2, incrementos I2–I4 del [plan](PLAN_FASE2_GOOGLE_CLOUD.md). Para el
> despliegue local con contenedores ver [DESPLIEGUE.md](DESPLIEGUE.md).

## Arquitectura

```
GitHub Actions ──(WIF, sin llaves)──► Artifact Registry ──► Cloud Run: snow-multiagent-api
                                                              │  cuenta de servicio snow-ma-run
                                                              ├──► Vertex AI (Gemini)       LLM_PROVIDER=vertex
                                                              ├──► Firestore                STORAGE_BACKEND=firestore
                                                              ├──► Secret Manager           API_KEYS, secretos de Teams/ServiceNow
                                                              ├──► ServiceNow               TICKETING_PROVIDER=servicenow
                                                              └──► Microsoft Teams          NOTIFY_CHANNEL=teams
                         stdout JSON ──► Cloud Logging ──┬──► bucket "snow-ma-audit" (365 días)
                                                         └──► BigQuery snow_ma_telemetry
```

Todo está en [infra/terraform/](../infra/terraform/). El pipeline
[deploy-gcp.yml](../.github/workflows/deploy-gcp.yml) solo publica imágenes y
revisiones; la infraestructura la cambia Terraform.

## Requisitos

- Proyecto de GCP por entorno (`dev`, `prod`) con facturación activa.
- `gcloud` y Terraform ≥ 1.6 en la máquina de quien hace el bootstrap.
- Rol `Owner` (o `Editor` + `Security Admin`) en el proyecto **solo para el bootstrap**.

## 1. Bootstrap (una vez por entorno)

```bash
export PROJECT=snow-ma-dev REGION=us-central1 ENV=dev
gcloud auth login && gcloud auth application-default login
gcloud config set project "$PROJECT"

# Bucket del estado de Terraform (versionado)
gcloud storage buckets create "gs://${PROJECT}-tfstate" --location="$REGION" --uniform-bucket-level-access
gcloud storage buckets update "gs://${PROJECT}-tfstate" --versioning
```

Editar `infra/terraform/envs/$ENV.tfvars` (proyecto, `cors_origins`) y
`envs/$ENV.backend.hcl` (nombre del bucket).

## 2. Primera aplicación de Terraform

```bash
make gcp-init ENV=dev
make gcp-plan ENV=dev
make gcp-apply ENV=dev
```

La primera vez Cloud Run arranca con una imagen de ejemplo (`hello`); el
pipeline la reemplaza en el paso 5. Si el proyecto ya tenía Firestore:

```bash
terraform -chdir=infra/terraform import -var-file=envs/dev.tfvars \
  google_firestore_database.main "projects/$PROJECT/databases/(default)"
```

## 3. Cargar los secretos

Terraform crea los secretos **vacíos** (los valores no deben quedar en el
estado). Cargar cada valor y después listarlo en `secret_env` del `.tfvars`:

```bash
# API_KEYS: formato clave:rol,clave:rol
KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
printf '%s' "${KEY}:admin" | gcloud secrets versions add api-keys --data-file=-

# Teams (cuando exista el bot; ver docs/integraciones/TEAMS.md)
printf '%s' "$SECRETO_DEL_BOT" | gcloud secrets versions add teams-bot-app-password --data-file=-
```

> Un secreto en `secret_env` **sin ninguna versión** hace fallar el
> despliegue de la revisión. Por eso `dev.tfvars` solo incluye `API_KEYS`.

Volver a ejecutar `make gcp-plan gcp-apply ENV=dev`.

## 4. Conectar GitHub Actions

En GitHub → *Settings → Environments*, crear `dev` y `prod` (en `prod`, con
revisores obligatorios) y definir estas **variables** (no son secretos):

| Variable | Valor |
|----------|-------|
| `GCP_PROJECT_ID` | ID del proyecto |
| `GCP_REGION` | `us-central1` |
| `GCP_WIF_PROVIDER` | `terraform output -raw workload_identity_provider` |
| `GCP_DEPLOYER_SA` | `terraform output -raw deployer_service_account` |
| `CLOUD_RUN_SERVICE` | `snow-multiagent-api` |

El proveedor de identidad solo acepta tokens de `ABRAHAMCIMAT/servicenow-multiagent`
emitidos para un job del environment del mismo nombre.

## 5. Desplegar

| Disparador | Entorno |
|------------|---------|
| CI en verde en `main` | `dev` |
| Tag `vX.Y.Z` | `prod` (requiere aprobación del environment) |
| *Run workflow* manual | el que se elija |

Cada despliegue publica la revisión **sin tráfico**, prueba `/api/health`
en su URL etiquetada y solo entonces le pasa el 100 % del tráfico.

**Rollback** (menos de un minuto):

```bash
gcloud run revisions list --service snow-multiagent-api --region us-central1
gcloud run services update-traffic snow-multiagent-api --region us-central1 \
  --to-revisions=<revision-anterior>=100
```

## 6. Verificar

```bash
URL=$(terraform -chdir=infra/terraform output -raw service_url)
curl -fsS "$URL/api/health"
curl -fsS -H "X-API-Key: $KEY" "$URL/api/health/detail"
# → llm_provider: vertex, storage_backend: firestore, notification_channel: teams
```

Logs: *Cloud Logging* con `resource.labels.service_name="snow-multiagent-api"`.
Auditoría: bucket `snow-ma-audit`. Telemetría: dataset `snow_ma_telemetry`.

## Vertex AI en local

```bash
gcloud auth application-default login
export LLM_PROVIDER=vertex GCP_PROJECT=snow-ma-dev VERTEX_LOCATION=us-central1
python -m backend.server
```

`VERTEX_MODEL` cambia el modelo (por defecto `google/gemini-2.5-flash`).
Antes de usarlo en producción, comparar contra la línea base actual con
`scripts/run_evals.py` (plan, I2).

## Configuración del servicio

| Variable | Valor en Cloud Run | Notas |
|----------|--------------------|-------|
| `APP_ENV` | `staging` (dev) / `production` (prod) | `production` exige ServiceNow LIVE y Teams configurado |
| `LLM_PROVIDER` | `vertex` | `mock` para probar la infraestructura sin costo de modelo |
| `STORAGE_BACKEND` | `firestore` | conversaciones y aprobaciones compartidas entre instancias |
| `NOTIFY_CHANNEL` | `teams` | |
| `TICKETING_PROVIDER` | `servicenow` | `servicetonic` cuando se cubran sus requerimientos (I5) |
| `STRUCTURED_STDOUT` | automático (`K_SERVICE`) | logs, auditoría y telemetría como JSON en stdout |

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---------|-------|----------|
| La revisión no arranca: *secret ... has no versions* | Un secreto en `secret_env` sin valor | Cargar la versión (paso 3) o quitarlo de `secret_env` |
| `RuntimeError: ServiceNow debe estar en modo LIVE en produccion` | `APP_ENV=production` sin credenciales de ServiceNow | Configurar `SNOW_*` o usar `staging` |
| 403 al asignar `allUsers` como invoker | Política *Domain Restricted Sharing* de la organización | Excepción para el proyecto, o balanceador + IAP; el bot de Teams necesita un endpoint público |
| `PERMISSION_DENIED` en Vertex AI | Falta `roles/aiplatform.user` o la API no está habilitada | `make gcp-apply`; revisar la región de `VERTEX_LOCATION` |
| El pipeline falla en *Autenticar en Google Cloud* | El job no corre en el environment correcto o la variable `GCP_WIF_PROVIDER` es incorrecta | Revisar el paso 4 |
