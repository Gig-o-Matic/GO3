resource "google_project_iam_member" "project_editors" {
  for_each = toset(var.gcp_project_editors)
  project  = var.gcp_project_id
  role     = "roles/editor"
  member   = "user:${each.value}"
}

locals {
  service_account_ids = {
    "website" = "gig-o-matic frontend website"
    # "worker-pubsub-invoker" = "gig-o-matic pubsub to worker invoker"
    # "worker"                = "gig-o-matic background worker"
  }
}

resource "time_rotating" "mykey_rotation" {
  rotation_days = 30
}

resource "google_service_account" "omatic" {
  for_each     = local.service_account_ids
  account_id   = each.key
  display_name = each.value
}

resource "google_cloud_run_service_iam_policy" "omatic" {
  for_each = google_cloud_run_service.omatic
  location = each.value.location
  project  = each.value.project
  service  = each.value.name

  policy_data = data.google_iam_policy.omatic[each.key].policy_data
}

data "google_iam_policy" "omatic" {
  for_each = local.cloud_run_services
  binding {
    role    = "roles/run.invoker"
    members = each.value.invokers
  }
}

resource "google_project_iam_binding" "omatic_cloudsql_clients" {
  project = var.gcp_project_id
  for_each = toset([
    "roles/cloudsql.instanceUser",
    "roles/cloudsql.client",
  ])
  role = each.value
  members = [
    "serviceAccount:${google_service_account.omatic["website"].email}",
    # "serviceAccount:${google_service_account.omatic["worker"].email}",

  ]
}

resource "google_project_iam_binding" "omatic_trace_agents" {
  project = var.gcp_project_id
  role    = "roles/cloudtrace.agent"
  members = [
    "serviceAccount:${google_service_account.omatic["website"].email}",
    # "serviceAccount:${google_service_account.omatic["worker"].email}",
  ]
}

resource "google_service_account_iam_binding" "allow_sa_impersonation_tokens" {
  service_account_id = google_service_account.omatic["website"].name
  role               = "roles/iam.serviceAccountTokenCreator"
  members            = [for u in var.gcp_project_editors : "user:${u}"]
}

resource "google_service_account_iam_binding" "allow_sa_impersonation" {
  service_account_id = google_service_account.omatic["website"].name
  role               = "roles/iam.serviceAccountUser"
  members            = [for u in var.gcp_project_editors : "user:${u}"]
}

data "google_iam_policy" "secret_accessor" {
  binding {
    role = "roles/secretmanager.secretAccessor"
    members = [
      "serviceAccount:${google_service_account.omatic["website"].email}",
      # "serviceAccount:${google_service_account.omatic["worker"].email}",
    ]
  }
}

resource "google_secret_manager_secret_iam_policy" "database_url_access" {
  project     = google_secret_manager_secret.database_url.project
  secret_id   = google_secret_manager_secret.database_url.id
  policy_data = data.google_iam_policy.secret_accessor.policy_data
}

resource "google_secret_manager_secret_iam_policy" "secret_key_access" {
  project     = google_secret_manager_secret.secret_key.project
  secret_id   = google_secret_manager_secret.secret_key.id
  policy_data = data.google_iam_policy.secret_accessor.policy_data
}
