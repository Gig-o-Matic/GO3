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
from go3.colors import the_colors
from member.models import MemberPreferences
from member.util import AgendaChoices

@login_required
def AgendaSelector(request):

    view_selector = {
        AgendaChoices.AGENDA: AgendaView
    }

    return view_selector[request.user.preferences.default_view].as_view()(request)

class AgendaView(LoginRequiredMixin, TemplateView):
    template_name='agenda/agenda.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['the_colors'] = the_colors
        return context

class CalendarView(LoginRequiredMixin, TemplateView):
    template_name='agenda/calendar.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['the_colors'] = the_colors
        return context
