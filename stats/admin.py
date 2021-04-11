from django.contrib import admin
from .models import BandMetric

# Register your models here.
@admin.register(BandMetric)
class BandMetricAdmin(admin.ModelAdmin):
    pass
