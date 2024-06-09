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
from .tasks import collect_band_stats
from django.http import HttpResponse
from django.db.models import Sum
from datetime import datetime

def get_band_stats(the_band):
    """ return the stats that exist for a band """

    the_stats = []

    for mname in ['Number of Active Members', 'Number of Gigs', 'Number of Emails Sent']:
        try:
            m = BandMetric.objects.get(band=the_band, name=mname)
            if m.kind == MetricTypes.EVERY:
                the_val = m.total_value()
                the_date = datetime.now().date()
            else:
                the_val, the_date = m.latest_value()
            the_stats.append({
                'name': m.name,
                'date': the_date,
                'value': the_val,
            })
        except BandMetric.DoesNotExist:
            pass
        
    return the_stats

def get_gigs_over_time_stats(the_band):
    try:
        the_metric = BandMetric.objects.get(band=the_band, name='Number of Gigs')
    except BandMetric.DoesNotExist:
        return []

    the_stats = the_metric.stats.order_by("created")
    return [ [s.created, s.value] for s in the_stats.all()]        

def test_stats(request):
    collect_band_stats()
    return HttpResponse()


def get_all_gigs_over_time_stats():
    x = Stat.objects.filter(metric__name='Number of Gigs').order_by('created').values('created').annotate(gigs=Sum('value'))
    return [[s['created'],s['gigs']] for s in x]

def get_emails_for_date(date=None, band=None):

    args = {'metric__name':'Number of Emails Sent'}
    if date:
        args['created'] = date

    if band:
        args['metric__band'] = band

    val = Stat.objects.filter(**args).aggregate(Sum('value'))['value__sum']

    return val if val else 0

def get_emails_for_all_bands(maxnum=None):
    """ returns list of [band, all-time-emails-sent, today-emails-sent]"""
    
    x = Stat.objects.filter(metric__name='Number of Emails Sent').values('metric__band').annotate(emails=Sum('value')).order_by('-emails')
    if maxnum:
        x = x[:maxnum]

    the_list = []
    today = datetime.now().date()
    for s in x:
        """ get emails for today for the band """
        band = Band.objects.get(id=s['metric__band'])
        now = get_emails_for_date(date=today, band=band)
        the_list.append([band, s['emails'], now])

    return the_list
