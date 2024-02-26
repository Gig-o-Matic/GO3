output "gha_service_account_email" {
  value = google_service_account.github_deployer.email
}

output "github_oidc_provider_name" {
  value = module.github_oidc.provider_name
}

output "project_number" {
  value = google_project.murga_o_matic.number
}
