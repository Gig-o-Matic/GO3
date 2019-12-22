from django.contrib import admin

# Register your models here.

from .models import Band, Assoc

admin.site.register(Band)
admin.site.register(Assoc)

