locals {
  website_postgres_connection_url = join(
    "",
    [
      "postgres://",
      google_sql_user.website.name,
      ":",
      google_sql_user.website.password,
      "@",
      "//cloudsql/${var.gcp_project_id}:${var.gcp_region}",
      ":",
      google_sql_database_instance.omatic.name,
      "/",
      google_sql_database.database.name,
    ]
  )
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database_url"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.website_postgres_connection_url

  lifecycle {
    create_before_destroy = true
  }
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "secret_key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "secret_key" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = random_password.secret_key.result

  lifecycle {
    create_before_destroy = true
  }
}

# resource "google_secret_manager_secret" "service_accounts" {
#   for_each = toset([
#     "website",
#     # "worker",
#   ])
#   secret_id = "${each.key}-service_account_key"

#   replication {
#     auto {}
#   }
# }

# resource "google_secret_manager_secret_version" "service_accounts" {
#   for_each    = google_secret_manager_secret.service_accounts
#   secret      = each.value.id
#   secret_data = base64decode(google_service_account_key.omatic[each.key].private_key)

#   lifecycle {
#     create_before_destroy = true
#   }
# }
