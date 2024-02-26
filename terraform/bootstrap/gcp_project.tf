# import {
#   to = google_project.murga_o_matic
#   id = "murga-o-matic"
# }

resource "google_project" "murga_o_matic" {
  name            = var.gcp_project_name
  project_id      = var.gcp_project_id
  billing_account = var.gcp_billing_account_id

  auto_create_network = false
}

resource "google_project_service" "murga_o_matic" {
  for_each = toset([
    # For gh-oidc module
    # Reference: https://github.com/terraform-google-modules/terraform-google-github-actions-runners/tree/master/modules/gh-oidc#requirements
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iamcredentials.googleapis.com", # IAM Credentials API
    "sts.googleapis.com",

    "serviceusage.googleapis.com",

    "containerregistry.googleapis.com", # hosting cloudrun images
    "artifactregistry.googleapis.com",  # needed for GCR

    "secretmanager.googleapis.com", # direct usage

    "run.googleapis.com",
    "compute.googleapis.com", # Needed to edit Cloud SQL config via the console for some reason?

    "sqladmin.googleapis.com", # for connecting to sql from GHA workflow runs?
  ])

  service                    = each.value
  disable_dependent_services = true

  timeouts {
    create = "30m"
    update = "40m"
  }
}
