variable "app_log_level" {
  type    = string
  default = "INFO"
}

variable "base_domain" {
  type    = string
  default = "murga.app"
}

variable "cloud_run_subdomain" {
  type    = string
  default = "gig-o"
}

variable "gcp_project_editors" {
  type = list(string)
  default = [
    "Jeff.Hogan1@gmail.com",
  ]
}

variable "gcp_project_id" {
  type    = string
  default = "murga-o-matic"
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "website_image" {
  type    = string
  default = "gcr.io/murga-o-matic/website:latest"
}

# variable "worker_image" {
#   type    = string
#   default = "gcr.io/murga-o-matic/worker:latest"
# }
