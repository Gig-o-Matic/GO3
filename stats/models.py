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

# Create your models here.

class Metric(models.Model):
    name = models.TextField(max_length=500, blank=False)

    def __str__(self):
        return "{0}".format(self.name)

class BandMetric(Metric):
    band = models.ForeignKey(Band, related_name="metrics", on_delete=models.CASCADE, null=False)

    def __str__(self):
        return "{0} for band {1}".format(super().__str__(), self.band)


class Stat(models.Model):
    metric = models.ForeignKey(Metric, related_name="stats", on_delete=models.CASCADE, null=False)
    updated = models.DateTimeField(auto_now=True)
    value = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return "Stat of '{0}' updated {1}".format(self.metric.name, self.updated)
