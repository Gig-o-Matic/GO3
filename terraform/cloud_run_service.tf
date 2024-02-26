locals {
  cloud_run_domain_name = "${var.cloud_run_subdomain}.${var.base_domain}"

  cloud_run_services = {
    "website" = {
      image                = var.website_image
      service_account_name = google_service_account.omatic["website"].email
      memory_mb            = "512Mi"
      min_scale            = "1"
      max_scale            = "1"
      invokers             = ["allUsers"]
      timeout_seconds      = 60 * 5 # 5 minutes
    }
    # "worker" = {
    #   image                   = var.worker_image
    #   service_account_name    = google_service_account.omatic["worker"].email
    #   min_scale               = "0"
    #   max_scale               = "1"
    #   memory_mb               = "1Gi"
    #   invokers                = ["serviceAccount:${google_service_account.omatic["worker-pubsub-invoker"].email}"]
    #   timeout_seconds         = 60 * 30 # 30 minutes
    # }
  }
}

resource "google_cloud_run_service" "omatic" {
  provider                   = google-beta
  for_each                   = local.cloud_run_services
  name                       = each.key
  location                   = var.gcp_region
  autogenerate_revision_name = true

  traffic {
    percent         = 100
    latest_revision = true
  }

  metadata {
    annotations = {
      "run.googleapis.com/launch-stage" = "BETA"
    }
  }

  template {

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"         = each.value.min_scale
        "autoscaling.knative.dev/maxScale"         = each.value.max_scale
        "run.googleapis.com/cloudsql-instances"    = google_sql_database_instance.omatic.connection_name
        "run.googleapis.com/client-name"           = each.key
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/launch-stage"          = "BETA"
      }
    }

    spec {
      service_account_name = each.value.service_account_name

      timeout_seconds = each.value.timeout_seconds

      containers {
        image = each.value.image

        env {
          name = "SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secret_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.database_url.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name  = "CLOUDRUN_SERVICE_URL"
          value = "https://${local.cloud_run_domain_name}"
        }

        env {
          name  = "GS_BUCKET_NAME"
          value = google_storage_bucket.statics.name
        }

        env {
          name  = "LOG_LEVEL"
          value = upper(var.app_log_level)
        }

        ports {
          name           = "http1"
          container_port = "8080"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = each.value.memory_mb
          }
        }
      }
    }
  }
}

resource "google_cloud_run_domain_mapping" "omatic" {
  location = var.gcp_region
  name     = local.cloud_run_domain_name

  metadata {
    namespace = var.gcp_project_id
  }

  spec {
    route_name = google_cloud_run_service.omatic["website"].name
  }
}
