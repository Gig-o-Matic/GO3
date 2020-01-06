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
from django.shortcuts import render
from django.views import generic
from django.views.generic.edit import UpdateView as BaseUpdateView
from django.urls import reverse
from .models import Gig

class DetailView(generic.DetailView):
    model = Gig
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_can_edit'] = self.request.user.is_superuser # todo or band members, admins etc.

        return context

class UpdateView(BaseUpdateView):
    model = Gig
    fields = ['title','contact','status','is_private','date','enddate','calltime','settime','endtime','address','dress','paid','postgig',
                'details','setlist','rss_description','invite_occasionals','hide_from_calendar']
    def get_success_url(self):
        return reverse('gig-detail', kwargs={'pk': self.object.id})
