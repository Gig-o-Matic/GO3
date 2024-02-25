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

from .models import BandMetric, Stat, MetricTypes
from band.models import Band
from gig.models import Gig
from datetime import datetime
import pytz


def collect_band_stats():

    agg_number_active_members = 0
    agg_all_time_number_members = 0
    agg_number_of_gigs = 0
    agg_all_time_gigs = 0

    for b in Band.objects.all():

        # number of members in each band
        m = BandMetric.objects.filter(name="Number of Active Members", band=b).first()
        if m is None:
            m = BandMetric(
                name="Number of Active Members", band=b, kind=MetricTypes.DAILY
            )
            m.save()
        c = b.confirmed_members.count()
        m.register(c)
        agg_number_active_members += c

        # all time members in each band
        m = BandMetric.objects.filter(name="All Time Number of Members", band=b).first()
        if m is None:
            m = BandMetric(
                name="All Time Number of Members", band=b, kind=MetricTypes.ALLTIME
            )
            m.save()
        c = b.assocs.count()
        m.register(c)
        agg_all_time_number_members += c

        # number of gigs each band is planning
        m = BandMetric.objects.filter(name="Number of Gigs", band=b).first()
        if m is None:
            m = BandMetric(name="Number of Gigs", band=b, kind=MetricTypes.DAILY)
            m.save()
        gigcount = (
            Gig.objects.future()
            .filter(band=b, date__gte=pytz.utc.localize(datetime.utcnow()))
            .count()
        )
        m.register(gigcount)
        agg_number_of_gigs += gigcount

        # number of gigs total for each band
        m = BandMetric.objects.filter(name="All Time Total Gigs", band=b).first()
        if m is None:
            m = BandMetric(name="All Time Total Gigs", band=b, kind=MetricTypes.ALLTIME)
            m.save()
        c = Gig.objects.filter(band=b).count()
        m.register(c)
        agg_all_time_gigs = c

        # now collect them in aggregate

        # number of members in each band
        m = BandMetric.objects.filter(
            name="Number of Active Members", band=None
        ).first()
        if m is None:
            m = BandMetric(
                name="Number of Active Members", band=None, kind=MetricTypes.DAILY
            )
            m.save()
        m.register(agg_number_active_members)

        # all time members in each band
        m = BandMetric.objects.filter(
            name="All Time Number of Members", band=None
        ).first()
        if m is None:
            m = BandMetric(
                name="All Time Number of Members", band=None, kind=MetricTypes.ALLTIME
            )
            m.save()
        m.register(agg_all_time_number_members)

        # number of gigs each band is planning
        m = BandMetric.objects.filter(name="Number of Gigs", band=None).first()
        if m is None:
            m = BandMetric(name="Number of Gigs", band=None, kind=MetricTypes.DAILY)
            m.save()
        m.register(agg_number_of_gigs)

        # number of gigs total for each band
        m = BandMetric.objects.filter(name="All Time Total Gigs", band=None).first()
        if m is None:
            m = BandMetric(
                name="All Time Total Gigs", band=None, kind=MetricTypes.ALLTIME
            )
            m.save()
        m.register(agg_all_time_gigs)
