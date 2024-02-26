resource "google_storage_bucket" "statics" {
  name          = "cstatic.${var.base_domain}"
  location      = "US"
  force_destroy = true

  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
  }
}

# TODO: fix all these IAM bits here...

# resource "google_storage_bucket_iam_member" "all_users_viewers" {
#   bucket = google_storage_bucket.statics.name
#   role   = "roles/storage.legacyObjectReader"
#   member = "allUsers"
# }

# resource "google_storage_bucket_iam_member" "omatic_sa_obj_admin" {
#   bucket = google_storage_bucket.statics.name
#   role   = "roles/storage.legacyObjectOwner"
#   member = "serviceAccount:${google_service_account.omatic["website"].email}"
# }


# resource "google_storage_bucket_iam_member" "omatic_sa_bucket_reader" {
#   bucket = google_storage_bucket.statics.name
#   role   = "roles/storage.legacyBucketReader"
#   member = "serviceAccount:${google_service_account.omatic["website"].email}"
# }


# resource "google_storage_bucket_iam_member" "omatic_worker_sa_obj_admin" {
#   bucket = google_storage_bucket.statics.name
#   role   = "roles/storage.objectAdmin"
#   member = "serviceAccount:${google_service_account.omatic["worker"].email}"
# }


# resource "google_storage_bucket_iam_member" "omatic_worker_sa_obj_owner" {
#   bucket = google_storage_bucket.statics.name
#   role   = "roles/storage.legacyObjectOwner"
#   member = "serviceAccount:${google_service_account.omatic["worker"].email}"
# }


# resource "google_storage_bucket_iam_member" "omatic_worker_sa_bucket_reader" {
#   bucket = google_storage_bucket.statics.name
#   role   = "roles/storage.legacyBucketReader"
#   member = "serviceAccount:${google_service_account.omatic["worker"].email}"
# }
