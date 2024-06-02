from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .helpers import get_all_gigs_over_time_stats, get_all_stats
from .util import dateconverter
import json
from datetime import datetime
from go3.settings import URL_BASE

# Create your views here.
class AllStatsView(LoginRequiredMixin, TemplateView):
    template_name = 'stats/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_base'] = URL_BASE
        context['the_stats'] = get_all_stats()

        # get the gigs over time data
        context['gigs_over_time_data'] = json.dumps(get_all_gigs_over_time_stats(), default=dateconverter)

        return context
