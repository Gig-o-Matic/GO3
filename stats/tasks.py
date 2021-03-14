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

    for b in Band.objects.all():

        # number of members in each band
        m = BandMetric.objects.filter(name='Number of Members', band=b).first()
        if m is None:
            m = BandMetric(name='Number of Members', band=b, kind=MetricTypes.DAILY)
            m.save()
        m.register(b.confirmed_members.count())

        # number of gigs each band is planning
        m = BandMetric.objects.filter(name='Number of Gigs', band=b).first()
        if m is None:
            m = BandMetric(name='Number of Gigs', band=b,  kind=MetricTypes.DAILY)
            m.save()
        gigcount = Gig.objects.active().filter(
            band=b,
            date__gte=pytz.utc.localize(datetime.utcnow())
        ).count()
        m.register(gigcount)

        # number of gigs total for each band
        m = BandMetric.objects.filter(name='Total Gigs', band=b).first()
        if m is None:
            m = BandMetric(name='Total Gigs', band=b, kind=MetricTypes.ALLTIME)
            m.save()
        m.register(Gig.objects.filter(band=b).count())
