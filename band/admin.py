from django.contrib import admin

# Register your models here.

from .models import Band, Assoc

class BandAdmin(admin.ModelAdmin):
    readonly_fields = ("creation_date","last_activity",)

admin.site.register(Band, BandAdmin)
admin.site.register(Assoc)

