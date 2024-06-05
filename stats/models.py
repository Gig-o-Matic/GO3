"""
    This file is part of Gig-o-Matic

    Gig-o-Matic is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from band.models import Band
from django.db import models
from django.db.models import Sum
from datetime import datetime

class MetricTypes(models.IntegerChoices):
    DAILY = 0, "Daily"
    ALLTIME = 1, "All Time"
    DAILY_ACCUMULATE = 2, "Daily Accumulate"
    EVERY = 3, "Every"


class Metric(models.Model):
    name = models.TextField(max_length=500, blank=False)
    kind = models.IntegerField(
        choices=MetricTypes.choices, default=MetricTypes.DAILY)

    def register(self, val):
        if self.kind == MetricTypes.ALLTIME:
            # for this kind of metric there is only one stat
            Stat.objects.lock_for_update().update_or_create(
                metric=self,
                defaults={
                    "metric":self,
                    "value":val
                },
            )
        elif self.kind == MetricTypes.DAILY:
            # for this kind of metric there's one for each day
            now = datetime.now().date()
            Stat.objects.update_or_create(
                metric=self,
                created=now,
                defaults={
                    "metric":self,
                    "value":val
                },
            )
        elif self.kind == MetricTypes.DAILY_ACCUMULATE:
            # see if we already have one for today
            now = datetime.now().date()
            obj, _ = Stat.objects.get_or_create(
                metric=self,
                created=now,
                defaults={
                    "metric":self,
                }
            )
            obj.value = val
            obj.save(["value"])
        elif self.kind == MetricTypes.EVERY:
            # just save a stat every time
            _ = Stat.objects.create(metric=self, value=val)

    def latest_value(self):
        if self.kind == MetricTypes.EVERY:
            # find out the last time we did any collecting
            s = self.stats.latest('created')
            # sum up all of the stats
            return self.stats.filter(created=s.created).aggregate(Sum('value'))['value__sum'], s.created
        else:
            s = self.stats.latest('created')
            return s.value, s.created
        
    def total_value(self):
        if self.kind == MetricTypes.EVERY:
            # sum up all of the stats
            return self.stats.aggregate(Sum('value'))['value__sum']
        else:
            # for other types, it's the same - just return the latest since they're aggregates
            s = self.stats.latest('created')
            return s.value

    def __str__(self):
        return "{0}".format(self.name)


class BandMetric(Metric):
    band = models.ForeignKey(Band, related_name="metrics",
                             on_delete=models.CASCADE, null=True)

    def __str__(self):
        return "{0} for band {1}".format(super().__str__(), self.band)


class Stat(models.Model):
    metric = models.ForeignKey(
        BandMetric, related_name="stats", on_delete=models.CASCADE, null=False)
    created = models.DateField(auto_now_add=True)
    value = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return "Stat of '{0}' created {1}".format(self.metric, self.created)
