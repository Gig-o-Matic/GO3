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
from django.shortcuts import redirect
from django.utils import timezone
from member.util import AgendaChoices, AgendaLayoutChoices
from band.models import Assoc
from band.util import AssocStatusChoices
from datetime import datetime
import json
from graphene_django.views import GraphQLView
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from gig.tasks import alert_watchers

@login_required
def AgendaSelector(request):

    alert_watchers()

    if request.user.band_count == 0:
        return redirect("/member")

    try:
        newzone = request.GET['zone']
        request.user.preferences.current_timezone = newzone
        request.user.preferences.save()
    except KeyError:
        pass

    if request.user:
        request.session["django_timezone"] = request.user.preferences.current_timezone
        timezone.activate(request.user.preferences.current_timezone)


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

        # Depending on the layout they want, send different instructions

        if self.request.user.preferences.agenda_use_classic:
            if len(self.request.user.future_noplans) == 0:
                context['noplans'] = False
            else:
                context['noplans'] = True
        else:
            layout = self.request.user.preferences.agenda_layout
            if layout == AgendaLayoutChoices.HAS_RESPONSE:
                layout = AgendaLayoutChoices.ONE_LIST
                
            layout_band = self.request.user.preferences.agenda_band
            context['the_layout'] = layout

            # the buttons are an array for the template to chew on:
            # * layout type
            # * button label
            # * band (if it's a band filter otherwise ignored)
            # * True if the button is active
            # * True if it's the 'needs response' button
            context['the_buttons'] = [
                [AgendaLayoutChoices.ONE_LIST, _("All Upcoming Gigs"), 0,
                 layout==AgendaLayoutChoices.ONE_LIST, False],
                [AgendaLayoutChoices.NEED_RESPONSE, _('Needs Reponse'), 0,
                    layout==AgendaLayoutChoices.NEED_RESPONSE, True],
            ]

            bands = [a.band for a in self.request.user.confirmed_assocs if not a.hide_from_schedule]
            if len(bands) > 1:
                for b in bands:
                    context['the_buttons'].append(
                        [AgendaLayoutChoices.BY_BAND, 
                         b.shortname if b.shortname else b.name, b.id,
                         layout==AgendaLayoutChoices.BY_BAND and layout_band==b, False]
                    )

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


class GridView(AgendaBaseView):
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
