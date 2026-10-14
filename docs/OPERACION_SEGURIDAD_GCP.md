# Operación de cierre de seguridad en GCP

> Estado 14/10/2026: automatización publicada en `main`; ejecución bloqueada
> hasta crear el primer proyecto y vincular una cuenta de facturación.

## Estado de prerrequisitos

Los proyectos GCP todavía no existen y no hay secretos operativos configurados.
Por tanto, ninguna prueba contra dev/prod ni rotación real puede ejecutarse
hasta completar el bootstrap. WIF evita llaves JSON, pero necesita una primera
aplicación autenticada por un administrador de GCP.

## 1. Bootstrap único por entorno

Un administrador debe ejecutar desde Cloud Shell:

1. Crear el proyecto con un ID globalmente único.
2. Vincular la cuenta de facturación.
3. Crear el bucket de estado Terraform con versionado y acceso uniforme.
4. Sustituir los marcadores en:
   - `infra/terraform/envs/<entorno>.tfvars`
   - `infra/terraform/envs/<entorno>.backend.hcl`
5. Ejecutar `terraform init` y aplicar primero APIs, cuentas de servicio, WIF,
   Artifact Registry y contenedores de Secret Manager.
6. Cargar la primera versión de `api-keys` por un canal seguro.
7. Ejecutar el `terraform apply` completo.

El repositorio incluye un bootstrap parametrizado para los pasos 1–5:

```bash
export PROJECT_ID='<id-globalmente-unico>'
export BILLING_ACCOUNT_ID='<cuenta-de-facturacion>'
export ENVIRONMENT='dev'
export STATE_BUCKET='<bucket-globalmente-unico>'
export REGION='us-central1'
# Opcional: export FOLDER_ID=... o ORGANIZATION_ID=...
./scripts/bootstrap_gcp_wif.sh
```

El script no genera ni imprime secretos y se detiene antes de crear Cloud Run.
Después se carga `api-keys`, se actualizan los valores reales del entorno y se
ejecuta el apply completo desde una identidad ya federada.

WIF no puede crear su propia confianza inicial; esta es la única operación que
requiere identidad administrativa directa. No se deben crear claves JSON.

## 2. Variables de los environments de GitHub

Crear `dev` y `prod` en **Settings → Environments**. Configurar:

| Variable | Origen |
|---|---|
| `GCP_PROJECT_ID` | ID real del proyecto |
| `GCP_REGION` | Región de Cloud Run |
| `GCP_WIF_PROVIDER` | `terraform output workload_identity_provider` |
| `GCP_DEPLOYER_SA` | `terraform output deployer_service_account` |
| `CLOUD_RUN_SERVICE` | Nombre del servicio |
| `CORS_ORIGIN` | Origen autorizado real |
| `BIGQUERY_DATASET` | `valkiria_telemetry` |

Secretos requeridos para las verificaciones:

- `SECURITY_USER_KEY`
- `SECURITY_AGENT_KEY`
- `SECURITY_ADMIN_KEY`

Configurar **required reviewers**, especialmente en `prod`. El aprobador debe
ser una persona distinta de quien dispara el workflow.

## 3. Verificación dev y producción

Ejecutar **Actions → Verificar seguridad GCP → Run workflow**. El workflow:

1. Ejecuta las 12 comprobaciones de autenticación, RBAC, CORS y guardrails.
2. Envía canarios sintéticos de PII y secreto.
3. Comprueba que el valor crudo no aparece en Cloud Logging ni BigQuery.
4. Lista roles efectivos de las cuentas runtime/deployer.
5. Falla si existe cualquier clave de cuenta de servicio administrada por el
   usuario.
6. Conserva un artefacto de evidencia durante 365 días.

Primero debe aprobarse `dev`; después se repite exactamente en `prod`.

## 4. Rotación de API keys

Preparar en cada environment, sin poner valores en inputs del workflow:

- `API_KEYS_ROTATION_OVERLAP`: claves anteriores y nuevas juntas.
- `API_KEYS_ROTATION_FINAL`: solo claves nuevas.
- `SECURITY_USER_KEY_NEXT`, `SECURITY_AGENT_KEY_NEXT`,
  `SECURITY_ADMIN_KEY_NEXT`: claves nuevas individuales para el smoke test.

Ejecutar **Rotar secretos GCP** con `api-keys-overlap`, migrar consumidores y
verificar. Después ejecutar `api-keys-finalize`. Conservar ambos artefactos.

## 5. Rotación del bot de Teams

1. Un administrador de Entra ID crea un secreto nuevo sin retirar el vigente.
2. Guardarlo como `TEAMS_BOT_APP_PASSWORD_NEXT` en el environment de GitHub.
3. Ejecutar **Rotar secretos GCP** con operación `teams-bot`.
4. Probar una aprobación real en Teams.
5. Retirar el secreto anterior en Entra ID solo después de la prueba.

El workflow nunca puede crear el secreto de Entra ID sin autorización de
Microsoft; únicamente rota su copia en Secret Manager y Cloud Run.

## 6. Cierre y aprobación

El segundo responsable debe descargar el artefacto, revisar los resultados y
aprobar el deployment del environment. Registrar URL de la ejecución, ticket de
cambio, revisor y fecha en el sistema de control de cambios de la organización.
