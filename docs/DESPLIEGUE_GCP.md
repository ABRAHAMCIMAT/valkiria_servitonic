# Despliegue del stack Google Cloud

> Arquitectura objetivo: ServiceTonic + Microsoft Teams + Google Cloud.
> Estado: IaC y workflows listos; proyectos dev/prod pendientes de creación.

## Stack

```text
GitHub Actions --WIF--> Artifact Registry --> Cloud Run
                                             |--> Vertex AI
                                             |--> Firestore
                                             |--> Secret Manager
                                             |--> ServiceTonic REST API
                                             `--> Microsoft Teams Bot/Graph

Cloud Run stdout --> Cloud Logging --> BigQuery
Cloud Monitoring  --> alertas/SLO
Cloud Scheduler   --> recordatorios/jobs
Cloud Armor/LB    --> protección perimetral productiva
```

## Servicios

| Servicio | Recurso sugerido |
|---|---|
| Cloud Run | `valkiria-servitonic-api` |
| Artifact Registry | `valkiria-servitonic` |
| Runtime SA | `valkiria-run@PROJECT_ID` |
| Deployer SA | `valkiria-deploy@PROJECT_ID` |
| Firestore | `(default)` modo nativo |
| BigQuery | `valkiria_telemetry` |
| Logging bucket | `valkiria-audit` |
| Secret Manager | `api-keys`, `servicetonic-api-token`, secretos Teams |

## Bootstrap

Desde Google Cloud Shell:

```bash
export PROJECT_ID='<id-globalmente-unico>'
export BILLING_ACCOUNT_ID='<cuenta-facturacion>'
export ENVIRONMENT=dev
export STATE_BUCKET="${PROJECT_ID}-tfstate"
export REGION=us-central1
./scripts/bootstrap_gcp_wif.sh
```

El bootstrap crea proyecto, facturación, estado remoto, APIs, cuentas de
servicio, WIF, Artifact Registry y contenedores de secretos. No crea llaves JSON.

## Secretos iniciales

| Variable Cloud Run | Secret Manager |
|---|---|
| `API_KEYS` | `api-keys` |
| `SERVICETONIC_API_TOKEN` | `servicetonic-api-token` |
| `TEAMS_BOT_APP_PASSWORD` | `teams-bot-app-password` |
| `TEAMS_WORKFLOW_URL` | `teams-workflow-url` |
| `GRAPH_CLIENT_SECRET` | `graph-client-secret` |

Los valores se cargan fuera de Terraform y nunca se imprimen o versionan.

## Variables no secretas

```text
APP_ENV=staging|production
LLM_PROVIDER=vertex
GCP_PROJECT=<project-id>
VERTEX_LOCATION=us-central1
STORAGE_BACKEND=firestore
TICKETING_PROVIDER=servicetonic
SERVICETONIC_BASE_URL=<api-base-url>
NOTIFY_CHANNEL=teams
TEAMS_BOT_APP_ID=<app-id>
TEAMS_TENANT_ID=<tenant-id>
```

## GitHub Environments

Crear `dev` y `prod`. Producción requiere revisores obligatorios.

| Variable | Valor |
|---|---|
| `GCP_PROJECT_ID` | Proyecto del entorno |
| `GCP_REGION` | Región Cloud Run |
| `GCP_WIF_PROVIDER` | Output Terraform |
| `GCP_DEPLOYER_SA` | Output Terraform |
| `CLOUD_RUN_SERVICE` | `valkiria-servitonic-api` |
| `CORS_ORIGIN` | Dominio permitido |
| `BIGQUERY_DATASET` | `valkiria_telemetry` |

## Aplicación Terraform

```bash
terraform -chdir=infra/terraform init \
  -backend-config="bucket=$STATE_BUCKET" \
  -backend-config="prefix=valkiria-servitonic"

terraform -chdir=infra/terraform plan \
  -var-file="envs/${ENVIRONMENT}.tfvars" \
  -var="project_id=$PROJECT_ID" \
  -out="${ENVIRONMENT}.tfplan"

terraform -chdir=infra/terraform apply "${ENVIRONMENT}.tfplan"
```

## Despliegue

El workflow `deploy-gcp.yml`:

1. Autentica con WIF.
2. Construye y publica la imagen.
3. Crea revisión Cloud Run sin tráfico.
4. Ejecuta health check.
5. Mueve tráfico solo si la revisión es saludable.

## Verificación

Ejecutar `security-gcp.yml` primero en dev y luego en prod. Valida RBAC,
CORS, endpoints, canarios de PII/secretos, IAM, llaves JSON, Logging y BigQuery.

## Producción

- Cloud Armor y HTTPS Load Balancer.
- Mínimo privilegio por cuenta y secreto.
- `min-instances` conforme al SLO.
- Presupuesto y alertas Vertex/Cloud Run.
- Rotación de API keys, ServiceTonic y Teams.
- Pruebas de carga y rollback documentado.

Ver [operación de seguridad](OPERACION_SEGURIDAD_GCP.md) y
[plan incremental](PLAN_FASE2_GOOGLE_CLOUD.md).
