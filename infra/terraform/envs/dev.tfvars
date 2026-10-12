project_id   = "snow-ma-dev" # reemplazar por el proyecto real
environment  = "dev"
region       = "us-central1"
app_env      = "staging" # 'production' exige ServiceNow LIVE y Teams configurado
cors_origins = "https://snow-multiagent-api-REEMPLAZAR.a.run.app"

min_instances = 0
max_instances = 3
llm_provider  = "vertex"

# Rellenar cuando exista el registro del bot en Entra ID (docs/integraciones/TEAMS.md)
teams_bot_app_id = ""
teams_tenant_id  = ""

# Solo secretos que ya tienen una versión cargada
secret_env = {
  API_KEYS = "api-keys"
  # TEAMS_BOT_APP_PASSWORD = "teams-bot-app-password"
  # TEAMS_WORKFLOW_URL     = "teams-workflow-url"
}
