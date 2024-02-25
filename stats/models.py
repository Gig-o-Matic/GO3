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

from django.db import models
from band.models import Band
from django.utils import timezone


class MetricTypes(models.IntegerChoices):
    DAILY = 0, "Daily"
    ALLTIME = 1, "All Time"


class Metric(models.Model):
    name = models.TextField(max_length=500, blank=False)
    kind = models.IntegerField(choices=MetricTypes.choices, default=MetricTypes.DAILY)

    def register(self, val):
        if self.kind == MetricTypes.ALLTIME:
            self.stats.all().delete()
        elif self.kind == MetricTypes.DAILY:
            # see if we already have one for today
            now = timezone.now()
            self.stats.filter(created__date=now).delete()
        s = Stat(metric=self, value=val)
        s.save()

    def __str__(self):
        return "{0}".format(self.name)


class BandMetric(Metric):
    band = models.ForeignKey(
        Band, related_name="metrics", on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return "{0} for band {1}".format(super().__str__(), self.band)


class Stat(models.Model):
    metric = models.ForeignKey(
        Metric, related_name="stats", on_delete=models.CASCADE, null=False
    )
    created = models.DateTimeField(default=timezone.now)
    value = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return "Stat of '{0}' created {1}".format(self.metric.name, self.created)
