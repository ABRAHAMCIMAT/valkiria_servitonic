# Terraform crea los secretos VACÍOS; los valores se cargan fuera de Terraform
# (no deben quedar en el estado). Ver docs/DESPLIEGUE_GCP.md, paso 3:
#   printf '%s' "$VALOR" | gcloud secrets versions add <id> --data-file=-
locals {
  secret_ids = toset([
    "api-keys",               # API_KEYS (clave:rol,...)
    "teams-bot-app-password", # secreto de cliente del bot (Entra ID)
    "teams-workflow-url",     # URL del webhook de Workflows (contiene una firma)
    "snow-password",          # ServiceNow (mientras siga siendo el sistema de tickets)
    "snow-token",
    "servicetonic-api-token", # I5, cuando se definan los requerimientos
  ])
}

resource "google_secret_manager_secret" "app" {
  for_each  = local.secret_ids
  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Acceso por secreto (no a nivel de proyecto)
resource "google_secret_manager_secret_iam_member" "runtime" {
  # La cuenta de ejecución solo accede a los secretos montados en este
  # entorno, no a todos los contenedores de secretos futuros o inactivos.
  for_each  = toset(values(var.secret_env))
  secret_id = google_secret_manager_secret.app[each.value].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
