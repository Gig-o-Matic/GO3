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
    path('<int:pk>/', views.DetailView.as_view(), name='band-detail'),
    path('<int:pk>/update', views.UpdateView.as_view(), name='band-update'),
    path('<int:pk>/members/', views.AllMembersView.as_view(), name='all-members'),
    path('<int:pk>/section/<int:sk>', views.SectionMembersView.as_view(), name='section-members'),

    path('assoc/<int:ak>/tfparam/<str:param>/<str:truefalse>', helpers.set_assoc_tfparam, name='assoc-tfparam'),
    path('assoc/<int:ak>/color/<int:colorindex>', helpers.set_assoc_color, name='assoc-color'),
    path('assoc/<int:ak>/section/<int:sk>', helpers.set_assoc_section, name='assoc-section'),
    path('<int:bk>/join/<int:mk>', helpers.join_assoc, name='assoc-join'),
    path('assoc/<int:ak>/confirm', helpers.confirm_assoc, name='assoc-confirm'),
    path('assoc/<int:ak>/delete', helpers.delete_assoc, name='assoc-delete'),
]
