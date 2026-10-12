# Fase 2 (I3): infraestructura en Google Cloud para el sistema multiagente.
# Un estado de Terraform por entorno, en un bucket de GCS:
#   terraform init -backend-config=envs/dev.backend.hcl
#   terraform apply -var-file=envs/dev.tfvars
terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  backend "gcs" {}
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

data "google_project" "this" {
  project_id = var.project_id
}
