project_id   = "snow-ma-prod" # reemplazar por el proyecto real
environment  = "prod"
region       = "us-central1"
app_env      = "production"
cors_origins = "https://helpdesk.ejemplo.com" # dominio propio (plan, I8)

min_instances = 1 # sin arranques en frío en el chat
max_instances = 10
llm_provider  = "vertex"

teams_bot_app_id = ""
teams_tenant_id  = ""

# APP_ENV=production exige ServiceNow en modo LIVE y Teams configurado
extra_env = {
  SNOW_INSTANCE = ""
  SNOW_USER     = ""
}

secret_env = {
  API_KEYS               = "api-keys"
  SNOW_PASSWORD          = "snow-password"
  TEAMS_BOT_APP_PASSWORD = "teams-bot-app-password"
}

# billing_account_id          = "XXXXXX-XXXXXX-XXXXXX"
# alert_notification_channels = ["projects/snow-ma-prod/notificationChannels/123"]
