from django.contrib import admin

# Register your models here.

from .models import Band, Assoc, Section

class BandAdmin(admin.ModelAdmin):
    readonly_fields = ("creation_date","last_activity",)

admin.site.register(Band, BandAdmin)
admin.site.register(Assoc)
admin.site.register(Section)

