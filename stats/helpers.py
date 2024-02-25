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

from .models import BandMetric, Stat
from band.models import Band
from .tasks import collect_band_stats
from django.http import HttpResponse


def get_band_stats(the_band):
    """return the stats that exist for a band"""

    the_stats = []

    the_metrics = BandMetric.objects.filter(band=the_band)
    for m in the_metrics:
        the_stat = m.stats.latest("created")
        the_stats.append(
            {"name": m.name, "date": the_stat.created, "value": the_stat.value}
        )
    return the_stats


def get_gigs_over_time_stats(the_band):
    the_metric = BandMetric.objects.filter(band=the_band, name="Number of Gigs").first()
    if the_metric is None:
        return []
    the_stats = the_metric.stats
    return [[s.created, s.value] for s in the_stats.all()]


def test_stats(request):
    collect_band_stats()
    return HttpResponse()


def get_all_stats():
    """return stats for the whole gig-o"""
    the_stats = []

    the_metrics = BandMetric.objects.filter(band=None)
    for m in the_metrics:
        the_stat = m.stats.latest("created")
        the_stats.append(
            {"name": m.name, "date": the_stat.created, "value": the_stat.value}
        )
    return the_stats


def get_all_gigs_over_time_stats():
    the_metric = BandMetric.objects.filter(band=None, name="Number of Gigs").first()
    if the_metric is None:
        return []
    the_stats = the_metric.stats
    return [[s.created, s.value] for s in the_stats.all()]
