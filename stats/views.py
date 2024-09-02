from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .helpers import get_all_gigs_over_time_stats, get_emails_for_date, get_emails_for_all_bands
from .util import dateconverter
from band.util import _get_active_bands, _get_inactive_bands
import json
from datetime import datetime, timedelta
from go3.settings import URL_BASE

# Create your views here.
class AllStatsView(LoginRequiredMixin, TemplateView):
    template_name = 'stats/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_base'] = URL_BASE
        context['the_stats'] = []
        context['the_stats'].append(['Active Bands Count', [_get_active_bands().count()]])
        context['the_stats'].append(['Inactive Bands', [b.name for b in _get_inactive_bands()]])
        context['the_stats'].append(['Emails Sent Today',[get_emails_for_date(datetime.now().date())]])
        context['the_stats'].append(['Emails Sent Yesterday',[get_emails_for_date((datetime.now().date())-timedelta(days=1))]])

        # get the gigs over time data
        context['gigs_over_time_data'] = json.dumps(get_all_gigs_over_time_stats(), default=dateconverter)

        # get the email totals for all bands
        data = get_emails_for_all_bands(10)
        y = [f'{x[0].name} ({x[2]} today, {x[1]} all time)' for x in data]
        context['the_stats'].append(['Top Emailing Bands',y])

        return context
