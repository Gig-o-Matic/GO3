resource "random_id" "db_name_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "omatic" {
  name                = "${var.gcp_project_id}-${random_id.db_name_suffix.hex}"
  region              = var.gcp_region
  database_version    = "POSTGRES_13"
  deletion_protection = "true"

  settings {
    tier      = "db-f1-micro"
    disk_size = "10"

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    backup_configuration {
      enabled    = true
      location   = var.gcp_region
      start_time = "07:00"

      backup_retention_settings {
        retained_backups = 1
      }
    }

    ip_configuration {
      ipv4_enabled = true
      require_ssl  = true
    }
  }
}

resource "google_sql_database" "database" {
  name     = var.gcp_project_id
  instance = google_sql_database_instance.omatic.name
}

resource "random_password" "website_sql_user" {
  length  = 32
  special = false
}

resource "google_sql_user" "website" {
  name     = "website"
  password = random_password.website_sql_user.result
  instance = google_sql_database_instance.omatic.name
  type     = "BUILT_IN"
}


# resource "google_sql_user" "management" {
#   name     = "tf-management"
#   password = var.management_sql_user_password
#   instance = google_sql_database_instance.omatic.name
#   type     = "BUILT_IN"
# }

# locals {
#   read_only_sql_users = ["bigquery"]
# }

# resource "random_password" "read_only_sql_users" {
#   for_each = toset(local.read_only_sql_users)
#   length   = 32
#   special  = false
# }

# resource "google_sql_user" "read_only" {
#   for_each = random_password.read_only_sql_users
#   name     = each.key
#   password = each.value.result
#   instance = google_sql_database_instance.omatic.name
#   type     = "BUILT_IN"
# }

resource "google_sql_user" "service_accounts" {
  for_each = {
    website = google_service_account.omatic["website"].email,
    # worker  = google_service_account.omatic["worker"].email,
  }
  name     = replace(each.value, ".gserviceaccount.com", "")
  instance = google_sql_database_instance.omatic.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

resource "google_sql_user" "users" {
  for_each = toset(var.gcp_project_editors)
  name     = lower(each.value)
  instance = google_sql_database_instance.omatic.name
  type     = "CLOUD_IAM_USER"
}
