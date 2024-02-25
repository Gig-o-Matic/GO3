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
from . import views

urlpatterns = [
    path("", views.help, name="help"),
    path("privacy", views.privacy, name="help-privacy"),
    path("credits", views.credits, name="help-credits"),
    path("changelog", views.changelog, name="help-changelog"),
    path("calfeed/<int:pk>", views.CalfeedView.as_view(), name="help-calfeed"),
    path("whatis", views.whatis, name="help-whatis"),
    path("band_request", views.BandRequestView.as_view(), name="help-band-request"),
]
