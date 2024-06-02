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

    for b in Band.objects.all():

        # number of members in each band
        m = BandMetric.objects.get_or_create(
            name='Number of Active Members', band=b,
            defaults={
                'name' : 'Number of Active Members',
                'band' : b,
                'kind' : MetricTypes.DAILY,
            })
        c = b.confirmed_members.count()
        m.register(c)

        # number of gigs each band is planning
        m = BandMetric.objects.get_or_create(
            name='Number of Gigs', band=b,
            defaults={
                'name' : 'Number of Gigs',
                'band' : b,
                'kind' : MetricTypes.DAILY,
            }
        )
        gigcount = Gig.objects.future().filter(
            band=b,
            date__gte=timezone.now()
        ).count()
        m.register(gigcount)

def async_register_sent_emails(counter):
    async_task('stats.tasks.register_sent_emails', counter)

def register_sent_emails(counter):
    """ recieves a collections Counter object of bands """

    for k, v in counter.items():
        """ add to the total emails sent today by this band """
        m, _ = BandMetric.objects.get_or_create(
            name='Number of Emails Sent', band=k,
            defaults={
                'name' : 'Number of Emails Sent',
                'band' : k,
                'kind' : MetricTypes.EVERY
            }
        )
        m.register(v)

