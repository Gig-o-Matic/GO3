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
from django.utils import timezone
from datetime import datetime
from django_q.tasks import async_task
import pytz


def collect_band_stats():

    agg_number_active_members = 0
    agg_all_time_number_members = 0
    agg_number_of_gigs = 0
    agg_all_time_gigs = 0

    for b in Band.objects.all():

        # number of members in each band
        try:
            m = BandMetric.objects.get(name='Number of Active Members', band=b)
        except BandMetric.DoesNotExist:
            m = BandMetric(name='Number of Active Members', band=b, kind=MetricTypes.DAILY)
            m.save()
        c = b.confirmed_members.count()
        m.register(c)
        agg_number_active_members += c

        # number of gigs each band is planning
        try:
            m = BandMetric.objects.get(name='Number of Gigs', band=b)
        except BandMetric.DoesNotExist:
            m = BandMetric(name='Number of Gigs', band=b,  kind=MetricTypes.DAILY)
            m.save()
        gigcount = Gig.objects.future().filter(
            band=b,
            date__gte=timezone.now()
        ).count()
        m.register(gigcount)
        agg_number_of_gigs += gigcount


    # now collect them in aggregate

    # number of members in the bands
    try:
        m = BandMetric.objects.get(name='Number of Active Members', band=None)
    except BandMetric.DoesNotExist:
        m = BandMetric(name='Number of Active Members', band=None, kind=MetricTypes.DAILY)
        m.save()
    m.register(agg_number_active_members)

    # number of gigs each band is planning
    try:
        m = BandMetric.objects.get(name='Number of Gigs', band=None)
    except BandMetric.DoesNotExist:
        m = BandMetric(name='Number of Gigs', band=None,  kind=MetricTypes.DAILY)
        m.save()
    m.register(agg_number_of_gigs)



def async_register_sent_emails(counter):
    async_task('stats.tasks.register_sent_emails', counter)

def register_sent_emails(counter):
    """ recieves a collections Counter object of bands """

    agg_numbers_of_emails = 0
    for k, v in counter.items():
        """ add to the total emails sent today by this band """
        try:
            m = BandMetric.objects.get(name='Number of Emails Sent', band=k)
        except BandMetric.DoesNotExist:
            m = BandMetric(name='Number of Emails Sent', band=k,  kind=MetricTypes.DAILY_ACCUMULATE)
            m.save()

        m.register(v)
        agg_numbers_of_emails += v

    # total emails sent today
    try:
        m = BandMetric.objects.get(name='Number of Emails Sent', band=None)
    except BandMetric.DoesNotExist:
        m = BandMetric(name='Number of Emails Sent', band=None, kind=MetricTypes.DAILY_ACCUMULATE)
        m.save()
    m.register(agg_numbers_of_emails)

