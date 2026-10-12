resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "snow-multiagent"
  format        = "DOCKER"
  description   = "Imágenes del sistema multiagente"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "conservar-recientes"
    action = "KEEP"
    most_recent_versions {
      keep_count = 15
    }
  }

  cleanup_policies {
    id     = "borrar-antiguas"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30 días
    }
  }

  depends_on = [google_project_service.apis]
}
