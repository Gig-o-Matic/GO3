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

from django.urls import path
from . import views, helpers

urlpatterns = [
    path("", views.AgendaSelector, name="home"),
    path("agenda", views.AgendaView.as_view(), name="agenda"),
    # path('noplans/<int:page>', helpers.agenda_gigs, name='agenda-gigs-noplans'),
    path("plans/<path:the_type>/<int:page>", helpers.agenda_gigs, name="agenda-gigs"),
    path("calendar", views.CalendarView.as_view(), name="calendar"),
    path("calendar/events/<int:pk>", helpers.calendar_events, name="calendar-events"),
    path("grid", views.GridView.as_view(), name="grid"),
    path("grid/heatmap", helpers.grid_heatmap, name="grid-heatmap"),
    path(
        "grid/section-members",
        helpers.grid_section_members,
        name="grid-section-members",
    ),
    path("grid/gigs", helpers.grid_gigs, name="grid-gigs"),
    path("defaultview/<int:val>", helpers.set_default_view, name="set-default-view"),
]
