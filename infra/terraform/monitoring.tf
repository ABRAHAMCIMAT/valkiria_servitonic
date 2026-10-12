resource "google_monitoring_alert_policy" "api_5xx" {
  display_name          = "snow-ma ${var.environment}: errores 5xx"
  combiner              = "OR"
  notification_channels = var.alert_notification_channels

  conditions {
    display_name = "Respuestas 5xx sostenidas"
    condition_threshold {
      filter          = "${local.service_filter} AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05 # solicitudes 5xx por segundo
      duration        = "300s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_monitoring_alert_policy" "api_latency" {
  display_name          = "snow-ma ${var.environment}: latencia p95 alta"
  combiner              = "OR"
  notification_channels = var.alert_notification_channels

  conditions {
    display_name = "Latencia p95 > 15 s"
    condition_threshold {
      filter          = "${local.service_filter} AND metric.type=\"run.googleapis.com/request_latencies\""
      comparison      = "COMPARISON_GT"
      threshold_value = 15000 # ms
      duration        = "600s"

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
        cross_series_reducer = "REDUCE_MAX"
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_billing_budget" "monthly" {
  count           = var.billing_account_id == "" ? 0 : 1
  billing_account = var.billing_account_id
  display_name    = "snow-ma-${var.environment}"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}
