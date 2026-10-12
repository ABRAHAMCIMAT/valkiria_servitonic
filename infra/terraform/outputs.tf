output "service_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "artifact_registry" {
  description = "Prefijo de las imágenes: <este valor>/api:<tag>"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "runtime_service_account" {
  value = google_service_account.runtime.email
}

output "deployer_service_account" {
  description = "Variable GCP_DEPLOYER_SA del environment de GitHub."
  value       = google_service_account.deployer.email
}

output "workload_identity_provider" {
  description = "Variable GCP_WIF_PROVIDER del environment de GitHub."
  value       = google_iam_workload_identity_pool_provider.github.name
}
