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
from . import helpers

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='member-detail'),
    path('<int:pk>/update', views.UpdateView.as_view(), name='member-update'),
    path('<int:pk>/preferences/update/', views.PreferencesUpdateView.as_view(), name='member-prefs-update'),

    path('<int:pk>/assocs/', views.AssocsView.as_view(), name='member-assocs'),
    path('<int:pk>/otherbands/', views.OtherBandsView.as_view(), name='member-otherbands'),

    path('<int:pk>/motd_seen',helpers.motd_seen),

    path('calfeed/<uuid:pk>', helpers.calfeed),

    path('invite', views.invite, name='member-invite'),

]
