#!/usr/bin/env bash
# Bootstrap único ejecutado por un administrador desde Google Cloud Shell.
# Crea proyecto/estado remoto y materializa WIF sin generar llaves JSON.
set -euo pipefail

required=(PROJECT_ID BILLING_ACCOUNT_ID ENVIRONMENT STATE_BUCKET)
for name in "${required[@]}"; do
  test -n "${!name:-}" || { echo "Falta la variable $name" >&2; exit 2; }
done

case "$ENVIRONMENT" in
  dev|prod) ;;
  *) echo "ENVIRONMENT debe ser dev o prod" >&2; exit 2 ;;
esac

REGION="${REGION:-us-central1}"
TF_DIR="${TF_DIR:-infra/terraform}"

if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  create_args=("$PROJECT_ID" "--name=Valkiria ${ENVIRONMENT}")
  if test -n "${FOLDER_ID:-}"; then
    create_args+=("--folder=$FOLDER_ID")
  elif test -n "${ORGANIZATION_ID:-}"; then
    create_args+=("--organization=$ORGANIZATION_ID")
  fi
  gcloud projects create "${create_args[@]}"
fi

gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com storage.googleapis.com \
  --project="$PROJECT_ID"

if ! gcloud storage buckets describe "gs://$STATE_BUCKET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$STATE_BUCKET" --project="$PROJECT_ID" \
    --location="$REGION" --uniform-bucket-level-access
fi
gcloud storage buckets update "gs://$STATE_BUCKET" --versioning

terraform -chdir="$TF_DIR" init -reconfigure \
  -backend-config="bucket=$STATE_BUCKET" \
  -backend-config="prefix=snow-multiagent"

# Primera aplicación deliberadamente acotada. Cloud Run se crea después de
# cargar la primera versión de API_KEYS en Secret Manager.
terraform -chdir="$TF_DIR" apply \
  -var-file="envs/${ENVIRONMENT}.tfvars" \
  -var="project_id=$PROJECT_ID" \
  -var="environment=$ENVIRONMENT" \
  -var="region=$REGION" \
  -target=google_project_service.apis \
  -target=google_artifact_registry_repository.images \
  -target=google_service_account.runtime \
  -target=google_service_account.deployer \
  -target=google_project_iam_member.runtime \
  -target=google_project_iam_member.deployer_run \
  -target=google_project_iam_member.deployer_audit \
  -target=google_artifact_registry_repository_iam_member.deployer_push \
  -target=google_service_account_iam_member.deployer_acts_as_runtime \
  -target=google_iam_workload_identity_pool.github \
  -target=google_iam_workload_identity_pool_provider.github \
  -target=google_service_account_iam_member.deployer_wif \
  -target=google_secret_manager_secret.app \
  -target=google_secret_manager_secret_iam_member.deployer_rotator

echo
echo "Bootstrap completado. Configure el environment de GitHub con:"
terraform -chdir="$TF_DIR" output deployer_service_account
terraform -chdir="$TF_DIR" output workload_identity_provider
echo "GCP_PROJECT_ID=$PROJECT_ID"
echo "GCP_REGION=$REGION"
