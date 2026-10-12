variable "project_id" {
  description = "Proyecto de Google Cloud del entorno."
  type        = string
}

variable "environment" {
  description = "Nombre corto del entorno (dev, prod)."
  type        = string
}

variable "region" {
  description = "Región de Cloud Run, Artifact Registry y Vertex AI."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Nombre del servicio de Cloud Run."
  type        = string
  default     = "snow-multiagent-api"
}

variable "image" {
  description = "Imagen inicial. Después la actualiza el pipeline (deploy-gcp.yml) y Terraform la ignora."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "app_env" {
  description = "APP_ENV. 'production' exige ServiceNow LIVE y Teams configurado (fail-fast de Fase 0)."
  type        = string
  default     = "staging"
}

variable "cors_origins" {
  description = "Orígenes permitidos (CORS_ORIGINS), separados por coma."
  type        = string
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 5
}

variable "concurrency" {
  type    = number
  default = 40
}

variable "vertex_location" {
  type    = string
  default = "us-central1"
}

variable "vertex_model" {
  type    = string
  default = "google/gemini-2.5-flash"
}

variable "llm_provider" {
  description = "vertex | mock (mock permite probar la infraestructura sin costo de modelo)."
  type        = string
  default     = "vertex"
}

variable "teams_bot_app_id" {
  description = "App ID (Entra ID) del bot de Teams. Vacío = Teams en modo Workflows o demo."
  type        = string
  default     = ""
}

variable "teams_tenant_id" {
  type    = string
  default = ""
}

variable "extra_env" {
  description = "Variables de entorno adicionales en texto plano (p. ej. SNOW_INSTANCE)."
  type        = map(string)
  default     = {}
}

variable "secret_env" {
  description = <<-EOT
    Variables de entorno que se leen de Secret Manager: { VARIABLE = id-del-secreto }.
    Solo incluir secretos que YA tengan al menos una versión (ver docs/DESPLIEGUE_GCP.md);
    si no, Cloud Run rechaza la revisión.
  EOT
  type        = map(string)
  default     = { API_KEYS = "api-keys" }
}

variable "firestore_location" {
  description = "Ubicación de Firestore (no se puede cambiar después de crearla)."
  type        = string
  default     = "nam5"
}

variable "bigquery_location" {
  type    = string
  default = "US"
}

variable "github_repository" {
  description = "Repositorio autorizado a desplegar con Workload Identity Federation (owner/repo)."
  type        = string
  default     = "ABRAHAMCIMAT/valkiria_servitonic"
}

variable "alert_notification_channels" {
  description = "IDs de canales de notificación de Cloud Monitoring para las alertas."
  type        = list(string)
  default     = []
}

variable "billing_account_id" {
  description = "Cuenta de facturación para la alerta de presupuesto. Vacío = sin presupuesto."
  type        = string
  default     = ""
}

variable "monthly_budget_usd" {
  type    = number
  default = 200
}
