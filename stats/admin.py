from django.contrib import admin
from .models import BandMetric, Stat


# Register your models here.
@admin.register(BandMetric)
class BandMetricAdmin(admin.ModelAdmin):
    pass


@admin.register(Stat)
class StatAdmin(admin.ModelAdmin):
    pass
