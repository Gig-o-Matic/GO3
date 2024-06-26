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
from django.http import HttpResponse
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from member.util import AgendaChoices
from band.models import Assoc
from band.util import AssocStatusChoices
from datetime import datetime
import json
from graphene_django.views import GraphQLView


@login_required
def AgendaSelector(request):

    view_selector = {
        AgendaChoices.AGENDA: AgendaView,
        AgendaChoices.CALENDAR: CalendarView,
        AgendaChoices.GRID: GridView,
    }

    return view_selector[request.user.preferences.default_view].as_view()(request)

class AgendaBaseView(LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hidden_bands"] = [assoc.band for assoc in self.request.user.assocs.filter(hide_from_schedule=True)]
        return context

class AgendaView(AgendaBaseView):
    template_name = 'agenda/agenda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Default to the first band's timezone, if an association exists
        if self.request.user.assocs.count() > 0:
            b = self.request.user.assocs.first().band
            timezone.activate(b.timezone)

        return context


class CalendarView(AgendaBaseView):
    template_name = 'agenda/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        m = self.request.GET.get('m', None)
        y = self.request.GET.get('y', None)

        if m and y:
            m = int(m)
            y = int(y)
            context['initialDate'] = f'{y}-{m:02d}-01'

        return context


class GridView(LoginRequiredMixin, TemplateView):
    template_name = 'agenda/grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['year'] = datetime.now().year
        context['month'] = datetime.now().month-1

        # find my bands
        m = self.request.user
        assocs = Assoc.objects.filter(
            member=m, status=AssocStatusChoices.CONFIRMED)
        context['band_data_json'] = json.dumps(
            [{'id': a.band.id, 'name': a.band.name} for a in assocs])

        return context


class GridViewHeatmap(LoginRequiredMixin, TemplateView):
    template_name = 'agenda/grid_heatmap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['year'] = self.request.GET.get(
            'year', None) or datetime.now().year

        return context


class PrivateGraphQLView(LoginRequiredMixin, GraphQLView):
    pass
