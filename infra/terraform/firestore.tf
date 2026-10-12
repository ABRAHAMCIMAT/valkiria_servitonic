# Si el proyecto ya tiene la base "(default)":
#   terraform import google_firestore_database.main "projects/<proyecto>/databases/(default)"
resource "google_firestore_database" "main" {
  name            = "(default)"
  location_id     = var.firestore_location
  type            = "FIRESTORE_NATIVE"
  deletion_policy = "ABANDON"

  depends_on = [google_project_service.apis]
}

# Borrado automático de conversaciones viejas (campo `expire_at`, que escribe
# backend/core/firestore_store.py según FIRESTORE_TTL_DAYS).
resource "google_firestore_field" "conversations_ttl" {
  database   = google_firestore_database.main.name
  collection = "conversations"
  field      = "expire_at"

  ttl_config {}
  index_config {}
}
