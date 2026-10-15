locals {
  plain_env = merge(
    {
      APP_ENV            = var.app_env
      HOST               = "0.0.0.0"
      CORS_ORIGINS       = var.cors_origins
      LLM_PROVIDER       = var.llm_provider
      GCP_PROJECT        = var.project_id
      VERTEX_LOCATION    = var.vertex_location
      VERTEX_MODEL       = var.vertex_model
      STORAGE_BACKEND    = "firestore"
      TICKETING_PROVIDER = "servicenow"
      NOTIFY_CHANNEL     = "teams"
      TEAMS_BOT_APP_ID   = var.teams_bot_app_id
      TEAMS_TENANT_ID    = var.teams_tenant_id
      LOG_LEVEL          = "INFO"
    },
    var.extra_env,
  )
}

resource "google_cloud_run_v2_service" "api" {
  name                = var.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = var.environment == "prod"

  template {
    service_account                  = google_service_account.runtime.email
    max_instance_request_concurrency = var.concurrency
    timeout                          = "120s" # las llamadas al LLM pueden tardar

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = local.plain_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      # /api/health es público y no expone configuración (Fase 0)
      startup_probe {
        http_get {
          path = "/api/health"
        }
        period_seconds    = 5
        timeout_seconds   = 3
        failure_threshold = 12
      }

      liveness_probe {
        http_get {
          path = "/api/health"
        }
        period_seconds  = 30
        timeout_seconds = 5
      }
    }
  }

  lifecycle {
    # La imagen la publica el pipeline (deploy-gcp.yml), no Terraform
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.runtime,
    google_project_iam_member.runtime,
  ]
}

# Acceso público a nivel de red: la app exige API keys (Fase 0) y el bot de
# Teams necesita un endpoint alcanzable por Microsoft. Si la organización
# bloquea allUsers (Domain Restricted Sharing), ver docs/DESPLIEGUE_GCP.md.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
