# Identidad del servicio en ejecución: mínimo privilegio.
resource "google_service_account" "runtime" {
  account_id   = "snow-ma-run"
  display_name = "Cloud Run: sistema multiagente (${var.environment})"
}

locals {
  runtime_roles = [
    "roles/aiplatform.user",   # Vertex AI (Gemini)
    "roles/datastore.user",    # Firestore
    "roles/logging.logWriter", # Cloud Logging
    "roles/monitoring.metricWriter",
  ]
}

resource "google_project_iam_member" "runtime" {
  for_each = toset(local.runtime_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.runtime.email}"
}

# Identidad del pipeline de GitHub Actions (vía Workload Identity Federation).
resource "google_service_account" "deployer" {
  account_id   = "snow-ma-deploy"
  display_name = "GitHub Actions: despliegue (${var.environment})"
}

resource "google_project_iam_member" "deployer_run" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_artifact_registry_repository_iam_member" "deployer_push" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

# Para desplegar una revisión que corre como snow-ma-run
resource "google_service_account_iam_member" "deployer_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}
