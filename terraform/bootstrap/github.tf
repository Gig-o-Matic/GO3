locals {
  oidc_pool_id = replace(var.github_repo, "/", "-")
}

module "github_oidc" {
  source      = "terraform-google-modules/github-actions-runners/google//modules/gh-oidc"
  version     = "~> 2.0"
  project_id  = var.gcp_project_id
  pool_id     = local.oidc_pool_id
  provider_id = local.oidc_pool_id
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.sub"              = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.ref"              = "assertion.ref"
    "attribute.environment"      = "assertion.environment"
    "attribute.workflow"         = "assertion.workflow"
    "attribute.job_workflow_ref" = "assertion.job_workflow_ref"
  }
  attribute_condition = "assertion.repository=='${var.github_repo}'"
  sa_mapping = {
    "github-deployer" = {
      sa_name = google_service_account.github_deployer.name
      # attribute = "attribute.ref/refs/heads/jefwecan/first-look"
      attribute = "attribute.repository/${var.github_repo}"
    }
  }
}

resource "google_service_account" "github_deployer" {
  account_id   = "github-deployer"
  display_name = "Identity used for privileged deploys within GitHub Actions workflow runs"
}

resource "google_project_iam_member" "github_deployer" {
  project = google_project.murga_o_matic.id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"
}
