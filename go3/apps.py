from django.contrib.admin.apps import AdminConfig

class Go3AdminConfig(AdminConfig):
    default_site = "go3.admin.Go3AdminSite"
