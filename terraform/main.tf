terraform {
  backend "gcs" {
    bucket = "murga-o-matic-tfstate"
    prefix = "env/production"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.8.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4.3"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9.1"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


# data "terraform_remote_state" "bootstrap" {
#   backend = "gcs"

#   config = {
#     bucket = "murga-o-matic-tfstate"
#     prefix = "bootstrap"
#   }
# }
