from django.contrib import admin

# Register your models here.

from .models import MOTD

admin.site.register(MOTD)

