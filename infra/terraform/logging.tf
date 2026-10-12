# La app escribe JSON por stdout (STRUCTURED_STDOUT, activo en Cloud Run) con
# log_type = "audit" | "telemetry". Dos sinks los separan del resto de logs.
locals {
  service_filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.service_name}\""
}

# Auditoría: bucket de logs con retención de 1 año
resource "google_logging_project_bucket_config" "audit" {
  project        = var.project_id
  location       = "global"
  bucket_id      = "snow-ma-audit"
  retention_days = 365
}

resource "google_logging_project_sink" "audit" {
  name                   = "snow-ma-audit"
  destination            = "logging.googleapis.com/${google_logging_project_bucket_config.audit.id}"
  filter                 = "${local.service_filter} AND jsonPayload.log_type=\"audit\""
  unique_writer_identity = true
}

# Telemetría: BigQuery para el histórico de métricas y costo de tokens
resource "google_bigquery_dataset" "telemetry" {
  dataset_id  = "snow_ma_telemetry"
  location    = var.bigquery_location
  description = "Eventos de telemetría del sistema multiagente (sink de Cloud Logging)"

  depends_on = [google_project_service.apis]
}

resource "google_logging_project_sink" "telemetry" {
  name                   = "snow-ma-telemetry"
  destination            = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.telemetry.dataset_id}"
  filter                 = "${local.service_filter} AND jsonPayload.log_type=\"telemetry\""
  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }
}

resource "google_bigquery_dataset_iam_member" "telemetry_sink" {
  dataset_id = google_bigquery_dataset.telemetry.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.telemetry.writer_identity
}
