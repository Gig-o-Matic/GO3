# locals {
#   postgres_connection_url = join(
#     "",
#     [
#       "postgres://",
#       google_sql_user.management.name,
#       ":",
#       google_sql_user.management.password,
#       "@",
#       google_sql_database_instance.omatic.public_ip_address,
#       "/",
#       google_sql_database.database.name,
#     ]
#   )
# }

output "cloud_sql_instance_name" {
  value = google_sql_database_instance.omatic.connection_name
}

output "database_url_secret_name" {
  value = google_secret_manager_secret.database_url.name
}
# output "postgres_connection_url" {
#   value     = local.postgres_connection_url
#   sensitive = true
# }

output "postgres_public_ip_address" {
  value = google_sql_database_instance.omatic.public_ip_address
}

output "postgres_database_name" {
  value = google_sql_database.database.name
}

# output "postgres_management_user_name" {
#   value = google_sql_user.management.name
# }

# output "postgres_management_user_password" {
#   value     = google_sql_user.management.password
#   sensitive = true
# }

# output "sql_usernames" {
#   value = [for u in concat(values(google_sql_user.service_accounts), values(google_sql_user.users)) : u.name]
# }

# output "read_only_sql_usernames" {
#   value = [for u in values(google_sql_user.read_only) : u.name]
# }

# output "read_only_sql_user_passwords" {
#   value     = random_password.read_only_sql_users
#   sensitive = true
# }

output "statics_bucket_id" {
  value = google_storage_bucket.statics.id
}

output "website_domain_name" {
  value = local.cloud_run_domain_name
}
